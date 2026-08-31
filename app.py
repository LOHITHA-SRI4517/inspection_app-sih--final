from flask import (
    Flask, request, redirect, url_for, session,
    send_from_directory, jsonify, render_template_string
)
import sqlite3
import os
import uuid
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import escape


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key-before-production"
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "inspection.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
FACE_FOLDER = os.path.join(BASE_DIR, "face_captures")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["FACE_FOLDER"] = FACE_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FACE_FOLDER, exist_ok=True)


# ============================================================
# CSS
# ============================================================

STYLE = """
<style>
* { box-sizing:border-box; }

body {
    margin:0;
    font-family:Arial, Helvetica, sans-serif;
    background:#f4f7fb;
    color:#1e293b;
}

a { text-decoration:none; }

.navbar {
    background:#ffffff;
    border-bottom:1px solid #e2e8f0;
    padding:14px 5%;
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:15px;
    position:sticky;
    top:0;
    z-index:100;
}

.brand {
    font-size:21px;
    font-weight:bold;
    color:#172554;
    display:flex;
    align-items:center;
    gap:9px;
}

.brand-icon {
    background:#2563eb;
    color:white;
    width:40px;
    height:40px;
    border-radius:10px;
    display:flex;
    justify-content:center;
    align-items:center;
}

.navlinks {
    display:flex;
    gap:4px;
    flex-wrap:wrap;
}

.navlinks a {
    padding:9px 11px;
    color:#475569;
    border-radius:8px;
    font-size:14px;
}

.navlinks a:hover {
    background:#eff6ff;
    color:#2563eb;
}

.container {
    max-width:1200px;
    margin:auto;
    padding:30px 18px;
}

.hero {
    min-height:460px;
    border-radius:24px;
    padding:70px 30px;
    text-align:center;
    background:linear-gradient(135deg,#eff6ff,#ffffff,#eef2ff);
    border:1px solid #dbeafe;
}

.hero-badge {
    display:inline-block;
    background:#dbeafe;
    color:#1d4ed8;
    padding:8px 15px;
    border-radius:30px;
    font-size:13px;
    font-weight:bold;
}

.hero h1 {
    font-size:46px;
    color:#172554;
    max-width:850px;
    margin:20px auto;
}

.hero p {
    max-width:750px;
    margin:auto auto 25px;
    color:#64748b;
    line-height:1.7;
    font-size:17px;
}

.card {
    background:white;
    border:1px solid #e2e8f0;
    border-radius:17px;
    padding:23px;
    margin-bottom:20px;
    box-shadow:0 5px 20px rgba(15,23,42,.04);
}

.grid {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:18px;
    margin-top:22px;
}

.feature {
    background:white;
    padding:23px;
    border-radius:16px;
    border:1px solid #e2e8f0;
}

.feature h3 { color:#172554; }

.feature p {
    color:#64748b;
    line-height:1.6;
    font-size:14px;
}

.feature-icon { font-size:30px; }

.btn {
    display:inline-block;
    border:none;
    padding:11px 18px;
    border-radius:9px;
    background:#2563eb;
    color:white;
    font-weight:bold;
    cursor:pointer;
    margin:3px;
}

.btn:hover { opacity:.9; }

.btn-green { background:#059669; }
.btn-purple { background:#7c3aed; }
.btn-orange { background:#ea580c; }
.btn-red { background:#dc2626; }

.btn-light {
    background:#eff6ff;
    color:#1d4ed8;
}

.form-grid {
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:15px;
}

.field label {
    display:block;
    margin-bottom:6px;
    font-size:14px;
    font-weight:bold;
}

input, select, textarea {
    width:100%;
    padding:12px;
    border:1px solid #cbd5e1;
    border-radius:9px;
    font-size:15px;
}

textarea {
    min-height:110px;
    resize:vertical;
}

.full { grid-column:1/-1; }

.info {
    background:#eff6ff;
    border-left:5px solid #2563eb;
    padding:14px;
    border-radius:8px;
    margin:14px 0;
    line-height:1.6;
}

.success {
    background:#ecfdf5;
    border-left-color:#059669;
}

.warning {
    background:#fff7ed;
    border-left-color:#ea580c;
}

.error {
    background:#fef2f2;
    border-left-color:#dc2626;
}

.stats {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
    gap:15px;
    margin-bottom:20px;
}

.stat {
    background:white;
    border:1px solid #e2e8f0;
    padding:20px;
    border-radius:14px;
}

.num {
    font-size:30px;
    font-weight:bold;
    color:#2563eb;
}

.table-wrap { overflow-x:auto; }

table {
    width:100%;
    border-collapse:collapse;
    min-width:650px;
}

th {
    background:#172554;
    color:white;
}

th, td {
    padding:12px;
    text-align:left;
    border-bottom:1px solid #e2e8f0;
}

.badge {
    padding:5px 9px;
    border-radius:20px;
    font-size:12px;
    font-weight:bold;
}

.low { background:#dcfce7; color:#166534; }
.medium { background:#fef3c7; color:#92400e; }
.high { background:#fee2e2; color:#991b1b; }

.evidence {
    width:90px;
    height:65px;
    object-fit:cover;
    border-radius:7px;
}

.camera {
    width:100%;
    background:#111827;
    border-radius:12px;
    min-height:280px;
}

.login-box {
    max-width:460px;
    margin:45px auto;
}

.footer {
    text-align:center;
    padding:30px;
    color:#64748b;
}

.role {
    background:#eef2ff;
    color:#4338ca;
    padding:6px 10px;
    border-radius:20px;
    font-size:12px;
    font-weight:bold;
}

@media(max-width:700px) {
    .navbar { flex-direction:column; align-items:flex-start; }
    .hero h1 { font-size:32px; }
    .form-grid { grid-template-columns:1fr; }
    .full { grid-column:auto; }
}
</style>
"""


