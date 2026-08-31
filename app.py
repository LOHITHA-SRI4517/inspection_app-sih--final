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


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "simms_secure_secret_key_change_in_production"
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


# =========================================================
# STYLING
# =========================================================

STYLE = """
<style>
*{box-sizing:border-box}

body{
    margin:0;
    font-family:Arial,Helvetica,sans-serif;
    background:#f4f7fb;
    color:#172033;
}

a{text-decoration:none;color:inherit}

.navbar{
    position:sticky;
    top:0;
    z-index:100;
    background:#ffffff;
    border-bottom:1px solid #e2e8f0;
    padding:14px 5%;
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:15px;
}

.brand{
    display:flex;
    align-items:center;
    gap:10px;
    font-size:20px;
    font-weight:800;
    color:#172554;
}

.brand-icon{
    width:40px;
    height:40px;
    border-radius:10px;
    background:#2563eb;
    color:white;
    display:grid;
    place-items:center;
}

.navlinks{
    display:flex;
    gap:5px;
    align-items:center;
    flex-wrap:wrap;
}

.navlinks a{
    padding:9px 11px;
    border-radius:8px;
    color:#475569;
    font-size:14px;
}

.navlinks a:hover{
    background:#eff6ff;
    color:#2563eb;
}

.container{
    max-width:1250px;
    margin:auto;
    padding:30px 20px;
}

.hero{
    background:linear-gradient(135deg,#eff6ff,#ffffff,#f0fdf4);
    border:1px solid #dbeafe;
    border-radius:25px;
    padding:65px 30px;
    text-align:center;
}

.hero h1{
    font-size:44px;
    color:#172554;
    max-width:900px;
    margin:0 auto 18px;
}

.hero p{
    max-width:760px;
    margin:auto;
    color:#64748b;
    line-height:1.7;
    font-size:18px;
}

.card{
    background:white;
    border:1px solid #e2e8f0;
    border-radius:18px;
    padding:24px;
    margin-bottom:22px;
    box-shadow:0 8px 25px rgba(15,23,42,.04);
}

.grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
    gap:18px;
}

.feature{
    background:white;
    border:1px solid #e2e8f0;
    border-radius:16px;
    padding:22px;
    transition:.2s;
}

.feature:hover{
    transform:translateY(-3px);
    box-shadow:0 10px 25px rgba(15,23,42,.08);
}

.feature-icon{font-size:32px}

.feature h3{
    color:#1e3a8a;
    margin:12px 0 8px;
}

.feature p{
    color:#64748b;
    line-height:1.6;
}

.btn{
    display:inline-block;
    border:none;
    background:#2563eb;
    color:white;
    padding:11px 17px;
    border-radius:9px;
    cursor:pointer;
    font-weight:bold;
    margin:3px;
}

.btn:hover{filter:brightness(.93)}

.btn-green{background:#059669}
.btn-purple{background:#7c3aed}
.btn-orange{background:#ea580c}
.btn-red{background:#dc2626}

.btn-light{
    background:#eff6ff;
    color:#2563eb;
}

.form-grid{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:15px;
}

.full{grid-column:1/-1}

.field label{
    display:block;
    margin-bottom:6px;
    font-weight:bold;
    color:#334155;
}

input,select,textarea{
    width:100%;
    padding:12px;
    border:1px solid #cbd5e1;
    border-radius:9px;
    font-size:15px;
}

textarea{
    min-height:110px;
    resize:vertical;
}

.info{
    background:#eff6ff;
    border-left:5px solid #2563eb;
    padding:14px;
    border-radius:8px;
    margin:15px 0;
    line-height:1.6;
}

.success{
    background:#ecfdf5;
    border-left-color:#059669;
}

.warning{
    background:#fff7ed;
    border-left-color:#ea580c;
}

.error{
    background:#fef2f2;
    border-left-color:#dc2626;
}

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
    gap:15px;
    margin:20px 0;
}

.stat{
    background:white;
    padding:20px;
    border-radius:15px;
    border:1px solid #e2e8f0;
}

.num{
    font-size:30px;
    font-weight:bold;
    color:#2563eb;
}

.table-wrap{overflow:auto}

table{
    width:100%;
    border-collapse:collapse;
    min-width:700px;
}

th{
    background:#172554;
    color:white;
}

th,td{
    padding:12px;
    text-align:left;
    border-bottom:1px solid #e5e7eb;
}

.badge{
    padding:5px 9px;
    border-radius:999px;
    font-size:12px;
    font-weight:bold;
}

.low{background:#dcfce7;color:#166534}
.medium{background:#fef3c7;color:#92400e}
.high{background:#fee2e2;color:#991b1b}

.evidence{
    width:90px;
    height:65px;
    object-fit:cover;
    border-radius:8px;
}

.camera{
    width:100%;
    min-height:280px;
    background:#111827;
    border-radius:12px;
    object-fit:cover;
}

.login-box{
    max-width:480px;
    margin:45px auto;
}

.workflow{
    display:flex;
    flex-wrap:wrap;
    justify-content:center;
    align-items:center;
    gap:8px;
}

.step{
    background:#eff6ff;
    color:#1e3a8a;
    padding:10px 14px;
    border-radius:9px;
    font-weight:bold;
}

.footer{
    text-align:center;
    padding:30px;
    color:#64748b;
}

@media(max-width:700px){
    .navbar{
        flex-direction:column;
        align-items:flex-start;
    }

    .hero{padding:40px 18px}

    .hero h1{font-size:30px}

    .form-grid{grid-template-columns:1fr}

    .full{grid-column:auto}

    .container{padding:18px 12px}
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

<footer class="footer">
    SIMMS • Smart Real-Time Monitoring & Inspection System
</footer>

</body>
</html>
"""


