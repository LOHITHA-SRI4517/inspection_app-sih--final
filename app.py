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
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "simms_secure_secret_key_2026"
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
# CSS STYLE
# =========================================================

STYLE = """
<style>
*{
    box-sizing:border-box;
}

body{
    margin:0;
    font-family:Arial, Helvetica, sans-serif;
    background:#f4f6fa;
    color:#24334d;
}

a{
    text-decoration:none;
    color:inherit;
}

/* NAVBAR */

.navbar{
    min-height:57px;
    background:linear-gradient(90deg,#202b49,#3659b5);
    color:white;
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0 7%;
}

.brand{
    font-size:18px;
    font-weight:bold;
}

.navlinks{
    display:flex;
    align-items:center;
    gap:5px;
    flex-wrap:wrap;
}

.navlinks a{
    padding:17px 10px;
    font-weight:bold;
    font-size:14px;
}

.navlinks a:hover{
    background:rgba(255,255,255,.12);
}

/* CONTAINER */

.container{
    max-width:1250px;
    margin:auto;
    padding:30px 20px;
}

/* LANDING PAGE */

.landing{
    min-height:calc(100vh - 57px);
    padding-top:100px;
    background:
        radial-gradient(circle at center, #f8f9fc 0%, #e9edf5 45%, #d5dae4 100%);
}

.hero{
    text-align:center;
    padding:10px 20px 80px;
}

.hero h1{
    font-size:44px;
    color:#294477;
    margin:0 0 25px;
    letter-spacing:.3px;
}

.hero p{
    font-size:18px;
    margin:0 auto 25px;
    color:#3f4b5e;
}

.login-button{
    background:#3262ba;
    color:white;
    border:0;
    border-radius:9px;
    padding:14px 24px;
    font-size:15px;
    cursor:pointer;
    box-shadow:0 5px 12px rgba(30,70,150,.2);
}

.login-button:hover{
    background:#274f9a;
}

/* FEATURE CARDS */

.features{
    max-width:1210px;
    margin:auto;
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:18px;
    padding:0 20px 60px;
}

.feature{
    background:rgba(255,255,255,.86);
    border-radius:18px;
    padding:27px 23px;
    min-height:187px;
    box-shadow:0 8px 22px rgba(50,65,90,.10);
    border:1px solid rgba(255,255,255,.7);
}

.feature h3{
    color:#30466e;
    font-size:19px;
    margin:0 0 18px;
}

.feature p{
    color:#3d4757;
    line-height:1.35;
    margin:0;
    font-size:16px;
}

/* GENERAL CARDS */

.card{
    background:white;
    border-radius:16px;
    padding:25px;
    margin-bottom:22px;
    box-shadow:0 5px 20px rgba(30,40,60,.07);
    border:1px solid #e5e9f1;
}

.card h1,
.card h2{
    color:#263f70;
    margin-top:0;
}

.info{
    background:#edf4ff;
    border-left:5px solid #3972d3;
    padding:14px;
    border-radius:8px;
    margin:15px 0;
    line-height:1.6;
}

.success{
    background:#eafaf1;
    border-left-color:#16a065;
}

.warning{
    background:#fff6e6;
    border-left-color:#e99122;
}

.error{
    color:#c0392b;
    font-weight:bold;
}

/* BUTTONS */

.btn{
    display:inline-block;
    border:0;
    padding:11px 17px;
    border-radius:8px;
    background:#3262ba;
    color:white;
    font-weight:bold;
    cursor:pointer;
    margin:3px;
}

.btn:hover{
    opacity:.9;
}

.btn-green{
    background:#159b65;
}

.btn-purple{
    background:#7048c8;
}

.btn-orange{
    background:#dc7a18;
}

.btn-red{
    background:#d64545;
}

.btn-light{
    background:#e9effc;
    color:#31589d;
}

/* FORMS */

.form-grid{
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:16px;
}

.field label{
    display:block;
    margin-bottom:7px;
    font-weight:bold;
    color:#39465d;
}

input,
select,
textarea{
    width:100%;
    padding:12px;
    border:1px solid #cfd6e2;
    border-radius:8px;
    font-size:15px;
}

textarea{
    min-height:110px;
}

.full{
    grid-column:1/-1;
}

/* DASHBOARD */

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
    gap:16px;
    margin-bottom:22px;
}

.stat{
    background:white;
    padding:20px;
    border-radius:14px;
    box-shadow:0 4px 16px rgba(0,0,0,.06);
    border:1px solid #e5e9f1;
}

.stat .num{
    font-size:30px;
    font-weight:bold;
    color:#3564b8;
}

.stat small{
    color:#64748b;
}

/* TABLES */

.table-wrap{
    overflow-x:auto;
}

table{
    width:100%;
    min-width:700px;
    border-collapse:collapse;
}

th{
    background:#263f70;
    color:white;
}

th,
td{
    padding:12px;
    text-align:left;
    border-bottom:1px solid #e6eaf0;
}

tr:hover td{
    background:#f7f9fc;
}

.evidence{
    width:90px;
    height:65px;
    object-fit:cover;
    border-radius:7px;
}

/* BADGES */

.badge{
    padding:5px 10px;
    border-radius:20px;
    font-size:12px;
    font-weight:bold;
    display:inline-block;
}

.low{
    background:#dff6e8;
    color:#187043;
}

.medium{
    background:#fff0c9;
    color:#956300;
}

.high{
    background:#ffe0e0;
    color:#b52b2b;
}

.role{
    display:inline-block;
    padding:6px 11px;
    background:#e9edff;
    color:#4941a1;
    border-radius:20px;
    font-size:13px;
    font-weight:bold;
}

.camera{
    width:100%;
    min-height:280px;
    object-fit:cover;
    background:#111827;
    border-radius:12px;
}

.video-box{
    padding:8px;
    background:#111827;
    border-radius:15px;
}

.empty{
    text-align:center;
    padding:30px;
    color:#64748b;
}

.footer{
    text-align:center;
    padding:25px;
    color:#64748b;
}

.login-box{
    max-width:450px;
    margin:50px auto;
}

@media(max-width:900px){
    .features{
        grid-template-columns:repeat(2,1fr);
    }

    .hero h1{
        font-size:34px;
    }
}

@media(max-width:600px){

    .navbar{
        padding:10px 5%;
        flex-direction:column;
    }

    .navlinks a{
        padding:7px;
    }

    .landing{
        padding-top:50px;
    }

    .features{
        grid-template-columns:1fr;
    }

    .hero h1{
        font-size:28px;
    }

    .form-grid{
        grid-template-columns:1fr;
    }

    .full{
        grid-column:auto;
    }
}
</style>
"""