LAYOUT = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
</head>
<body>
{{ navbar|safe }}
<main class="container">
{{ body|safe }}
</main>
<div class="footer">
SIMMS • Smart Real-Time Monitoring & Inspection System
</div>
</body>
</html>
"""


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def logged_in():
    return "user_id" in session


def role_required(role):
    return logged_in() and session.get("role") == role


def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def esc(value):
    if value is None:
        return ""
    return str(escape(str(value)))


def priority_for(count):
    if count >= 4:
        return "High"
    elif count >= 2:
        return "Medium"
    return "Low"


def priority_badge(priority):
    classes = {
        "Low": "low",
        "Medium": "medium",
        "High": "high"
    }
    return '<span class="badge {}">{}</span>'.format(
        classes.get(priority, "low"),
        esc(priority)
    )


# ============================================================
# NAVIGATION
# ============================================================

def nav():
    if not logged_in():
        return """
        <div class="navbar">
            <a class="brand" href="/">
                <span class="brand-icon">🏛️</span> SIMMS
            </a>
            <div class="navlinks">
                <a href="/">Home</a>
                <a href="/login">🔐 Login</a>
            </div>
        </div>
        """

    role = session.get("role")

    links = """
        <a href="/home">🏠 Home</a>
        <a href="/dashboard">📊 Dashboard</a>
    """

    if role in ("Worker", "Inspector"):
        links += '<a href="/my-assignments">📋 Assignments</a>'

    if role == "Authority":
        links += """
            <a href="/users">👥 Users</a>
            <a href="/assignments">🎲 Assign</a>
            <a href="/analytics">📈 Analytics</a>
            <a href="/cctv">📹 CCTV</a>
        """

    links += """
        <a href="/meetings">🎥 Meetings</a>
        <a href="/logout">🚪 Logout</a>
    """

    return """
    <div class="navbar">
        <a class="brand" href="/home">
            <span class="brand-icon">🏛️</span> SIMMS
        </a>
        <div class="navlinks">
            %s
        </div>
    </div>
    """ % links


def page(body, title="SIMMS"):
    return render_template_string(
        STYLE + LAYOUT,
        body=body,
        navbar=nav(),
        title=title
    )


# ============================================================
# DATABASE
# ============================================================

def init_db():
    conn = db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        location TEXT NOT NULL,
        assigned_at TEXT NOT NULL,
        status TEXT DEFAULT 'Assigned',
        face_verified INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        status TEXT DEFAULT 'Reported',
        priority TEXT DEFAULT 'Low',
        photo TEXT,
        reporter_id INTEGER,
        latitude TEXT,
        longitude TEXT,
        verified INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS cctv_feeds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location TEXT NOT NULL,
        feed_url TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        meeting_code TEXT UNIQUE,
        created_at TEXT NOT NULL,
        created_by INTEGER
    );

    CREATE TABLE IF NOT EXISTS meeting_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TEXT NOT NULL
    );
    """)

    # Default accounts are created internally.
    # They are NOT displayed on the website.
    accounts = [
        ("ADMIN001", "System Authority", "admin123", "Authority"),
        ("INS001", "Inspection Officer", "inspector123", "Inspector"),
        ("WORK001", "Field Worker", "worker123", "Worker")
    ]

    for unique_id, name, password, role in accounts:
        existing = conn.execute(
            "SELECT id FROM users WHERE unique_id=?",
            (unique_id,)
        ).fetchone()

        if not existing:
            conn.execute(
                """INSERT INTO users
                (unique_id,name,password,role,created_at)
                VALUES(?,?,?,?,?)""",
                (
                    unique_id,
                    name,
                    generate_password_hash(password),
                    role,
                    now()
                )
            )

    conn.commit()
    conn.close()


init_db()


# ============================================================
# FRONT PAGE
# ============================================================