# =========================================================
# HELPER FUNCTIONS
# =========================================================

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
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def esc(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def priority_for(count):
    if count > 3:
        return "High"
    elif count >= 2:
        return "Medium"
    return "Low"


def badge(priority):
    classes = {
        "Low": "low",
        "Medium": "medium",
        "High": "high"
    }

    return (
        '<span class="badge '
        + classes.get(priority, "low")
        + '">'
        + esc(priority)
        + '</span>'
    )


def nav():
    if not logged_in():
        return """
        <div class="navbar">
            <a class="brand" href="/">
                <span class="brand-icon">🏛️</span>
                SIMMS
            </a>
            <div class="navlinks">
                <a href="/">Home</a>
                <a href="/login">🔐 Login</a>
            </div>
        </div>
        """

    links = [
        '<a href="/home">🏠 Home</a>',
        '<a href="/dashboard">📊 Dashboard</a>',
        '<a href="/meetings">🎥 Meetings</a>'
    ]

    if session.get("role") in ("Worker", "Inspector"):
        links.append('<a href="/my-assignments">📋 Assignments</a>')

    if session.get("role") == "Authority":
        links.extend([
            '<a href="/users">👥 Users</a>',
            '<a href="/assignments">🎲 Assign</a>',
            '<a href="/analytics">📈 Analytics</a>',
            '<a href="/cctv">📹 CCTV</a>'
        ])

    links.append('<a href="/logout">🚪 Logout</a>')

    return (
        '<div class="navbar">'
        '<a class="brand" href="/home">'
        '<span class="brand-icon">🏛️</span> SIMMS</a>'
        '<div class="navlinks">'
        + "".join(links)
        + "</div></div>"
    )


def page(body, title="SIMMS"):
    return render_template_string(
        STYLE + LAYOUT,
        body=body,
        navbar=nav(),
        title=title
    )


# =========================================================
# DATABASE
# =========================================================

def init_db():
    conn = db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS assignments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        location TEXT NOT NULL,
        assigned_at TEXT NOT NULL,
        status TEXT DEFAULT 'Assigned',
        face_verified INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS issues(
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

    CREATE TABLE IF NOT EXISTS cctv_feeds(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location TEXT NOT NULL,
        feed_url TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS meetings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        meeting_code TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL,
        created_by INTEGER
    );
    """)

    # Demo accounts exist internally for testing,
    # but are NOT displayed anywhere in the interface.
    defaults = [
        ("ADMIN001", "System Authority", "admin123", "Authority"),
        ("INS001", "Inspection Officer", "inspector123", "Inspector"),
        ("WORK001", "Field Worker", "worker123", "Worker")
    ]

    for uid, name, password, role in defaults:
        existing = conn.execute(
            "SELECT id FROM users WHERE unique_id=?",
            (uid,)
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO users
                (unique_id,name,password,role,created_at)
                VALUES(?,?,?,?,?)
                """,
                (
                    uid,
                    name,
                    generate_password_hash(password),
                    role,
                    now()
                )
            )

    conn.commit()
    conn.close()


init_db()


# =========================================================
# FRONT PAGE
# =========================================================

@app.route("/")
def landing():

    body = """
    <section class="hero">
        <div style="font-weight:bold;color:#2563eb;margin-bottom:15px">
            SMART DIGITAL INSPECTION PLATFORM
        </div>

        <h1>Smart Real-Time Monitoring & Inspection System</h1>

        <p>
            A centralized platform for intelligent inspection management,
            real-time monitoring, CCTV integration, geo-tagged evidence
            and faster corrective action.
        </p>

        <div style="margin-top:25px">
            <a class="btn" href="/login">🔐 Access System</a>
            <a class="btn btn-light" href="#features">Explore Features</a>
        </div>
    </section>

    <section id="features" style="margin-top:25px">

        <div style="text-align:center;margin-bottom:22px">
            <h2 style="color:#172554">Powerful Smart Monitoring Features</h2>
            <p style="color:#64748b">
                One platform connecting authorities, inspectors and field workers.
            </p>
        </div>

        <div class="grid">

            <div class="feature">
                <div class="feature-icon">🎲</div>
                <h3>Smart Assignment</h3>
                <p>
                    Inspection duties can be randomly assigned to reduce
                    predictable inspections and improve transparency.
                </p>
            </div>

            <div class="feature">
                <div class="feature-icon">📋</div>
                <h3>Digital Inspection Forms</h3>
                <p>
                    Workers and inspectors can submit field observations
                    using structured inspection forms.
                </p>
            </div>

            <div class="feature">
                <div class="feature-icon">📷</div>
                <h3>Evidence Capture</h3>
                <p>
                    Capture photographic evidence directly during inspections
                    for better reporting and verification.
                </p>
            </div>

            <div class="feature">
                <div class="feature-icon">📍</div>
                <h3>Geo-Tagged Reports</h3>
                <p>
                    GPS coordinates can be attached to inspection reports
                    to improve location-based accountability.
                </p>
            </div>

            <div class="feature">
                <div class="feature-icon">📹</div>
                <h3>CCTV Monitoring</h3>
                <p>
                    Authorities can centrally manage authorized CCTV monitoring
                    feeds for real-time situational awareness.
                </p>
            </div>

            <div class="feature">
                <div class="feature-icon">📊</div>
                <h3>Live Dashboard</h3>
                <p>
                    Track reported issues, priorities and corrective actions
                    from a centralized monitoring dashboard.
                </p>
            </div>

        </div>
    </section>

    <div class="card" style="margin-top:25px;text-align:center">
        <h2>🔄 Smart Inspection Workflow</h2>
        <div class="workflow">
            <span class="step">1. Assign</span>
            →
            <span class="step">2. Verify</span>
            →
            <span class="step">3. Inspect</span>
            →
            <span class="step">4. Capture Evidence</span>
            →
            <span class="step">5. Monitor</span>
            →
            <span class="step">6. Resolve</span>
        </div>
    </div>
    """

    return page(body, "SIMMS | Smart Inspection System")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if logged_in():
        return redirect(url_for("home"))

    error = ""

    if request.method == "POST":
        uid = request.form.get("unique_id", "").strip().upper()
        password = request.form.get("password", "")

        conn = db()

        user = conn.execute(
            "SELECT * FROM users WHERE unique_id=?",
            (uid,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        error = """
        <div class="info error">
            ❌ Invalid Unique ID or Password.
        </div>
        """

    body = """
    <div class="card login-box">

        <div style="text-align:center">
            <div class="brand-icon" style="margin:auto">🔐</div>
            <h1 style="color:#172554">Secure System Login</h1>
            <p style="color:#64748b">
                Sign in to access your SIMMS workspace.
            </p>
        </div>

        """ + error + """

        <form method="POST">

            <div class="field">
                <label>Unique ID</label>
                <input
                    name="unique_id"
                    placeholder="Enter your Unique ID"
                    required
                >
            </div>

            <br>

            <div class="field">
                <label>Password</label>
                <input
                    type="password"
                    name="password"
                    placeholder="Enter your password"
                    required
                >
            </div>

            <div style="text-align:right;margin-top:8px">
                <a
                    href="/forgot-password"
                    style="color:#2563eb;font-size:14px"
                >
                    Forgot Password?
                </a>
            </div>

            <button
                class="btn"
                style="width:100%;margin-top:15px"
            >
                Login →
            </button>

        </form>

        <div style="text-align:center;margin-top:18px">
            <a href="/">← Back to Home</a>
        </div>

    </div>
    """

    return page(body, "Login | SIMMS")


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    message = ""

    if request.method == "POST":

        uid = request.form.get("unique_id", "").strip().upper()
        new_password = request.form.get("new_password", "")

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
                (uid,)
            ).fetchone()

            if user:
                conn.execute(
                    "UPDATE users SET password=? WHERE unique_id=?",
                    (
                        generate_password_hash(new_password),
                        uid
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

        <div style="text-align:center">
            <div class="brand-icon" style="margin:auto">🔑</div>
            <h1 style="color:#172554">Forgot Password</h1>
            <p style="color:#64748b">
                Reset your SIMMS account password.
            </p>
        </div>

        """ + message + """

        <form method="POST">

            <div class="field">
                <label>Unique ID</label>
                <input name="unique_id" required>
            </div>

            <br>

            <div class="field">
                <label>New Password</label>
                <input
                    type="password"
                    name="new_password"
                    minlength="4"
                    required
                >
            </div>

            <button
                class="btn btn-purple"
                style="width:100%;margin-top:15px"
            >
                🔑 Reset Password
            </button>

        </form>

        <div style="text-align:center;margin-top:18px">
            <a href="/login">← Back to Login</a>
        </div>

    </div>
    """

    return page(body, "Forgot Password | SIMMS")


# =========================================================
# LOGOUT AND HOME
# =========================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/home")
def home():

    if not logged_in():
        return redirect(url_for("login"))

    role = session["role"]

    buttons = '<a class="btn" href="/dashboard">📊 Dashboard</a>'

    if role in ("Worker", "Inspector"):
        buttons += """
        <a class="btn btn-purple" href="/my-assignments">
            📋 My Assignments
        </a>
        """

    if role == "Authority":
        buttons += """
        <a class="btn btn-orange" href="/assignments">
            🎲 Assign Inspection
        </a>
        <a class="btn btn-purple" href="/cctv">
            📹 CCTV Monitoring
        </a>
        <a class="btn btn-green" href="/analytics">
            📈 Analytics
        </a>
        """

    body = """
    <div class="card">
        <h1>Welcome, """ + esc(session["name"]) + """ 👋</h1>

        <p style="color:#64748b">
            You are logged in as <b>""" + esc(role) + """</b>
        </p>

        <div class="info">
            🔐 Role-based access control is active.
            Your workspace features are based on your role.
        </div>

        <div>""" + buttons + """</div>
    </div>

    <div class="card">
        <h2>🎯 Inspection Workflow</h2>
        <div class="workflow">
            <span class="step">Assign</span> →
            <span class="step">Verify</span> →
            <span class="step">Inspect</span> →
            <span class="step">Evidence</span> →
            <span class="step">Monitor</span> →
            <span class="step">Resolve</span>
        </div>
    </div>
    """

    return page(body, "Home | SIMMS")


# =========================================================
# ASSIGNMENTS
# =========================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not role_required("Authority"):
        return "Access denied", 403

    message = ""
    conn = db()

    workers = conn.execute("""
        SELECT id,name,unique_id
        FROM users
        WHERE role IN ('Worker','Inspector')
    """).fetchall()

    if request.method == "POST":

        location = request.form.get("location", "").strip()

        if not location:
            message = '<div class="info warning">Enter a location.</div>'

        elif not workers:
            message = """
            <div class="info warning">
                No Workers or Inspectors are available.
            </div>
            """

        else:
            selected = random.choice(workers)

            conn.execute("""
                INSERT INTO assignments
                (user_id,location,assigned_at,status,face_verified)
                VALUES(?,?,?,?,?)
            """, (
                selected["id"],
                location,
                now(),
                "Assigned",
                0
            ))

            conn.commit()

            message = """
            <div class="info success">
                ✅ Inspection assigned successfully to
                <b>""" + esc(selected["name"]) + """</b>.
            </div>
            """

    rows = conn.execute("""
        SELECT a.*,u.name,u.unique_id
        FROM assignments a
        JOIN users u ON a.user_id=u.id
        ORDER BY a.id DESC
    """).fetchall()

    conn.close()

    table_rows = ""

    for row in rows:
        table_rows += """
        <tr>
            <td>📍 """ + esc(row["location"]) + """</td>
            <td>""" + esc(row["name"]) + """</td>
            <td>""" + esc(row["assigned_at"]) + """</td>
            <td>""" + esc(row["status"]) + """</td>
        </tr>
        """

    body = """
    <div class="card">
        <h1>🎲 Smart Inspection Assignment</h1>

        <p style="color:#64748b">
            Randomly assign inspection duties to eligible field personnel.
        </p>

        """ + message + """

        <form method="POST">

            <div class="field">
                <label>Inspection Location</label>
                <input
                    name="location"
                    placeholder="Enter location to inspect"
                    required
                >
            </div>

            <button class="btn btn-purple">
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
                """ + (
                    table_rows if table_rows else
                    '<tr><td colspan="4">No assignments yet.</td></tr>'
                ) + """
            </table>
        </div>
    </div>
    """

    return page(body, "Assignments | SIMMS")


# =========================================================
# WORKER ASSIGNMENTS
# =========================================================

@app.route("/my-assignments")
def my_assignments():

    if (
        not logged_in()
        or session.get("role") not in ("Worker", "Inspector")
    ):
        return "Access denied", 403

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM assignments
        WHERE user_id=?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    table_rows = ""

    for row in rows:

        if row["status"] == "Completed":
            action = '<span class="badge low">Completed</span>'

        elif row["face_verified"]:
            action = (
                '<a class="btn btn-green" href="/inspection/'
                + str(row["id"])
                + '">📋 Start Inspection</a>'
            )

        else:
            action = (
                '<a class="btn btn-purple" href="/face-verification/'
                + str(row["id"])
                + '">📷 Verify & Start</a>'
            )

        table_rows += """
        <tr>
            <td>📍 """ + esc(row["location"]) + """</td>
            <td>""" + esc(row["assigned_at"]) + """</td>
            <td>""" + esc(row["status"]) + """</td>
            <td>""" + action + """</td>
        </tr>
        """

    body = """
    <div class="card">
        <h1>📋 My Inspection Assignments</h1>

        <div class="info">
            Complete the verification step before starting your field inspection.
        </div>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Assigned Time</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
                """ + (
                    table_rows if table_rows else
                    '<tr><td colspan="4">No assignments available.</td></tr>'
                ) + """
            </table>
        </div>
    </div>
    """

    return page(body, "My Assignments | SIMMS")


# =========================================================
# CAMERA VERIFICATION
# =========================================================

@app.route("/face-verification/<int:assignment_id>", methods=["GET", "POST"])
def face_verification(assignment_id):

    if (
        not logged_in()
        or session.get("role") not in ("Worker", "Inspector")
    ):
        return "Access denied", 403

    conn = db()

    assignment = conn.execute("""
        SELECT *
        FROM assignments
        WHERE id=? AND user_id=? AND status='Assigned'
    """, (
        assignment_id,
        session["user_id"]
    )).fetchone()

    if not assignment:
        conn.close()
        return "Invalid assignment", 403

    if request.method == "POST":

        photo = request.files.get("face_photo")

        if not photo or not photo.filename:
            conn.close()
            return "Please capture a verification photo.", 400

        if not allowed_file(photo.filename):
            conn.close()
            return "Invalid image format.", 400

        filename = "verification_" + uuid.uuid4().hex + ".jpg"

        photo.save(os.path.join(FACE_FOLDER, filename))

        conn.execute("""
            UPDATE assignments
            SET face_verified=1
            WHERE id=? AND user_id=?
        """, (
            assignment_id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect(
            url_for("inspection", assignment_id=assignment_id)
        )

    location = assignment["location"]
    conn.close()

    # IMPORTANT: This HTML is NOT an f-string.
    # Therefore JavaScript braces will never cause the previous syntax error.
    body = """
    <div class="card" style="max-width:700px;margin:auto">

        <h1>📷 Identity Verification</h1>

        <div class="info">
            Inspection Location: <b>""" + esc(location) + """</b><br>
            Capture a camera photo to continue to the inspection form.
        </div>

        <video
            id="video"
            class="camera"
            autoplay
            playsinline
        ></video>

        <canvas id="canvas" hidden></canvas>

        <form
            id="faceForm"
            method="POST"
            enctype="multipart/form-data"
        >
            <input
                id="face_photo"
                name="face_photo"
                type="file"
                accept="image/*"
                hidden
            >

            <button
                type="button"
                class="btn btn-purple"
                onclick="captureFace()"
                style="margin-top:15px"
            >
                📸 Capture & Continue
            </button>
        </form>

        <p id="message"></p>
    </div>

    <script>
    const video = document.getElementById("video");

    navigator.mediaDevices.getUserMedia({video:true})
    .then(function(stream) {
        video.srcObject = stream;
    })
    .catch(function() {
        document.getElementById("message").innerText =
            "Camera permission was denied. Please allow camera access.";
    });

    function captureFace() {

        if (!video.videoWidth) {
            alert("Please wait for the camera to start.");
            return;
        }

        const canvas = document.getElementById("canvas");

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        canvas.getContext("2d").drawImage(
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
                {type:"image/jpeg"}
            );

            const data = new DataTransfer();
            data.items.add(file);

            document.getElementById("face_photo").files =
                data.files;

            if (video.srcObject) {
                video.srcObject.getTracks().forEach(function(track) {
                    track.stop();
                });
            }

            document.getElementById("faceForm").submit();

        }, "image/jpeg");
    }
    </script>
    """

    return page(body, "Verification | SIMMS")


# =========================================================
# INSPECTION FORM
# =========================================================

@app.route("/inspection/<int:assignment_id>", methods=["GET", "POST"])
def inspection(assignment_id):

    if (
        not logged_in()
        or session.get("role") not in ("Worker", "Inspector")
    ):
        return "Access denied", 403

    conn = db()

    assignment = conn.execute("""
        SELECT *
        FROM assignments
        WHERE id=?
        AND user_id=?
        AND face_verified=1
        AND status='Assigned'
    """, (
        assignment_id,
        session["user_id"]
    )).fetchone()

    if not assignment:
        conn.close()
        return "Inspection access denied", 403

    if request.method == "POST":

        location = assignment["location"]

        cleanliness = request.form.get("cleanliness", "Yes")
        safety = request.form.get("safety", "Yes")
        facilities = request.form.get("facilities", "Yes")

        description = request.form.get(
            "description", ""
        ).strip()

        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()

        photo_name = None
        photo = request.files.get("photo")

        if photo and photo.filename:

            if not allowed_file(photo.filename):
                conn.close()
                return "Invalid photo format.", 400

            extension = secure_filename(
                photo.filename
            ).rsplit(".", 1)[-1].lower()

            photo_name = uuid.uuid4().hex + "." + extension

            photo.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    photo_name
                )
            )

        detected = []

        if cleanliness == "No":
            detected.append("Cleanliness")

        if safety == "No":
            detected.append("Safety")

        if facilities == "No":
            detected.append("Facilities")

        for issue_type in detected:

            previous_count = conn.execute("""
                SELECT COUNT(*)
                FROM issues
                WHERE LOWER(location)=LOWER(?)
            """, (location,)).fetchone()[0]

            priority = priority_for(previous_count + 1)

            conn.execute("""
                INSERT INTO issues(
                    location,
                    issue_type,
                    description,
                    created_at,
                    status,
                    priority,
                    photo,
                    reporter_id,
                    latitude,
                    longitude,
                    verified
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (
                location,
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
            ))

        conn.execute("""
            UPDATE assignments
            SET status='Completed'
            WHERE id=?
        """, (assignment_id,))

        conn.commit()
        conn.close()

        result = (
            "⚠️ Issues reported: " + ", ".join(detected)
            if detected
            else "✅ Inspection completed successfully. No issues found."
        )

        body = """
        <div class="card" style="text-align:center">
            <h1>Inspection Submitted Successfully ✅</h1>

            <div class="info success">
                """ + esc(result) + """
            </div>

            <a class="btn" href="/my-assignments">
                📋 My Assignments
            </a>
        </div>
        """

        return page(body, "Inspection Submitted")

    location = assignment["location"]
    conn.close()

    body = """
    <div class="card">

        <h1>📋 Field Inspection Form</h1>

        <div class="info">
            📍 Assigned Location: <b>""" + esc(location) + """</b>
        </div>

        <form
            method="POST"
            enctype="multipart/form-data"
            class="form-grid"
        >

            <div class="field">
                <label>🧹 Is the area clean?</label>
                <select name="cleanliness">
                    <option>Yes</option>
                    <option>No</option>
                </select>
            </div>

            <div class="field">
                <label>🛡️ Is the area safe?</label>
                <select name="safety">
                    <option>Yes</option>
                    <option>No</option>
                </select>
            </div>

            <div class="field">
                <label>🏢 Are facilities working?</label>
                <select name="facilities">
                    <option>Yes</option>
                    <option>No</option>
                </select>
            </div>

            <div class="field">
                <label>📸 Photo Evidence</label>
                <input
                    type="file"
                    name="photo"
                    accept="image/*"
                >
            </div>

            <div class="field">
                <label>Latitude</label>
                <input
                    id="latitude"
                    name="latitude"
                    placeholder="Latitude"
                >
            </div>

            <div class="field">
                <label>Longitude</label>
                <input
                    id="longitude"
                    name="longitude"
                    placeholder="Longitude"
                >
            </div>

            <div class="full">
                <button
                    type="button"
                    class="btn btn-purple"
                    onclick="getLocation()"
                >
                    📍 Get Current Location
                </button>
            </div>

            <div class="field full">
                <label>📝 Observation / Description</label>
                <textarea
                    name="description"
                    placeholder="Describe your observation..."
                ></textarea>
            </div>

            <div class="full">
                <button class="btn" type="submit">
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
    """

    return page(body, "Inspection Form | SIMMS")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():
        return redirect(url_for("login"))

    conn = db()

    query = """
        SELECT i.*,u.name AS reporter_name
        FROM issues i
        LEFT JOIN users u ON i.reporter_id=u.id
    """

    params = ()

    if session["role"] != "Authority":
        query += " WHERE i.reporter_id=?"
        params = (session["user_id"],)

    query += " ORDER BY i.id DESC"

    issues = conn.execute(query, params).fetchall()
    conn.close()

    total = len(issues)
    reported = sum(x["status"] == "Reported" for x in issues)
    progress = sum(x["status"] == "In Progress" for x in issues)
    resolved = sum(x["status"] == "Resolved" for x in issues)

    table_rows = ""

    for issue in issues:

        photo = "—"

        if issue["photo"]:
            photo = (
                '<a target="_blank" href="/uploads/'
                + esc(issue["photo"])
                + '"><img class="evidence" src="/uploads/'
                + esc(issue["photo"])
                + '"></a>'
            )

        action = "View Only"

        if session["role"] == "Authority":

            if issue["status"] == "Reported":
                action = (
                    '<a class="btn btn-orange" href="/update/'
                    + str(issue["id"])
                    + '/In%20Progress">Start</a>'
                )

            elif issue["status"] == "In Progress":
                action = (
                    '<a class="btn btn-green" href="/update/'
                    + str(issue["id"])
                    + '/Resolved">Resolve</a>'
                )

            else:
                action = "✅ Resolved"

        table_rows += """
        <tr>
            <td>""" + esc(issue["location"]) + """</td>
            <td>""" + esc(issue["issue_type"]) + """</td>
            <td>""" + (esc(issue["description"]) or "-") + """</td>
            <td>""" + badge(issue["priority"]) + """</td>
            <td>""" + photo + """</td>
            <td>""" + esc(issue["status"]) + """</td>
            <td>""" + action + """</td>
        </tr>
        """

    body = """
    <h1>📊 Real-Time Monitoring Dashboard</h1>

    <div class="stats">
        <div class="stat">
            <div class="num">""" + str(total) + """</div>
            Total Issues
        </div>

        <div class="stat">
            <div class="num">""" + str(reported) + """</div>
            Reported
        </div>

        <div class="stat">
            <div class="num">""" + str(progress) + """</div>
            In Progress
        </div>

        <div class="stat">
            <div class="num">""" + str(resolved) + """</div>
            Resolved
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
                """ + (
                    table_rows if table_rows else
                    '<tr><td colspan="7">No issues reported yet.</td></tr>'
                ) + """
            </table>
        </div>
    </div>
    """

    return page(body, "Dashboard | SIMMS")


# =========================================================
# UPDATE ISSUE STATUS
# =========================================================

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


# =========================================================
# CCTV MONITORING
# =========================================================

@app.route("/cctv", methods=["GET", "POST"])
def cctv():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()
    message = ""

    if request.method == "POST":

        location = request.form.get("location", "").strip()
        feed_url = request.form.get("feed_url", "").strip()

        if not location or not feed_url:

            message = """
            <div class="info warning">
                Please enter both CCTV location and feed URL.
            </div>
            """

        else:

            conn.execute("""
                INSERT INTO cctv_feeds(
                    location,feed_url,created_at
                )
                VALUES(?,?,?)
            """, (
                location,
                feed_url,
                now()
            ))

            conn.commit()

            message = """
            <div class="info success">
                📹 CCTV feed added successfully.
            </div>
            """

    feeds = conn.execute("""
        SELECT *
        FROM cctv_feeds
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    table_rows = ""

    for feed in feeds:
        table_rows += """
        <tr>
            <td>📹 """ + esc(feed["location"]) + """</td>
            <td>""" + esc(feed["created_at"]) + """</td>
            <td>
                <a
                    class="btn"
                    href="""" + esc(feed["feed_url"]) + """
                    target="_blank"
                    rel="noopener"
                >
                    📺 Open Monitoring Feed
                </a>
            </td>
        </tr>
        """

    body = """
    <div class="card">

        <h1>📹 CCTV Monitoring Center</h1>

        <div class="info">
            Centralized access to authorized CCTV monitoring feeds.
            This module is restricted to authorized personnel.
        </div>

        """ + message + """

        <form method="POST" class="form-grid">

            <div class="field">
                <label>Camera Location</label>
                <input
                    name="location"
                    placeholder="Example: Main Entrance"
                    required
                >
            </div>

            <div class="field">
                <label>Authorized CCTV / Monitoring URL</label>
                <input
                    type="url"
                    name="feed_url"
                    placeholder="https://..."
                    required
                >
            </div>

            <div class="full">
                <button class="btn btn-purple">
                    ➕ Add CCTV Feed
                </button>
            </div>

        </form>
    </div>

    <div class="card">

        <h2>📺 Available Monitoring Feeds</h2>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Added Time</th>
                    <th>Monitoring</th>
                </tr>
                """ + (
                    table_rows if table_rows else
                    '<tr><td colspan="3">No CCTV feeds configured.</td></tr>'
                ) + """
            </table>
        </div>

    </div>
    """

    return page(body, "CCTV Monitoring | SIMMS")


# =========================================================
# ANALYTICS
# =========================================================

@app.route("/analytics")
def analytics():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()

    locations = conn.execute("""
        SELECT location,COUNT(*) AS reports
        FROM issues
        GROUP BY location
        ORDER BY reports DESC
    """).fetchall()

    conn.close()

    rows = ""

    for item in locations:
        rows += """
        <tr>
            <td>""" + esc(item["location"]) + """</td>
            <td>""" + str(item["reports"]) + """</td>
            <td>""" + badge(priority_for(item["reports"])) + """</td>
        </tr>
        """

    body = """
    <div class="card">
        <h1>📈 Inspection Analytics</h1>

        <div class="info">
            Locations with repeated reports are automatically highlighted
            with higher priority.
        </div>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Total Reports</th>
                    <th>Priority</th>
                </tr>
                """ + (
                    rows if rows else
                    '<tr><td colspan="3">No analytics data available.</td></tr>'
                ) + """
            </table>
        </div>
    </div>
    """

    return page(body, "Analytics | SIMMS")


# =========================================================
# USER MANAGEMENT
# =========================================================

@app.route("/users")
def users():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()

    users_list = conn.execute("""
        SELECT unique_id,name,role,created_at
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for user in users_list:
        rows += """
        <tr>
            <td>""" + esc(user["unique_id"]) + """</td>
            <td>""" + esc(user["name"]) + """</td>
            <td>""" + esc(user["role"]) + """</td>
            <td>""" + esc(user["created_at"]) + """</td>
        </tr>
        """

    body = """
    <div class="card">
        <h1>👥 Registered System Users</h1>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Unique ID</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Created</th>
                </tr>
                """ + rows + """
            </table>
        </div>
    </div>
    """

    return page(body, "Users | SIMMS")


# =========================================================
# MEETINGS
# =========================================================

@app.route("/meetings", methods=["GET", "POST"])
def meetings():

    if not logged_in():
        return redirect(url_for("login"))

    conn = db()
    message = ""

    if request.method == "POST":

        if session["role"] != "Authority":
            conn.close()
            return "Only Authority can create meetings", 403

        title = request.form.get("title", "").strip()

        if title:

            code = uuid.uuid4().hex[:8].upper()

            conn.execute("""
                INSERT INTO meetings(
                    title,meeting_code,created_at,created_by
                )
                VALUES(?,?,?,?)
            """, (
                title,
                code,
                now(),
                session["user_id"]
            ))

            conn.commit()

            message = """
            <div class="info success">
                🎥 Meeting created successfully.
            </div>
            """

    meetings_list = conn.execute("""
        SELECT *
        FROM meetings
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    create_form = ""

    if session["role"] == "Authority":
        create_form = """
        <div class="card">
            <h1>🎥 Create Coordination Meeting</h1>

            <form method="POST">
                <div class="field">
                    <label>Meeting Title</label>
                    <input
                        name="title"
                        placeholder="Inspection Review Meeting"
                        required
                    >
                </div>

                <button class="btn btn-purple">
                    Create Meeting
                </button>
            </form>
        </div>
        """

    rows = ""

    for meeting in meetings_list:
        rows += """
        <tr>
            <td>""" + esc(meeting["title"]) + """</td>
            <td>""" + esc(meeting["created_at"]) + """</td>
            <td>
                <a class="btn btn-purple" href="/meeting/""" + esc(meeting["meeting_code"]) + """">
                    Join
                </a>
            </td>
        </tr>
        """

    body = (
        message
        + create_form
        + """
        <div class="card">
            <h2>🎥 Available Meetings</h2>

            <div class="table-wrap">
                <table>
                    <tr>
                        <th>Meeting</th>
                        <th>Created</th>
                        <th>Action</th>
                    </tr>
                    """
        + (
            rows if rows else
            '<tr><td colspan="3">No meetings available.</td></tr>'
        )
        + """
                </table>
            </div>
        </div>
        """
    )

    return page(body, "Meetings | SIMMS")


@app.route("/meeting/<meeting_code>")
def meeting_room(meeting_code):

    if not logged_in():
        return redirect(url_for("login"))

    conn = db()

    meeting = conn.execute("""
        SELECT *
        FROM meetings
        WHERE meeting_code=?
    """, (meeting_code,)).fetchone()

    conn.close()

    if not meeting:
        return "Meeting not found", 404

    body = """
    <div class="card" style="text-align:center">

        <h1>🎥 Inspection Coordination Room</h1>

        <div class="info success">
            You joined the meeting successfully.<br><br>
            <b>""" + esc(meeting["title"]) + """</b>
        </div>

        <p style="color:#64748b">
            This prototype meeting room can be integrated with a WebRTC
            or video conferencing service in a production system.
        </p>

        <a class="btn" href="/meetings">
            ← Back to Meetings
        </a>

    </div>
    """

    return page(body, "Meeting Room | SIMMS")


# =========================================================
# FILE ACCESS
# =========================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# =========================================================
# API
# =========================================================

@app.route("/api/status")
def api_status():
    return jsonify({
        "system": "SIMMS",
        "status": "running",
        "time": now()
    })


# =========================================================
# ERROR HANDLER
# =========================================================

@app.errorhandler(413)
def file_too_large(error):
    return page("""
        <div class="card">
            <h1>File Too Large</h1>
            <p>Please upload an image smaller than 10 MB.</p>
        </div>
    """, "Upload Error"), 413


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