# =========================================================
# PAGE LAYOUT
# =========================================================

LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>
</head>

<body>
    {{ navbar|safe }}
    {{ body|safe }}
</body>
</html>
"""


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


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
    if count >= 4:
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

    icons = {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🔴"
    }

    return (
        '<span class="badge ' + classes.get(priority, "low") + '">'
        + icons.get(priority, "⚪") + " "
        + esc(priority)
        + "</span>"
    )


def nav():

    if not logged_in():
        return """
        <div class="navbar">
            <a class="brand" href="/">🏛️ Smart Monitoring & Inspection System</a>
            <div class="navlinks">
                <a href="/login">🔐 Login</a>
            </div>
        </div>
        """

    links = """
        <a href="/home">🏠 Home</a>
        <a href="/dashboard">📊 Dashboard</a>
    """

    if session.get("role") in ("Worker", "Inspector"):
        links += '<a href="/my-assignments">📋 Assignments</a>'

    if session.get("role") == "Authority":
        links += """
            <a href="/users">👥 Users</a>
            <a href="/assignments">🎲 Assign</a>
            <a href="/analytics">📈 Analytics</a>
        """

    links += '<a href="/meetings">🎥 Meetings</a>'
    links += '<a href="/logout">🚪 Logout</a>'

    return """
    <div class="navbar">
        <a class="brand" href="/home">🏛️ SIMMS</a>
        <div class="navlinks">""" + links + """</div>
    </div>
    """


def page(body, title="SIMMS"):
    return render_template_string(
        STYLE + LAYOUT,
        body=body,
        navbar=nav(),
        title=title
    )


# =========================================================
# DATABASE INITIALIZATION
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

    CREATE TABLE IF NOT EXISTS meetings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        meeting_code TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL,
        created_by INTEGER
    );
    """)

    demo_users = [
        ("ADMIN001", "System Authority", "admin123", "Authority"),
        ("INS001", "Inspection Officer", "inspector123", "Inspector"),
        ("WORK001", "Demo Field Worker", "worker123", "Worker")
    ]

    for uid, name, password, role in demo_users:

        user = conn.execute(
            "SELECT id FROM users WHERE unique_id=?",
            (uid,)
        ).fetchone()

        if not user:
            conn.execute(
                """
                INSERT INTO users
                (unique_id, name, password, role, created_at)
                VALUES (?, ?, ?, ?, ?)
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
# LANDING PAGE
# =========================================================

@app.route("/")
def landing():

    body = """
    <div class="landing">

        <section class="hero">
            <h1>Smart Real-Time Monitoring & Inspection System</h1>

            <p>
                A digital platform for field inspection, evidence collection
                and real-time issue monitoring.
            </p>

            <a class="login-button" href="/login">
                🔐 Login to System
            </a>
        </section>

        <section class="features">

            <div class="feature">
                <h3>🧑‍🔧 Field Inspection</h3>
                <p>
                    Workers and Inspectors conduct inspections directly
                    from assigned locations.
                </p>
            </div>

            <div class="feature">
                <h3>📸 Evidence Capture</h3>
                <p>
                    Upload photographic evidence with inspection reports.
                </p>
            </div>

            <div class="feature">
                <h3>📍 GPS Location</h3>
                <p>
                    Capture the location of field inspection reports.
                </p>
            </div>

            <div class="feature">
                <h3>🤖 Smart Priority</h3>
                <p>
                    Repeated problems automatically receive higher priority.
                </p>
            </div>

        </section>

    </div>
    """

    return page(body, "Smart Monitoring & Inspection System")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if logged_in():
        return redirect(url_for("home"))

    error = ""

    if request.method == "POST":

        unique_id = request.form.get("unique_id", "").strip().upper()
        password = request.form.get("password", "")

        conn = db()

        user = conn.execute(
            "SELECT * FROM users WHERE unique_id=?",
            (unique_id,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        error = """
        <div class="info warning">
            ❌ Invalid Unique ID or Password.
        </div>
        """

    body = """
    <div class="card login-box">

        <h1 style="text-align:center">🔐 System Login</h1>

        <p style="text-align:center;color:#64748b">
            Login to access your inspection workspace.
        </p>

        """ + error + """

        <form method="POST">

            <div class="field">
                <label>Unique ID</label>
                <input
                    name="unique_id"
                    placeholder="ADMIN001 / INS001 / WORK001"
                    required
                >
            </div>

            <br>

            <div class="field">
                <label>Password</label>
                <input
                    type="password"
                    name="password"
                    placeholder="Enter password"
                    required
                >
            </div>

            <br>

            <button class="btn" style="width:100%">
                Login
            </button>

        </form>

        <div class="info">
            <b>🎓 Demo Login Accounts</b><br><br>

            Authority:<br>
            <b>ADMIN001 / admin123</b><br><br>

            Inspector:<br>
            <b>INS001 / inspector123</b><br><br>

            Worker:<br>
            <b>WORK001 / worker123</b>
        </div>

        <a href="/">← Back to Home</a>

    </div>
    """

    return page(body, "Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# =========================================================
# HOME
# =========================================================

@app.route("/home")
def home():

    if not logged_in():
        return redirect(url_for("login"))

    name = esc(session.get("name"))
    role = esc(session.get("role"))

    buttons = '<a class="btn" href="/dashboard">📊 Dashboard</a>'

    if session["role"] in ("Worker", "Inspector"):

        buttons += """
        <a class="btn btn-purple" href="/my-assignments">
            📋 My Assignments
        </a>
        """

    if session["role"] == "Authority":

        buttons += """
        <a class="btn btn-purple" href="/assignments">
            🎲 Assign Inspection
        </a>

        <a class="btn btn-green" href="/users">
            👥 Manage Users
        </a>

        <a class="btn btn-orange" href="/analytics">
            📈 Analytics
        </a>
        """

    body = """
    <main class="container">

        <div class="card">

            <h1>Welcome, """ + name + """ 👋</h1>

            <span class="role">""" + role + """</span>

            <div class="info">
                Role-based access is enabled. Select a module below
                to continue.
            </div>

            """ + buttons + """

        </div>

        <div class="card">

            <h2>🎯 SIMMS Inspection Workflow</h2>

            <div class="info">
                Authority Assigns → Worker Verifies →
                Field Inspection → Photo + GPS →
                Issue Priority → Resolution
            </div>

        </div>

    </main>
    """

    return page(body, "SIMMS Home")


# =========================================================
# USER MANAGEMENT
# =========================================================

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
            <div class="info warning">
                Enter a valid name and password.
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
                """
                INSERT INTO users
                (unique_id,name,password,role,created_at)
                VALUES(?,?,?,?,?)
                """,
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
                Unique ID: <b>""" + esc(unique_id) + """</b>
            </div>
            """

    conn = db()

    rows = conn.execute(
        "SELECT unique_id,name,role,created_at FROM users ORDER BY id DESC"
    ).fetchall()

    conn.close()

    table_rows = ""

    for row in rows:

        table_rows += """
        <tr>
            <td>""" + esc(row["unique_id"]) + """</td>
            <td>""" + esc(row["name"]) + """</td>
            <td>""" + esc(row["role"]) + """</td>
            <td>""" + esc(row["created_at"]) + """</td>
        </tr>
        """

    body = """
    <main class="container">

        <div class="card">

            <h1>👥 User Management</h1>

            """ + message + """

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
                    <label>&nbsp;</label>
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

                    """ + table_rows + """

                </table>
            </div>

        </div>

    </main>
    """

    return page(body, "Users")


# =========================================================
# RANDOM ASSIGNMENT
# =========================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()

    workers = conn.execute(
        """
        SELECT id,name,unique_id FROM users
        WHERE role IN ('Worker','Inspector')
        """
    ).fetchall()

    message = ""

    if request.method == "POST":

        location = request.form.get("location", "").strip()

        if not location:

            message = """
            <div class="info warning">
                Please enter a location.
            </div>
            """

        elif not workers:

            message = """
            <div class="info warning">
                No Workers or Inspectors are available.
            </div>
            """

        else:

            selected = random.choice(workers)

            conn.execute(
                """
                INSERT INTO assignments
                (user_id,location,assigned_at,status,face_verified)
                VALUES(?,?,?,?,?)
                """,
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
                🎲 Inspection assigned successfully!<br>
                📍 Location: <b>""" + esc(location) + """</b><br>
                👤 Assigned to: <b>""" + esc(selected["name"]) + """</b>
            </div>
            """

    rows = conn.execute(
        """
        SELECT a.*,u.name,u.unique_id
        FROM assignments a
        JOIN users u ON a.user_id=u.id
        ORDER BY a.id DESC
        """
    ).fetchall()

    conn.close()

    table_rows = ""

    for row in rows:

        table_rows += """
        <tr>
            <td>""" + esc(row["location"]) + """</td>
            <td>""" + esc(row["name"]) + """</td>
            <td>""" + esc(row["unique_id"]) + """</td>
            <td>""" + esc(row["assigned_at"]) + """</td>
            <td>""" + esc(row["status"]) + """</td>
        </tr>
        """

    body = """
    <main class="container">

        <div class="card">

            <h1>🎲 Random Inspection Assignment</h1>

            <p>
                The system automatically selects a Worker or Inspector
                for the inspection.
            </p>

            """ + message + """

            <form method="POST">

                <div class="field">
                    <label>📍 Inspection Location</label>

                    <input
                        name="location"
                        placeholder="Example: Government Office, Vijayawada"
                        required
                    >
                </div>

                <br>

                <button class="btn btn-purple">
                    🎲 Randomly Assign
                </button>

            </form>

        </div>

        <div class="card">

            <h2>📋 Assignment History</h2>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Location</th>
                        <th>Assigned To</th>
                        <th>ID</th>
                        <th>Assigned Time</th>
                        <th>Status</th>
                    </tr>

                    """ + (
                        table_rows if table_rows else
                        '<tr><td colspan="5" class="empty">No assignments yet.</td></tr>'
                    ) + """

                </table>

            </div>

        </div>

    </main>
    """

    return page(body, "Assignments")


# =========================================================
# WORKER ASSIGNMENTS
# =========================================================

@app.route("/my-assignments")
def my_assignments():

    if not logged_in() or session.get("role") not in ("Worker", "Inspector"):
        return "Access denied", 403

    conn = db()

    rows = conn.execute(
        """
        SELECT * FROM assignments
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    table_rows = ""

    for row in rows:

        if row["status"] == "Completed":

            action = '<span class="badge low">✅ Completed</span>'

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

        verification = (
            '<span class="badge low">Verified</span>'
            if row["face_verified"]
            else '<span class="badge medium">Required</span>'
        )

        table_rows += """
        <tr>
            <td>📍 """ + esc(row["location"]) + """</td>
            <td>""" + esc(row["assigned_at"]) + """</td>
            <td>""" + verification + """</td>
            <td>""" + esc(row["status"]) + """</td>
            <td>""" + action + """</td>
        </tr>
        """

    body = """
    <main class="container">

        <div class="card">

            <h1>📋 My Inspection Assignments</h1>

            <div class="info">
                Complete verification and then fill the inspection form.
            </div>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Location</th>
                        <th>Assigned Time</th>
                        <th>Verification</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>

                    """ + (
                        table_rows if table_rows else
                        '<tr><td colspan="5" class="empty">📭 No assignments available.</td></tr>'
                    ) + """

                </table>

            </div>

        </div>

    </main>
    """

    return page(body, "My Assignments")


# =========================================================
# FACE / CAMERA VERIFICATION
# IMPORTANT: NO f-string JavaScript is used here!
# =========================================================

@app.route("/face-verification/<int:assignment_id>", methods=["GET", "POST"])
def face_verification(assignment_id):

    if not logged_in() or session.get("role") not in ("Worker", "Inspector"):
        return "Access denied", 403

    conn = db()

    assignment = conn.execute(
        """
        SELECT * FROM assignments
        WHERE id=? AND user_id=? AND status='Assigned'
        """,
        (assignment_id, session["user_id"])
    ).fetchone()

    if not assignment:
        conn.close()
        return "Invalid assignment", 403

    if request.method == "POST":

        photo = request.files.get("face_photo")

        if not photo or not photo.filename:
            conn.close()
            return "Please capture your photo.", 400

        if not allowed_file(photo.filename):
            conn.close()
            return "Invalid image format.", 400

        filename = (
            "face_"
            + str(session["user_id"])
            + "_"
            + uuid.uuid4().hex
            + ".jpg"
        )

        photo.save(os.path.join(FACE_FOLDER, filename))

        conn.execute(
            """
            UPDATE assignments
            SET face_verified=1
            WHERE id=? AND user_id=?
            """,
            (assignment_id, session["user_id"])
        )

        conn.commit()
        conn.close()

        return redirect(
            url_for("inspection", assignment_id=assignment_id)
        )

    location = esc(assignment["location"])
    conn.close()

    # NOTE:
    # This is NOT an f-string, so JavaScript { } cannot cause
    # Python f-string syntax errors.

    body = """
    <main class="container">

        <div class="card" style="max-width:700px;margin:auto">

            <h1>📷 Identity Verification</h1>

            <div class="info">
                Assigned Location: <b>__LOCATION__</b><br>
                Please capture a photo before starting the inspection.
            </div>

            <div class="video-box">
                <video
                    id="video"
                    class="camera"
                    autoplay
                    playsinline>
                </video>
            </div>

            <canvas id="canvas" hidden></canvas>

            <form
                id="faceForm"
                method="POST"
                enctype="multipart/form-data">

                <input
                    id="face_photo"
                    name="face_photo"
                    type="file"
                    accept="image/*"
                    hidden
                >

                <br>

                <button
                    type="button"
                    class="btn btn-purple"
                    onclick="captureFace()">

                    📸 Capture & Continue

                </button>

            </form>

            <p id="message" class="error"></p>

        </div>

    </main>

    <script>

    const video = document.getElementById("video");

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {

        navigator.mediaDevices.getUserMedia({
            video: true
        })
        .then(function(stream) {
            video.srcObject = stream;
        })
        .catch(function(error) {
            document.getElementById("message").textContent =
                "❌ Camera permission denied. Please allow camera access.";
        });

    } else {

        document.getElementById("message").textContent =
            "❌ Camera is not supported by this browser.";

    }


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

            if (!blob) {
                alert("Could not capture the image.");
                return;
            }

            const file = new File(
                [blob],
                "face.jpg",
                {
                    type: "image/jpeg"
                }
            );

            const transfer = new DataTransfer();

            transfer.items.add(file);

            document.getElementById("face_photo").files =
                transfer.files;

            if (video.srcObject) {

                video.srcObject
                    .getTracks()
                    .forEach(function(track) {
                        track.stop();
                    });

            }

            document.getElementById("faceForm").submit();

        }, "image/jpeg");

    }

    </script>
    """

    body = body.replace("__LOCATION__", location)

    return page(body, "Verification")


# =========================================================
# INSPECTION FORM
# =========================================================

@app.route("/inspection/<int:assignment_id>", methods=["GET", "POST"])
def inspection(assignment_id):

    if not logged_in() or session.get("role") not in ("Worker", "Inspector"):
        return "Access denied", 403

    conn = db()

    assignment = conn.execute(
        """
        SELECT * FROM assignments
        WHERE id=?
        AND user_id=?
        AND face_verified=1
        AND status='Assigned'
        """,
        (assignment_id, session["user_id"])
    ).fetchone()

    if not assignment:
        conn.close()
        return "Inspection access denied", 403

    if request.method == "POST":

        cleanliness = request.form.get("cleanliness", "Yes")
        safety = request.form.get("safety", "Yes")
        facilities = request.form.get("facilities", "Yes")

        description = request.form.get("description", "").strip()
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
            ).rsplit(".", 1)[1].lower()

            photo_name = uuid.uuid4().hex + "." + extension

            photo.save(
                os.path.join(UPLOAD_FOLDER, photo_name)
            )

        issues_found = []

        if cleanliness == "No":
            issues_found.append("Cleanliness")

        if safety == "No":
            issues_found.append("Safety")

        if facilities == "No":
            issues_found.append("Facilities")

        for issue_type in issues_found:

            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM issues
                WHERE LOWER(location)=LOWER(?)
                """,
                (assignment["location"],)
            ).fetchone()[0]

            priority = priority_for(count + 1)

            conn.execute(
                """
                INSERT INTO issues
                (
                    location, issue_type, description,
                    created_at, status, priority,
                    photo, reporter_id,
                    latitude, longitude, verified
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
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

        conn.execute(
            """
            UPDATE assignments
            SET status='Completed'
            WHERE id=?
            """,
            (assignment_id,)
        )

        conn.commit()
        conn.close()

        result = (
            "⚠️ Issues reported: " + ", ".join(issues_found)
            if issues_found
            else "✅ Inspection completed successfully. No issues found."
        )

        body = """
        <main class="container">
            <div class="card" style="text-align:center">

                <h1>✅ Inspection Submitted</h1>

                <div class="info success">
                    """ + esc(result) + """
                </div>

                <a class="btn" href="/my-assignments">
                    📋 My Assignments
                </a>

                <a class="btn btn-green" href="/dashboard">
                    📊 Dashboard
                </a>

            </div>
        </main>
        """

        return page(body, "Inspection Submitted")

    location = esc(assignment["location"])
    conn.close()

    body = """
    <main class="container">

        <div class="card">

            <h1>📋 Field Inspection Form</h1>

            <div class="info">
                📍 Assigned Location: <b>__LOCATION__</b><br>
                🔐 Verification: Completed ✅
            </div>

            <form
                method="POST"
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
                    <input
                        type="file"
                        name="photo"
                        accept="image/*"
                    >
                </div>

                <div class="field">
                    <label>Latitude</label>
                    <input id="latitude" name="latitude">
                </div>

                <div class="field">
                    <label>Longitude</label>
                    <input id="longitude" name="longitude">
                </div>

                <div class="full">
                    <button
                        type="button"
                        class="btn btn-purple"
                        onclick="getLocation()">

                        📍 Get My GPS Location

                    </button>
                </div>

                <div class="field full">
                    <label>📝 Description / Observation</label>

                    <textarea
                        name="description"
                        placeholder="Describe any problem found..."
                    ></textarea>
                </div>

                <div class="full">
                    <button
                        type="submit"
                        class="btn">

                        📤 Submit Inspection

                    </button>
                </div>

            </form>

        </div>

    </main>

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

    body = body.replace("__LOCATION__", location)

    return page(body, "Field Inspection")


# =========================================================
# UPLOADED EVIDENCE
# =========================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


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

    high = sum(
        issue["priority"] == "High"
        for issue in issues
    )

    table_rows = ""

    for issue in issues:

        photo = "—"

        if issue["photo"]:
            photo = (
                '<a href="/uploads/'
                + esc(issue["photo"])
                + '" target="_blank">'
                + '<img class="evidence" src="/uploads/'
                + esc(issue["photo"])
                + '">'
                + '</a>'
            )

        action = "🔒 View Only"

        if session["role"] == "Authority":

            if issue["status"] == "Reported":

                action = (
                    '<a class="btn btn-orange" href="/update/'
                    + str(issue["id"])
                    + '/In%20Progress">🟡 Start</a>'
                )

            elif issue["status"] == "In Progress":

                action = (
                    '<a class="btn btn-green" href="/update/'
                    + str(issue["id"])
                    + '/Resolved">✅ Resolve</a>'
                )

            else:
                action = "✅ Resolved"

        coordinates = ""

        if issue["latitude"] and issue["longitude"]:

            coordinates = (
                "<br><small>📍 "
                + esc(issue["latitude"])
                + ", "
                + esc(issue["longitude"])
                + "</small>"
            )

        table_rows += """
        <tr>

            <td>
                """ + esc(issue["location"]) + coordinates + """
            </td>

            <td>""" + esc(issue["issue_type"]) + """</td>

            <td>
                """ + (
                    esc(issue["description"])
                    if issue["description"]
                    else "-"
                ) + """
            </td>

            <td>""" + badge(issue["priority"]) + """</td>

            <td>""" + photo + """</td>

            <td>""" + esc(issue["status"]) + """</td>

            <td>""" + esc(issue["created_at"]) + """</td>

            <td>""" + action + """</td>

        </tr>
        """

    body = """
    <main class="container">

        <h1>📊 Real-Time Monitoring Dashboard</h1>

        <div class="stats">

            <div class="stat">
                <div class="num">""" + str(total) + """</div>
                <small>Total Issues</small>
            </div>

            <div class="stat">
                <div class="num">""" + str(reported) + """</div>
                <small>🔴 Reported</small>
            </div>

            <div class="stat">
                <div class="num">""" + str(progress) + """</div>
                <small>🟡 In Progress</small>
            </div>

            <div class="stat">
                <div class="num">""" + str(resolved) + """</div>
                <small>🟢 Resolved</small>
            </div>

            <div class="stat">
                <div class="num">""" + str(high) + """</div>
                <small>🔴 High Priority</small>
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
                        <th>Time</th>
                        <th>Action</th>
                    </tr>

                    """ + (
                        table_rows if table_rows else
                        '<tr><td colspan="8" class="empty">🎉 No issues reported yet.</td></tr>'
                    ) + """

                </table>

            </div>

        </div>

    </main>
    """

    return page(body, "Dashboard")


# =========================================================
# UPDATE ISSUE STATUS
# =========================================================

@app.route("/update/<int:issue_id>/<status>")
def update_status(issue_id, status):

    if not role_required("Authority"):
        return "Access denied", 403

    allowed_status = (
        "Reported",
        "In Progress",
        "Resolved"
    )

    if status not in allowed_status:
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
# ANALYTICS
# =========================================================

@app.route("/analytics")
def analytics():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()

    locations = conn.execute(
        """
        SELECT location,COUNT(*) AS reports
        FROM issues
        GROUP BY location
        ORDER BY reports DESC
        """
    ).fetchall()

    workers = conn.execute(
        """
        SELECT u.name,u.unique_id,COUNT(i.id) AS reports
        FROM users u
        LEFT JOIN issues i ON u.id=i.reporter_id
        WHERE u.role IN ('Worker','Inspector')
        GROUP BY u.id
        ORDER BY reports DESC
        """
    ).fetchall()

    conn.close()

    location_rows = ""

    for item in locations:

        location_rows += """
        <tr>
            <td>""" + esc(item["location"]) + """</td>
            <td>""" + str(item["reports"]) + """</td>
            <td>""" + badge(priority_for(item["reports"])) + """</td>
        </tr>
        """

    worker_rows = ""

    for item in workers:

        worker_rows += """
        <tr>
            <td>""" + esc(item["name"]) + """</td>
            <td>""" + esc(item["unique_id"]) + """</td>
            <td>""" + str(item["reports"]) + """</td>
        </tr>
        """

    body = """
    <main class="container">

        <div class="card">

            <h1>📈 Inspection Analytics</h1>

            <div class="info">
                Repeated problems at the same location receive
                automatically increased priority.
            </div>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Location</th>
                        <th>Reports</th>
                        <th>Priority</th>
                    </tr>

                    """ + (
                        location_rows if location_rows else
                        '<tr><td colspan="3" class="empty">No data available.</td></tr>'
                    ) + """

                </table>

            </div>

        </div>

        <div class="card">

            <h2>👷 Worker Inspection Activity</h2>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Name</th>
                        <th>Unique ID</th>
                        <th>Reports Submitted</th>
                    </tr>

                    """ + (
                        worker_rows if worker_rows else
                        '<tr><td colspan="3" class="empty">No data available.</td></tr>'
                    ) + """

                </table>

            </div>

        </div>

    </main>
    """

    return page(body, "Analytics")


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

        if not title:

            message = """
            <div class="info warning">
                Please enter a meeting title.
            </div>
            """

        else:

            code = uuid.uuid4().hex[:8].upper()

            conn.execute(
                """
                INSERT INTO meetings
                (title,meeting_code,created_at,created_by)
                VALUES(?,?,?,?)
                """,
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
                🎥 Meeting created successfully!<br>
                Meeting Code: <b>""" + esc(code) + """</b>
            </div>
            """

    meeting_list = conn.execute(
        """
        SELECT m.*,u.name AS authority_name
        FROM meetings m
        LEFT JOIN users u ON m.created_by=u.id
        ORDER BY m.id DESC
        """
    ).fetchall()

    conn.close()

    form = ""

    if session["role"] == "Authority":

        form = """
        <div class="card">

            <h1>🎥 Create Team Meeting</h1>

            <form method="POST">

                <div class="field">
                    <label>Meeting Title</label>

                    <input
                        name="title"
                        placeholder="Inspection Review Meeting"
                        required
                    >
                </div>

                <br>

                <button class="btn btn-purple">
                    🎥 Create Meeting
                </button>

            </form>

        </div>
        """

    rows = ""

    for meeting in meeting_list:

        rows += """
        <tr>
            <td>""" + esc(meeting["title"]) + """</td>
            <td>""" + esc(meeting["authority_name"] or "Authority") + """</td>
            <td>""" + esc(meeting["created_at"]) + """</td>
            <td>
                <a class="btn btn-purple"
                   href="/meeting/""" + esc(meeting["meeting_code"]) + """">
                   🎥 Join
                </a>
            </td>
        </tr>
        """

    body = """
    <main class="container">

        """ + message + form + """

        <div class="card">

            <h2>🎥 Available Meetings</h2>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Meeting</th>
                        <th>Created By</th>
                        <th>Created Time</th>
                        <th>Action</th>
                    </tr>

                    """ + (
                        rows if rows else
                        '<tr><td colspan="4" class="empty">No meetings available.</td></tr>'
                    ) + """

                </table>

            </div>

        </div>

    </main>
    """

    return page(body, "Meetings")


@app.route("/meeting/<meeting_code>")
def meeting_room(meeting_code):

    if not logged_in():
        return redirect(url_for("login"))

    conn = db()

    meeting = conn.execute(
        """
        SELECT * FROM meetings
        WHERE meeting_code=?
        """,
        (meeting_code,)
    ).fetchone()

    conn.close()

    if not meeting:
        return "Meeting not found", 404

    body = """
    <main class="container">

        <div class="card" style="text-align:center">

            <h1>🎥 Smart Inspection Meeting Room</h1>

            <div class="info success">

                🟢 You joined the meeting successfully!<br><br>

                Meeting: <b>__TITLE__</b><br>
                Code: <b>__CODE__</b>

            </div>

            <p style="color:#64748b">
                This is a SIMMS prototype meeting coordination room.
                A production version can integrate WebRTC or a
                video conferencing service.
            </p>

            <a class="btn" href="/meetings">
                ← Back to Meetings
            </a>

        </div>

    </main>
    """

    body = body.replace("__TITLE__", esc(meeting["title"]))
    body = body.replace("__CODE__", esc(meeting_code))

    return page(body, "Meeting Room")


# =========================================================
# API - LATEST MEETING
# =========================================================

@app.route("/api/latest-meeting")
def latest_meeting():

    if not logged_in():
        return jsonify({"logged_in": False}), 401

    conn = db()

    meeting = conn.execute(
        """
        SELECT id,title,meeting_code,created_at
        FROM meetings
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    if not meeting:
        return jsonify({"meeting": None})

    return jsonify({
        "meeting": {
            "id": meeting["id"],
            "title": meeting["title"],
            "meeting_code": meeting["meeting_code"],
            "created_at": meeting["created_at"]
        }
    })


# =========================================================
# ERROR HANDLER
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    body = """
    <main class="container">
        <div class="card">
            <h1>⚠️ File Too Large</h1>
            <p>Please upload an image smaller than 10 MB.</p>
        </div>
    </main>
    """

    return page(body, "Upload Error"), 413


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