@app.route("/")
def landing():

    body = """
    <section class="hero">
        <span class="hero-badge">
            SMART INSPECTION • REAL-TIME MONITORING
        </span>

        <h1>Smart Real-Time Monitoring & Inspection System</h1>

        <p>
            A centralized digital platform for inspection management,
            surprise assignments, field evidence collection, CCTV monitoring,
            real-time reporting and faster corrective action.
        </p>

        <a class="btn" href="/login">🔐 Access SIMMS Portal</a>
        <a class="btn btn-light" href="#features">Explore System</a>
    </section>

    <section id="features" class="grid">

        <div class="feature">
            <div class="feature-icon">🎲</div>
            <h3>Smart Assignment</h3>
            <p>Inspection assignments are randomly allocated to reduce predictable inspections.</p>
        </div>

        <div class="feature">
            <div class="feature-icon">📋</div>
            <h3>Digital Inspection Form</h3>
            <p>Workers and inspectors can complete structured field inspection forms.</p>
        </div>

        <div class="feature">
            <div class="feature-icon">📍</div>
            <h3>GPS & Evidence</h3>
            <p>Location coordinates and photo evidence provide better accountability.</p>
        </div>

        <div class="feature">
            <div class="feature-icon">📹</div>
            <h3>CCTV Monitoring</h3>
            <p>Authorities can centrally manage authorized CCTV monitoring links.</p>
        </div>

        <div class="feature">
            <div class="feature-icon">📊</div>
            <h3>Live Dashboard</h3>
            <p>Track reported issues, priorities and corrective action in one place.</p>
        </div>

        <div class="feature">
            <div class="feature-icon">🎥</div>
            <h3>Team Coordination</h3>
            <p>Create inspection coordination meeting rooms for the team.</p>
        </div>

    </section>

    <div class="card" style="margin-top:25px;text-align:center">
        <h2 style="color:#172554">How SIMMS Works</h2>
        <p style="color:#64748b;line-height:2">
            🎲 Assign Inspection &nbsp; → &nbsp;
            📷 Verify Worker &nbsp; → &nbsp;
            📋 Complete Inspection &nbsp; → &nbsp;
            📍 Capture Evidence &nbsp; → &nbsp;
            📊 Authority Reviews &nbsp; → &nbsp;
            ✅ Issue Resolved
        </p>
    </div>
    """

    return page(body, "SIMMS | Smart Inspection System")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if logged_in():
        return redirect(url_for("home"))

    message = ""

    if request.method == "POST":

        unique_id = request.form.get(
            "unique_id", ""
        ).strip().upper()

        password = request.form.get("password", "")

        conn = db()
        user = conn.execute(
            "SELECT * FROM users WHERE unique_id=?",
            (unique_id,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        message = """
        <div class="info error">
            ❌ Invalid Unique ID or Password.
        </div>
        """

    body = """
    <div class="card login-box">

        <div style="text-align:center">
            <div class="brand-icon" style="margin:auto">🔐</div>
            <h1 style="color:#172554">Welcome Back</h1>
            <p style="color:#64748b">
                Login to access your SIMMS workspace.
            </p>
        </div>

        %s

        <form method="POST">

            <div class="field">
                <label>Unique ID</label>
                <input name="unique_id"
                       placeholder="Enter your Unique ID"
                       required>
            </div>

            <br>

            <div class="field">
                <label>Password</label>
                <input type="password"
                       name="password"
                       placeholder="Enter your password"
                       required>
            </div>

            <button class="btn"
                    style="width:100%%;margin-top:18px">
                🔐 Login to SIMMS
            </button>

        </form>

        <div style="text-align:center;margin-top:18px">
            <a href="/forgot-password"
               style="color:#2563eb;font-weight:bold">
                Forgot Password?
            </a>
        </div>

        <div style="text-align:center;margin-top:15px">
            <a href="/" style="color:#64748b">
                ← Back to Home
            </a>
        </div>

    </div>
    """ % message

    return page(body, "SIMMS Login")


# ============================================================
# FORGOT PASSWORD
# ============================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    message = ""

    if request.method == "POST":

        unique_id = request.form.get(
            "unique_id", ""
        ).strip().upper()

        new_password = request.form.get(
            "new_password", ""
        )

        if len(new_password) < 4:
            message = """
            <div class="info error">
                Password must contain at least 4 characters.
            </div>
            """
        else:
            conn = db()

            user = conn.execute(
                "SELECT id FROM users WHERE unique_id=?",
                (unique_id,)
            ).fetchone()

            if user:
                conn.execute(
                    "UPDATE users SET password=? WHERE id=?",
                    (
                        generate_password_hash(new_password),
                        user["id"]
                    )
                )
                conn.commit()
                message = """
                <div class="info success">
                    ✅ Password reset successfully.
                    You can now login with your new password.
                </div>
                """
            else:
                message = """
                <div class="info error">
                    ❌ Unique ID was not found.
                </div>
                """

            conn.close()

    body = """
    <div class="card login-box">
        <h1 style="color:#172554">🔑 Reset Password</h1>

        <p style="color:#64748b">
            Enter your registered Unique ID and choose a new password.
        </p>

        %s

        <form method="POST">

            <div class="field">
                <label>Unique ID</label>
                <input name="unique_id" required>
            </div>

            <br>

            <div class="field">
                <label>New Password</label>
                <input type="password"
                       name="new_password"
                       minlength="4"
                       required>
            </div>

            <button class="btn"
                    style="margin-top:15px;width:100%%">
                Reset Password
            </button>
        </form>

        <p>
            <a href="/login">← Back to Login</a>
        </p>
    </div>
    """ % message

    return page(body, "Forgot Password")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ============================================================
# HOME
# ============================================================

@app.route("/home")
def home():

    if not logged_in():
        return redirect(url_for("login"))

    role = session.get("role")

    if role == "Authority":
        actions = """
        <a class="btn" href="/dashboard">📊 Dashboard</a>
        <a class="btn btn-purple" href="/assignments">🎲 Assign Inspection</a>
        <a class="btn btn-green" href="/cctv">📹 CCTV Monitoring</a>
        """
    else:
        actions = """
        <a class="btn" href="/my-assignments">📋 My Assignments</a>
        <a class="btn btn-purple" href="/dashboard">📊 My Reports</a>
        """

    body = """
    <div class="card">
        <span class="role">%s</span>

        <h1 style="color:#172554">
            Welcome, %s 👋
        </h1>

        <p style="color:#64748b">
            Welcome to your Smart Inspection Management workspace.
        </p>

        <div class="info">
            🔐 Role-based access is active. Use the modules below
            to manage your inspection activities.
        </div>

        %s
    </div>
    """ % (
        esc(role),
        esc(session.get("name")),
        actions
    )

    return page(body, "SIMMS Home")


# ============================================================
# USER MANAGEMENT
# ============================================================

@app.route("/users", methods=["GET", "POST"])
def users():

    if not role_required("Authority"):
        return "Access denied", 403

    message = ""

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not name or len(password) < 4:
            message = """
            <div class="info error">
                Please provide a valid name and password.
            </div>
            """
        else:

            prefix = {
                "Authority": "AUTH",
                "Inspector": "INS",
                "Worker": "WORK"
            }.get(role, "USER")

            unique_id = prefix + uuid.uuid4().hex[:6].upper()

            conn = db()
            conn.execute(
                """INSERT INTO users
                (unique_id,name,password,role,created_at)
                VALUES(?,?,?,?,?)""",
                (
                    unique_id,
                    name,
                    generate_password_hash(password),
                    role,
                    now()
                )
            )
            conn.commit()
            conn.close()

            message = """
            <div class="info success">
                ✅ User created successfully.<br>
                Unique ID: <b>%s</b>
            </div>
            """ % esc(unique_id)

    conn = db()
    users_list = conn.execute(
        "SELECT unique_id,name,role,created_at FROM users ORDER BY id DESC"
    ).fetchall()
    conn.close()

    rows = ""

    for user in users_list:
        rows += """
        <tr>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        """ % (
            esc(user["unique_id"]),
            esc(user["name"]),
            esc(user["role"]),
            esc(user["created_at"])
        )

    body = """
    <div class="card">
        <h1>👥 User Management</h1>
        %s

        <form method="POST" class="form-grid">

            <div class="field">
                <label>Full Name</label>
                <input name="name" required>
            </div>

            <div class="field">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>

            <div class="field">
                <label>Role</label>
                <select name="role">
                    <option value="Worker">Worker</option>
                    <option value="Inspector">Inspector</option>
                    <option value="Authority">Authority</option>
                </select>
            </div>

            <div class="field">
                <button class="btn btn-purple">
                    ➕ Create User
                </button>
            </div>

        </form>
    </div>

    <div class="card">
        <h2>Registered Users</h2>
        <div class="table-wrap">
            <table>
                <tr>
                    <th>Unique ID</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Created</th>
                </tr>
                %s
            </table>
        </div>
    </div>
    """ % (message, rows)

    return page(body, "Users")


# ============================================================
# RANDOM ASSIGNMENT
# ============================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()

    workers = conn.execute(
        """SELECT id,name,unique_id FROM users
        WHERE role IN ('Worker','Inspector')"""
    ).fetchall()

    message = ""

    if request.method == "POST":

        location = request.form.get("location", "").strip()

        if not location:
            message = """
            <div class="info error">Please enter a location.</div>
            """
        elif not workers:
            message = """
            <div class="info warning">
                No workers or inspectors are available.
            </div>
            """
        else:

            selected = random.choice(workers)

            conn.execute(
                """INSERT INTO assignments
                (user_id,location,assigned_at,status,face_verified)
                VALUES(?,?,?,?,?)""",
                (
                    selected["id"],
                    location,
                    now(),
                    "Assigned",
                    0
                )
            )

            conn.commit()

            message = """
            <div class="info success">
                🎲 Inspection assigned successfully to <b>%s</b>.
            </div>
            """ % esc(selected["name"])

    assignment_list = conn.execute(
        """SELECT a.*,u.name,u.unique_id
        FROM assignments a
        JOIN users u ON a.user_id=u.id
        ORDER BY a.id DESC"""
    ).fetchall()

    conn.close()

    rows = ""

    for item in assignment_list:
        rows += """
        <tr>
            <td>📍 %s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        """ % (
            esc(item["location"]),
            esc(item["name"]),
            esc(item["assigned_at"]),
            esc(item["status"])
        )

    body = """
    <div class="card">
        <h1>🎲 Smart Inspection Assignment</h1>
        <p style="color:#64748b">
            Randomly assign inspection duties to available field personnel.
        </p>

        %s

        <form method="POST">
            <div class="field">
                <label>📍 Inspection Location</label>
                <input name="location"
                       placeholder="Enter location to inspect"
                       required>
            </div>

            <button class="btn btn-purple" style="margin-top:15px">
                🎲 Randomly Assign
            </button>
        </form>
    </div>

    <div class="card">
        <h2>Assignment History</h2>
        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Assigned To</th>
                    <th>Time</th>
                    <th>Status</th>
                </tr>
                %s
            </table>
        </div>
    </div>
    """ % (message, rows)

    return page(body, "Assignments")


# ============================================================
# MY ASSIGNMENTS
# ============================================================

@app.route("/my-assignments")
def my_assignments():

    if not logged_in() or session.get("role") not in (
        "Worker", "Inspector"
    ):
        return "Access denied", 403

    conn = db()

    assignments_list = conn.execute(
        """SELECT * FROM assignments
        WHERE user_id=?
        ORDER BY id DESC""",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    rows = ""

    for assignment in assignments_list:

        if assignment["status"] == "Completed":
            action = "✅ Completed"

        elif assignment["face_verified"]:
            action = """
            <a class="btn btn-green"
               href="/inspection/%s">
               📋 Start Inspection
            </a>
            """ % assignment["id"]

        else:
            action = """
            <a class="btn btn-purple"
               href="/face-verification/%s">
               📷 Verify & Start
            </a>
            """ % assignment["id"]

        rows += """
        <tr>
            <td>📍 %s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        """ % (
            esc(assignment["location"]),
            esc(assignment["assigned_at"]),
            esc(assignment["status"]),
            action
        )

    if not rows:
        rows = """
        <tr>
            <td colspan="4">No assignments available.</td>
        </tr>
        """

    body = """
    <div class="card">
        <h1>📋 My Inspection Assignments</h1>

        <div class="info">
            Complete verification and then submit your field inspection form.
        </div>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Assigned Time</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
                %s
            </table>
        </div>
    </div>
    """ % rows

    return page(body, "My Assignments")


# ============================================================
# FACE / CAMERA VERIFICATION
# No face_recognition package required
# ============================================================

@app.route("/face-verification/<int:assignment_id>", methods=["GET", "POST"])
def face_verification(assignment_id):

    if not logged_in() or session.get("role") not in (
        "Worker", "Inspector"
    ):
        return "Access denied", 403

    conn = db()

    assignment = conn.execute(
        """SELECT * FROM assignments
        WHERE id=? AND user_id=?""",
        (assignment_id, session["user_id"])
    ).fetchone()

    if not assignment:
        conn.close()
        return "Assignment not found", 404

    if request.method == "POST":

        photo = request.files.get("face_photo")

        if photo and photo.filename and allowed_file(photo.filename):

            filename = (
                "verification_" +
                uuid.uuid4().hex +
                ".jpg"
            )

            photo.save(
                os.path.join(FACE_FOLDER, filename)
            )

            conn.execute(
                """UPDATE assignments
                SET face_verified=1
                WHERE id=?""",
                (assignment_id,)
            )

            conn.commit()
            conn.close()

            return redirect(
                url_for(
                    "inspection",
                    assignment_id=assignment_id
                )
            )

        conn.close()
        return "Please capture a valid image.", 400

    conn.close()

    # IMPORTANT:
    # This is NOT an f-string, so JavaScript braces will never
    # cause the SyntaxError you were getting.
    body = """
    <div class="card" style="max-width:700px;margin:auto">

        <h1>📷 Identity Verification</h1>

        <div class="info">
            📍 Assigned Location: <b>%s</b><br>
            Capture a verification photograph before starting the inspection.
        </div>

        <video id="video"
               class="camera"
               autoplay
               playsinline>
        </video>

        <canvas id="canvas" style="display:none"></canvas>

        <form id="cameraForm"
              method="POST"
              enctype="multipart/form-data">

            <input id="facePhoto"
                   type="file"
                   name="face_photo"
                   accept="image/*"
                   style="display:none">

            <button type="button"
                    class="btn btn-purple"
                    onclick="capturePhoto()">
                📸 Capture & Continue
            </button>

        </form>

        <p id="cameraMessage"
           style="color:#dc2626;font-weight:bold">
        </p>

    </div>

    <script>
    const video = document.getElementById("video");

    navigator.mediaDevices.getUserMedia({ video: true })
        .then(function(stream) {
            video.srcObject = stream;
        })
        .catch(function() {
            document.getElementById("cameraMessage").innerText =
                "Camera access was denied. Please allow camera permission.";
        });

    function capturePhoto() {

        if (!video.videoWidth) {
            alert("Camera is still loading. Please wait.");
            return;
        }

        const canvas = document.getElementById("canvas");

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext("2d");

        context.drawImage(
            video,
            0,
            0,
            canvas.width,
            canvas.height
        );

        canvas.toBlob(function(blob) {

            const file = new File(
                [blob],
                "verification.jpg",
                { type: "image/jpeg" }
            );

            const transfer = new DataTransfer();

            transfer.items.add(file);

            document.getElementById("facePhoto").files =
                transfer.files;

            if (video.srcObject) {
                video.srcObject.getTracks().forEach(function(track) {
                    track.stop();
                });
            }

            document.getElementById("cameraForm").submit();

        }, "image/jpeg");
    }
    </script>
    """ % esc(assignment["location"])

    return page(body, "Verification")


# ============================================================
# INSPECTION FORM
# ============================================================

@app.route("/inspection/<int:assignment_id>", methods=["GET", "POST"])
def inspection(assignment_id):

    if not logged_in() or session.get("role") not in (
        "Worker", "Inspector"
    ):
        return "Access denied", 403

    conn = db()

    assignment = conn.execute(
        """SELECT * FROM assignments
        WHERE id=? AND user_id=?
        AND face_verified=1
        AND status='Assigned'""",
        (assignment_id, session["user_id"])
    ).fetchone()

    if not assignment:
        conn.close()
        return "Inspection access denied", 403

    if request.method == "POST":

        cleanliness = request.form.get("cleanliness")
        safety = request.form.get("safety")
        facilities = request.form.get("facilities")
        description = request.form.get("description", "").strip()
        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")

        photo_name = None
        photo = request.files.get("photo")

        if photo and photo.filename:

            if allowed_file(photo.filename):

                extension = secure_filename(
                    photo.filename
                ).rsplit(".", 1)[1].lower()

                photo_name = (
                    uuid.uuid4().hex +
                    "." +
                    extension
                )

                photo.save(
                    os.path.join(
                        UPLOAD_FOLDER,
                        photo_name
                    )
                )

        checks = [
            ("Cleanliness", cleanliness),
            ("Safety", safety),
            ("Facilities", facilities)
        ]

        issues_found = []

        for issue_type, answer in checks:

            if answer == "No":

                count = conn.execute(
                    """SELECT COUNT(*) FROM issues
                    WHERE LOWER(location)=LOWER(?)""",
                    (assignment["location"],)
                ).fetchone()[0] + 1

                priority = priority_for(count)

                conn.execute(
                    """INSERT INTO issues
                    (location,issue_type,description,created_at,
                     status,priority,photo,reporter_id,
                     latitude,longitude,verified)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        assignment["location"],
                        issue_type,
                        description,
                        now(),
                        "Reported",
                        priority,
                        photo_name,
                        session["user_id"],
                        latitude,
                        longitude,
                        0
                    )
                )

                issues_found.append(issue_type)

        conn.execute(
            "UPDATE assignments SET status='Completed' WHERE id=?",
            (assignment_id,)
        )

        conn.commit()
        conn.close()

        result = (
            "Issues reported: " + ", ".join(issues_found)
            if issues_found
            else "No issues were found during this inspection."
        )

        body = """
        <div class="card" style="text-align:center">
            <h1>✅ Inspection Submitted Successfully</h1>
            <div class="info success">
                📍 <b>%s</b><br><br>
                %s
            </div>
            <a class="btn" href="/my-assignments">
                📋 Back to Assignments
            </a>
        </div>
        """ % (
            esc(assignment["location"]),
            esc(result)
        )

        return page(body, "Inspection Submitted")

    location = esc(assignment["location"])
    conn.close()

    body = """
    <div class="card">

        <h1>📋 Field Inspection Form</h1>

        <div class="info">
            📍 Inspection Location: <b>%s</b><br>
            🔐 Verification: <b>Completed</b>
        </div>

        <form method="POST"
              enctype="multipart/form-data"
              class="form-grid">

            <div class="field">
                <label>🧹 Is the area clean?</label>
                <select name="cleanliness">
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                </select>
            </div>

            <div class="field">
                <label>🛡️ Is the area safe?</label>
                <select name="safety">
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                </select>
            </div>

            <div class="field">
                <label>🏢 Are facilities working?</label>
                <select name="facilities">
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                </select>
            </div>

            <div class="field">
                <label>📸 Photo Evidence</label>
                <input type="file"
                       name="photo"
                       accept="image/*">
            </div>

            <div class="field">
                <label>Latitude</label>
                <input id="latitude"
                       name="latitude"
                       readonly>
            </div>

            <div class="field">
                <label>Longitude</label>
                <input id="longitude"
                       name="longitude"
                       readonly>
            </div>

            <div class="full">
                <button type="button"
                        class="btn btn-purple"
                        onclick="getLocation()">
                    📍 Get Current Location
                </button>
            </div>

            <div class="field full">
                <label>📝 Inspection Observation</label>
                <textarea name="description"
                          placeholder="Describe observations or issues...">
                </textarea>
            </div>

            <div class="full">
                <button class="btn"
                        type="submit">
                    📤 Submit Inspection
                </button>
            </div>

        </form>
    </div>

    <script>
    function getLocation() {

        if (!navigator.geolocation) {
            alert("Geolocation is not supported.");
            return;
        }

        navigator.geolocation.getCurrentPosition(
            function(position) {

                document.getElementById("latitude").value =
                    position.coords.latitude;

                document.getElementById("longitude").value =
                    position.coords.longitude;

            },
            function() {
                alert("Please allow location permission.");
            }
        );
    }
    </script>
    """ % location

    return page(body, "Inspection Form")


# ============================================================
# UPLOADS
# ============================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():
        return redirect(url_for("login"))

    conn = db()

    if session.get("role") == "Authority":

        issues = conn.execute(
            "SELECT * FROM issues ORDER BY id DESC"
        ).fetchall()

    else:

        issues = conn.execute(
            """SELECT * FROM issues
            WHERE reporter_id=?
            ORDER BY id DESC""",
            (session["user_id"],)
        ).fetchall()

    conn.close()

    total = len(issues)
    reported = sum(
        issue["status"] == "Reported"
        for issue in issues
    )
    progress = sum(
        issue["status"] == "In Progress"
        for issue in issues
    )
    resolved = sum(
        issue["status"] == "Resolved"
        for issue in issues
    )

    rows = ""

    for issue in issues:

        if issue["photo"]:
            photo = """
            <a href="/uploads/%s" target="_blank">
                <img class="evidence"
                     src="/uploads/%s">
            </a>
            """ % (
                esc(issue["photo"]),
                esc(issue["photo"])
            )
        else:
            photo = "—"

        if session.get("role") == "Authority":

            if issue["status"] == "Reported":
                action = """
                <a class="btn btn-orange"
                   href="/update/%s/In%%20Progress">
                   Start
                </a>
                """ % issue["id"]

            elif issue["status"] == "In Progress":
                action = """
                <a class="btn btn-green"
                   href="/update/%s/Resolved">
                   Resolve
                </a>
                """ % issue["id"]

            else:
                action = "✅ Resolved"

        else:
            action = "View Only"

        rows += """
        <tr>
            <td>📍 %s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        """ % (
            esc(issue["location"]),
            esc(issue["issue_type"]),
            esc(issue["description"] or "-"),
            priority_badge(issue["priority"]),
            photo,
            esc(issue["status"]),
            action
        )

    if not rows:
        rows = """
        <tr>
            <td colspan="7" style="text-align:center">
                🎉 No issues reported yet.
            </td>
        </tr>
        """

    body = """
    <h1 style="color:#172554">📊 Real-Time Monitoring Dashboard</h1>

    <div class="stats">
        <div class="stat">
            <div class="num">%s</div>
            <small>Total Issues</small>
        </div>

        <div class="stat">
            <div class="num">%s</div>
            <small>Reported</small>
        </div>

        <div class="stat">
            <div class="num">%s</div>
            <small>In Progress</small>
        </div>

        <div class="stat">
            <div class="num">%s</div>
            <small>Resolved</small>
        </div>
    </div>

    <div class="card">
        <h2>🚨 Inspection Reports</h2>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Issue</th>
                    <th>Description</th>
                    <th>Priority</th>
                    <th>Evidence</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
                %s
            </table>
        </div>
    </div>
    """ % (
        total,
        reported,
        progress,
        resolved,
        rows
    )

    return page(body, "Dashboard")


@app.route("/update/<int:issue_id>/<status>")
def update_status(issue_id, status):

    if not role_required("Authority"):
        return "Access denied", 403

    if status not in ("Reported", "In Progress", "Resolved"):
        return "Invalid status", 400

    conn = db()

    conn.execute(
        "UPDATE issues SET status=? WHERE id=?",
        (status, issue_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ============================================================
# ANALYTICS
# ============================================================

@app.route("/analytics")
def analytics():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()

    locations = conn.execute(
        """SELECT location,COUNT(*) AS reports
        FROM issues
        GROUP BY location
        ORDER BY reports DESC"""
    ).fetchall()

    conn.close()

    rows = ""

    for item in locations:
        rows += """
        <tr>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>
        """ % (
            esc(item["location"]),
            item["reports"],
            priority_badge(
                priority_for(item["reports"])
            )
        )

    if not rows:
        rows = """
        <tr>
            <td colspan="3">No analytics data available.</td>
        </tr>
        """

    body = """
    <div class="card">
        <h1>📈 Inspection Analytics</h1>

        <div class="info">
            Locations with repeated issues receive higher priority.
        </div>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Total Reports</th>
                    <th>Priority</th>
                </tr>
                %s
            </table>
        </div>
    </div>
    """ % rows

    return page(body, "Analytics")


# ============================================================
# CCTV MONITORING
# ============================================================

@app.route("/cctv", methods=["GET", "POST"])
def cctv():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()
    message = ""

    if request.method == "POST":

        location = request.form.get(
            "location", ""
        ).strip()

        feed_url = request.form.get(
            "feed_url", ""
        ).strip()

        if not location or not feed_url:

            message = """
            <div class="info error">
                Please enter both location and monitoring URL.
            </div>
            """

        else:

            conn.execute(
                """INSERT INTO cctv_feeds
                (location,feed_url,created_at)
                VALUES(?,?,?)""",
                (
                    location,
                    feed_url,
                    now()
                )
            )

            conn.commit()

            message = """
            <div class="info success">
                📹 CCTV monitoring source added successfully.
            </div>
            """

    feeds = conn.execute(
        "SELECT * FROM cctv_feeds ORDER BY id DESC"
    ).fetchall()

    conn.close()

    rows = ""

    for feed in feeds:
        rows += """
        <tr>
            <td>📹 %s</td>
            <td>%s</td>
            <td>
                <a class="btn btn-purple"
                   href="%s"
                   target="_blank"
                   rel="noopener">
                    Open Monitoring
                </a>
            </td>
        </tr>
        """ % (
            esc(feed["location"]),
            esc(feed["created_at"]),
            esc(feed["feed_url"])
        )

    if not rows:
        rows = """
        <tr>
            <td colspan="3">
                No CCTV monitoring sources added yet.
            </td>
        </tr>
        """

    body = """
    <div class="card">

        <h1>📹 CCTV Monitoring Center</h1>

        <p style="color:#64748b">
            Add authorized CCTV monitoring links for centralized supervision.
        </p>

        %s

        <form method="POST" class="form-grid">

            <div class="field">
                <label>Camera Location</label>
                <input name="location"
                       placeholder="Example: Main Entrance"
                       required>
            </div>

            <div class="field">
                <label>Authorized Monitoring URL</label>
                <input type="url"
                       name="feed_url"
                       placeholder="https://..."
                       required>
            </div>

            <div class="full">
                <button class="btn btn-purple">
                    ➕ Add CCTV Source
                </button>
            </div>

        </form>

    </div>

    <div class="card">
        <h2>📺 Available Monitoring Sources</h2>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Added Time</th>
                    <th>Action</th>
                </tr>
                %s
            </table>
        </div>
    </div>
    """ % (message, rows)

    return page(body, "CCTV Monitoring")


# ============================================================
# MEETINGS
# ============================================================

@app.route("/meetings", methods=["GET", "POST"])
def meetings():

    if not logged_in():
        return redirect(url_for("login"))

    conn = db()
    message = ""

    if request.method == "POST":

        if session.get("role") != "Authority":
            conn.close()
            return "Only Authority can create meetings", 403

        title = request.form.get("title", "").strip()

        if title:

            code = uuid.uuid4().hex[:10].upper()

            conn.execute(
                """INSERT INTO meetings
                (title,meeting_code,created_at,created_by)
                VALUES(?,?,?,?)""",
                (
                    title,
                    code,
                    now(),
                    session["user_id"]
                )
            )

            conn.commit()

            message = """
            <div class="info success">
                🎥 Meeting created successfully.
                Team members can join from the meeting list.
            </div>
            """

    meetings_list = conn.execute(
        "SELECT * FROM meetings ORDER BY id DESC"
    ).fetchall()

    conn.close()

    create_form = ""

    if session.get("role") == "Authority":

        create_form = """
        <div class="card">
            <h1>🎥 Create Coordination Meeting</h1>

            <form method="POST">
                <div class="field">
                    <label>Meeting Title</label>
                    <input name="title"
                           placeholder="Inspection Review Meeting"
                           required>
                </div>

                <button class="btn btn-purple"
                        style="margin-top:15px">
                    Create Meeting
                </button>
            </form>
        </div>
        """

    rows = ""

    for meeting in meetings_list:
        rows += """
        <tr>
            <td>%s</td>
            <td>%s</td>
            <td>
                <a class="btn btn-purple"
                   href="/meeting/%s">
                   🎥 Join Room
                </a>
            </td>
        </tr>
        """ % (
            esc(meeting["title"]),
            esc(meeting["created_at"]),
            esc(meeting["meeting_code"])
        )

    if not rows:
        rows = """
        <tr>
            <td colspan="3">No meetings available.</td>
        </tr>
        """

    body = """
    %s
    %s

    <div class="card">
        <h2>🎥 Available Meetings</h2>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Meeting</th>
                    <th>Created</th>
                    <th>Join</th>
                </tr>
                %s
            </table>
        </div>
    </div>
    """ % (
        message,
        create_form,
        rows
    )

    return page(body, "Meetings")


@app.route("/meeting/<meeting_code>")
def meeting_room(meeting_code):

    if not logged_in():
        return redirect(url_for("login"))

    conn = db()

    meeting = conn.execute(
        "SELECT * FROM meetings WHERE meeting_code=?",
        (meeting_code,)
    ).fetchone()

    if not meeting:
        conn.close()
        return "Meeting not found", 404

    conn.execute(
        """INSERT INTO meeting_participants
        (meeting_id,user_id,joined_at)
        VALUES(?,?,?)""",
        (
            meeting["id"],
            session["user_id"],
            now()
        )
    )

    conn.commit()

    participants = conn.execute(
        """SELECT u.name,u.role
        FROM meeting_participants p
        JOIN users u ON p.user_id=u.id
        WHERE p.meeting_id=?
        GROUP BY u.id""",
        (meeting["id"],)
    ).fetchall()

    conn.close()

    participant_rows = ""

    for participant in participants:
        participant_rows += """
        <tr>
            <td>%s</td>
            <td>%s</td>
            <td>🟢 Joined</td>
        </tr>
        """ % (
            esc(participant["name"]),
            esc(participant["role"])
        )

    body = """
    <div class="card" style="text-align:center">

        <h1>🎥 SIMMS Coordination Room</h1>

        <div class="info success">
            🟢 You have joined the coordination room.<br><br>
            Meeting: <b>%s</b><br>
            Code: <b>%s</b>
        </div>

        <p style="color:#64748b">
            This prototype provides a coordination meeting room.
            A production version can integrate a WebRTC or
            video-conferencing service.
        </p>

        <a class="btn" href="/meetings">
            ← Back to Meetings
        </a>

    </div>

    <div class="card">
        <h2>👥 Participants</h2>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Status</th>
                </tr>
                %s
            </table>
        </div>
    </div>
    """ % (
        esc(meeting["title"]),
        esc(meeting_code),
        participant_rows
    )

    return page(body, "Meeting Room")


# ============================================================
# API - LATEST MEETING
# ============================================================

@app.route("/api/latest-meeting")
def latest_meeting():

    if not logged_in():
        return jsonify({"logged_in": False}), 401

    conn = db()

    meeting = conn.execute(
        """SELECT id,title,meeting_code,created_at
        FROM meetings
        ORDER BY id DESC LIMIT 1"""
    ).fetchone()

    conn.close()

    if not meeting:
        return jsonify({"meeting": None})

    return jsonify({
        "meeting": {
            "id": meeting["id"],
            "title": meeting["title"],
            "code": meeting["meeting_code"],
            "created_at": meeting["created_at"]
        }
    })


# ============================================================
# ERROR HANDLER
# ============================================================

@app.errorhandler(413)
def file_too_large(error):
    body = """
    <div class="card">
        <h1>⚠️ File Too Large</h1>
        <p>Please upload an image smaller than 10 MB.</p>
        <a class="btn" href="/">Go Home</a>
    </div>
    """

    return page(body, "Upload Error"), 413


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
