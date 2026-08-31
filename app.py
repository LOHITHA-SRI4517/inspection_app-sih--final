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


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smart_inspection_system_2026_secure_key"
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
# STYLING
# ============================================================

STYLE = """
<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f4f6fa;
    color: #26364d;
}

a {
    text-decoration: none;
    color: inherit;
}

/* NAVBAR - Similar to your screenshot */

.navbar {
    background: linear-gradient(90deg, #1f2c4a, #3658ad);
    color: white;
    min-height: 57px;
    padding: 0 7%;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.brand {
    font-size: 17px;
    font-weight: 700;
    display: flex;
    gap: 9px;
    align-items: center;
}

.navlinks {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-wrap: wrap;
}

.navlinks a {
    padding: 18px 12px;
    font-weight: 600;
    font-size: 14px;
}

.navlinks a:hover {
    background: rgba(255,255,255,.12);
}

/* MAIN */

.container {
    max-width: 1250px;
    margin: auto;
    padding: 32px 20px;
}

/* LANDING PAGE */

.hero {
    text-align: center;
    padding: 70px 20px 85px;
    background:
        radial-gradient(circle at top, #f8f9fc, #e9edf5);
    min-height: 385px;
}

.hero h1 {
    font-size: 43px;
    margin: 38px 0 22px;
    color: #304a7c;
    letter-spacing: .2px;
}

.hero p {
    font-size: 18px;
    color: #374151;
    margin: auto;
    max-width: 750px;
}

.hero-btn {
    display: inline-block;
    margin-top: 25px;
    background: linear-gradient(135deg, #4268bd, #2858b0);
    color: white;
    padding: 14px 25px;
    border-radius: 8px;
    font-size: 15px;
    box-shadow: 0 5px 12px rgba(37, 82, 175, .2);
}

.hero-btn:hover {
    transform: translateY(-1px);
}

.features {
    max-width: 1210px;
    margin: -45px auto 40px;
    padding: 0 20px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
}

.feature-card {
    background: rgba(255,255,255,.9);
    border: 1px solid #e2e6ee;
    border-radius: 17px;
    padding: 28px 23px;
    min-height: 187px;
    box-shadow: 0 8px 25px rgba(40,55,80,.08);
}

.feature-card h3 {
    margin: 10px 0 20px;
    color: #344a70;
    font-size: 18px;
}

.feature-card p {
    color: #3f4856;
    line-height: 1.35;
    margin: 0;
}

.feature-icon {
    font-size: 22px;
}

/* GENERAL CARDS */

.card {
    background: white;
    border: 1px solid #e3e7ee;
    border-radius: 14px;
    padding: 25px;
    margin-bottom: 22px;
    box-shadow: 0 6px 22px rgba(15, 23, 42, .04);
}

.login-box {
    max-width: 470px;
    margin: 35px auto;
}

.btn {
    display: inline-block;
    border: none;
    cursor: pointer;
    padding: 11px 17px;
    margin: 3px;
    border-radius: 8px;
    background: #3564ba;
    color: white;
    font-weight: 700;
    font-size: 14px;
}

.btn:hover {
    opacity: .92;
}

.btn-green { background: #14895d; }
.btn-purple { background: #6b46c1; }
.btn-orange { background: #dc6b19; }
.btn-red { background: #c53030; }

.btn-light {
    background: #e8eefb;
    color: #2854a4;
}

/* FORMS */

.form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 15px;
}

.field label {
    display: block;
    margin-bottom: 7px;
    font-size: 14px;
    font-weight: 700;
    color: #374151;
}

input, select, textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #ccd3df;
    border-radius: 8px;
    font-size: 15px;
}

textarea {
    min-height: 115px;
    resize: vertical;
}

.full {
    grid-column: 1 / -1;
}

/* INFO BOXES */

.info {
    background: #eef4ff;
    border-left: 4px solid #3564ba;
    padding: 14px;
    border-radius: 7px;
    margin: 15px 0;
    line-height: 1.6;
}

.success {
    background: #ecfdf5;
    border-left-color: #14895d;
}

.warning {
    background: #fff7ed;
    border-left-color: #dc6b19;
}

/* TABLE */

.table-wrap {
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 720px;
}

th {
    background: #263b69;
    color: white;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #e5e7eb;
}

tr:hover td {
    background: #f8fafc;
}

/* STATS */

.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 15px;
    margin: 20px 0;
}

.stat {
    background: white;
    border: 1px solid #e3e7ee;
    border-radius: 12px;
    padding: 20px;
}

.num {
    font-size: 30px;
    font-weight: bold;
    color: #3564ba;
}

.stat small {
    color: #64748b;
}

/* BADGES */

.badge {
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: bold;
}

.low {
    background: #dcfce7;
    color: #166534;
}

.medium {
    background: #fef3c7;
    color: #92400e;
}

.high {
    background: #fee2e2;
    color: #991b1b;
}

.role {
    display: inline-block;
    background: #e8edfb;
    color: #3b4e91;
    padding: 6px 10px;
    border-radius: 999px;
    font-weight: bold;
    font-size: 13px;
}

.evidence {
    width: 90px;
    height: 65px;
    object-fit: cover;
    border-radius: 7px;
}

/* CAMERA */

.camera {
    width: 100%;
    background: #111827;
    border-radius: 12px;
    min-height: 280px;
    object-fit: cover;
}

.video-box {
    padding: 10px;
    background: #172033;
    border-radius: 14px;
}

/* FOOTER */

.footer {
    text-align: center;
    color: #64748b;
    padding: 25px;
}

/* MOBILE */

@media(max-width: 900px) {
    .features {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media(max-width: 700px) {
    .navbar {
        padding: 12px 5%;
        flex-direction: column;
        align-items: flex-start;
    }

    .navlinks a {
        padding: 7px;
    }

    .hero h1 {
        font-size: 31px;
    }

    .features {
        grid-template-columns: 1fr;
        margin-top: -20px;
    }

    .form-grid {
        grid-template-columns: 1fr;
    }

    .full {
        grid-column: auto;
    }
}
</style>
"""


LAYOUT = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title or 'SIMMS' }}</title>
</head>
<body>

{{ navbar|safe }}

{{ body|safe }}

<div class="footer">
    🏛️ Smart Monitoring & Inspection System • SIMMS
</div>

</body>
</html>
"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

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
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
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
        f'<span class="badge {classes.get(priority, "low")}">'
        f'{icons.get(priority, "⚪")} {esc(priority)}</span>'
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

    links = [
        '<a href="/home">🏠 Home</a>',
        '<a href="/dashboard">📊 Dashboard</a>'
    ]

    if session.get("role") in ("Worker", "Inspector"):
        links.append('<a href="/my-assignments">📋 Assignments</a>')
        links.append('<a href="/face-registration">📷 Face Profile</a>')

    if session.get("role") == "Authority":
        links += [
            '<a href="/users">👥 Users</a>',
            '<a href="/assignments">🎲 Assign</a>',
            '<a href="/analytics">📈 Analytics</a>',
            '<a href="/cctv">📹 CCTV</a>'
        ]

    links += [
        '<a href="/meetings">🎥 Meetings</a>',
        '<a href="/logout">🚪 Logout</a>'
    ]

    return f"""
    <div class="navbar">
        <a class="brand" href="/home">🏛️ Smart Monitoring & Inspection System</a>
        <div class="navlinks">
            {"".join(links)}
        </div>
    </div>
    """


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

def add_column_if_missing(conn, table, column, definition):
    columns = {
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }

    if column not in columns:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def init_db():
    conn = db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL,
        face_photo TEXT
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
        meeting_url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        created_by INTEGER,
        meeting_code TEXT
    );

    CREATE TABLE IF NOT EXISTS meeting_participants(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TEXT NOT NULL,
        UNIQUE(meeting_id, user_id)
    );
    """)

    # Backward compatibility with older databases
    add_column_if_missing(conn, "users", "face_photo", "TEXT")
    add_column_if_missing(conn, "assignments", "face_verified", "INTEGER DEFAULT 0")
    add_column_if_missing(conn, "issues", "priority", "TEXT DEFAULT 'Low'")
    add_column_if_missing(conn, "issues", "photo", "TEXT")
    add_column_if_missing(conn, "issues", "reporter_id", "INTEGER")
    add_column_if_missing(conn, "issues", "latitude", "TEXT")
    add_column_if_missing(conn, "issues", "longitude", "TEXT")
    add_column_if_missing(conn, "issues", "verified", "INTEGER DEFAULT 0")
    add_column_if_missing(conn, "meetings", "created_by", "INTEGER")
    add_column_if_missing(conn, "meetings", "meeting_code", "TEXT")

    demo_users = [
        ("ADMIN001", "System Authority", "admin123", "Authority"),
        ("INS001", "Inspection Officer", "inspector123", "Inspector"),
        ("WORK001", "Demo Field Worker", "worker123", "Worker")
    ]

    for uid, name, password, role in demo_users:
        exists = conn.execute(
            "SELECT id FROM users WHERE unique_id=?",
            (uid,)
        ).fetchone()

        if not exists:
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


# ============================================================
# LANDING PAGE - SIMILAR TO YOUR SCREENSHOT
# ============================================================

@app.route("/")
def landing():

    body = """
    <section class="hero">
        <h1>Smart Real-Time Monitoring & Inspection System</h1>

        <p>
            A digital platform for field inspection, evidence collection
            and real-time issue monitoring.
        </p>

        <a class="hero-btn" href="/login">
            🔐 Login to System
        </a>
    </section>

    <section class="features">

        <div class="feature-card">
            <div class="feature-icon">🧑‍🔧</div>
            <h3>Field Inspection</h3>
            <p>
                Workers and Inspectors conduct inspections directly
                from assigned locations.
            </p>
        </div>

        <div class="feature-card">
            <div class="feature-icon">📸</div>
            <h3>Evidence Capture</h3>
            <p>
                Upload photographic evidence with inspection reports.
            </p>
        </div>

        <div class="feature-card">
            <div class="feature-icon">📍</div>
            <h3>GPS Location</h3>
            <p>
                Capture the location of field inspection reports.
            </p>
        </div>

        <div class="feature-card">
            <div class="feature-icon">🤖</div>
            <h3>Smart Priority</h3>
            <p>
                Repeated problems automatically receive higher priority.
            </p>
        </div>

    </section>
    """

    return page(body, "Smart Monitoring & Inspection System")


# ============================================================
# LOGIN / LOGOUT
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if logged_in():
        return redirect(url_for("home"))

    error = ""

    if request.method == "POST":

        uid = request.form.get(
            "unique_id", ""
        ).strip().upper()

        password = request.form.get("password", "")

        conn = db()

        user = conn.execute(
            "SELECT * FROM users WHERE unique_id=?",
            (uid,)
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

        error = "Invalid Unique ID or Password."

    body = f"""
    <div class="card login-box">

        <h1 style="text-align:center;color:#304a7c">
            🔐 Login to SIMMS
        </h1>

        <p style="text-align:center;color:#64748b">
            Access your Smart Inspection workspace.
        </p>

        {
            f'<div class="info warning">{esc(error)}</div>'
            if error else ''
        }

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
                🔐 Login
            </button>

        </form>

        <div class="info">
            <b>Demo Login Accounts</b><br><br>
            👑 Authority: ADMIN001 / admin123<br>
            🔍 Inspector: INS001 / inspector123<br>
            👷 Worker: WORK001 / worker123
        </div>

    </div>
    """

    return page(body, "Login")


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

    role = session["role"]

    buttons = '<a class="btn" href="/dashboard">📊 Dashboard</a>'

    if role in ("Worker", "Inspector"):
        buttons += """
        <a class="btn btn-purple" href="/my-assignments">
            📋 My Assignments
        </a>
        <a class="btn btn-light" href="/face-registration">
            📷 Face Registration
        </a>
        """

    if role == "Authority":
        buttons += """
        <a class="btn btn-purple" href="/assignments">
            🎲 Assign Inspection
        </a>
        <a class="btn btn-green" href="/analytics">
            📈 Analytics
        </a>
        """

    body = f"""
    <div class="container">

        <div class="card">

            <span class="role">{esc(role)}</span>

            <h1 style="color:#304a7c">
                Welcome, {esc(session["name"])} 👋
            </h1>

            <p style="color:#64748b">
                Welcome to your Smart Monitoring & Inspection workspace.
            </p>

            <div class="info">
                🔐 Role-based access is enabled for secure inspection
                management.
            </div>

            {buttons}

        </div>

        <div class="card">
            <h2>🎯 Inspection Workflow</h2>

            <p>
                🎲 Assignment → 📷 Identity Verification →
                🧑‍🔧 Field Inspection → 📍 GPS →
                📸 Evidence → 📊 Monitoring → ✅ Resolution
            </p>
        </div>

    </div>
    """

    return page(body, "SIMMS Home")


# ============================================================
# FACE REGISTRATION
# ============================================================

@app.route("/face-registration", methods=["GET", "POST"])
def face_registration():

    if not logged_in() or session.get("role") not in ("Worker", "Inspector"):
        return "Access denied", 403

    if request.method == "POST":

        photo = request.files.get("face_photo")

        if not photo or not photo.filename:
            return "Please capture a face photo.", 400

        if not allowed_file(photo.filename):
            return "Invalid image format.", 400

        filename = (
            "registered_"
            + str(session["user_id"])
            + "_"
            + uuid.uuid4().hex
            + ".jpg"
        )

        photo.save(
            os.path.join(FACE_FOLDER, filename)
        )

        conn = db()

        conn.execute(
            "UPDATE users SET face_photo=? WHERE id=?",
            (filename, session["user_id"])
        )

        conn.commit()
        conn.close()

        return redirect(url_for("my_assignments"))

    body = """
    <div class="container">
        <div class="card" style="max-width:700px;margin:auto">

            <h1>📷 Face Registration</h1>

            <div class="info">
                Register a camera photo for your inspection profile.
                This prototype stores the captured image securely as
                part of the inspection identity workflow.
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
                    type="file"
                    name="face_photo"
                    hidden
                >

                <br>

                <button
                    type="button"
                    class="btn btn-purple"
                    onclick="captureFace()">

                    📸 Capture & Register Face

                </button>

            </form>

            <p id="message" style="color:#b91c1c"></p>

        </div>
    </div>

    <script>

    const video = document.getElementById('video');

    navigator.mediaDevices.getUserMedia({
        video: true
    }).then(stream => {

        video.srcObject = stream;

    }).catch(() => {

        document.getElementById('message').textContent =
        'Camera access denied. Please allow camera permission.';

    });


    function captureFace() {

        if (!video.videoWidth) {
            alert('Please wait for camera to start.');
            return;
        }

        const canvas =
            document.getElementById('canvas');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        canvas.getContext('2d').drawImage(
            video, 0, 0,
            canvas.width,
            canvas.height
        );

        canvas.toBlob(function(blob) {

            const file = new File(
                [blob],
                'face.jpg',
                {type:'image/jpeg'}
            );

            const dt = new DataTransfer();

            dt.items.add(file);

            document.getElementById(
                'face_photo'
            ).files = dt.files;

            document.getElementById(
                'faceForm'
            ).submit();

        }, 'image/jpeg');
    }

    </script>
    """

    return page(body, "Face Registration")


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

        if (
            not name or
            len(password) < 4 or
            role not in ("Authority", "Inspector", "Worker")
        ):
            message = """
            <div class="info warning">
                Please enter valid user details.
            </div>
            """

        else:

            prefix = {
                "Authority": "AUTH",
                "Inspector": "INS",
                "Worker": "WORK"
            }[role]

            uid = prefix + uuid.uuid4().hex[:6].upper()

            conn = db()

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

            message = f"""
            <div class="info success">
                ✅ User created successfully.<br>
                Unique ID: <b>{esc(uid)}</b>
            </div>
            """

    conn = db()

    rows = conn.execute(
        """
        SELECT unique_id,name,role,created_at
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    trs = "".join(
        f"""
        <tr>
            <td>{esc(r["unique_id"])}</td>
            <td>{esc(r["name"])}</td>
            <td>{esc(r["role"])}</td>
            <td>{esc(r["created_at"])}</td>
        </tr>
        """
        for r in rows
    )

    body = f"""
    <div class="container">

        <div class="card">

            <h1>👥 User Management</h1>

            {message}

            <form method="POST" class="form-grid">

                <div class="field">
                    <label>Full Name</label>
                    <input name="name" required>
                </div>

                <div class="field">
                    <label>Password</label>
                    <input
                        type="password"
                        name="password"
                        required
                    >
                </div>

                <div class="field">
                    <label>Role</label>
                    <select name="role">
                        <option>Worker</option>
                        <option>Inspector</option>
                        <option>Authority</option>
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

                    {trs}

                </table>

            </div>

        </div>

    </div>
    """

    return page(body, "User Management")


# ============================================================
# RANDOM ASSIGNMENT
# ============================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()

    workers = conn.execute(
        """
        SELECT id,name,unique_id
        FROM users
        WHERE role IN ('Worker','Inspector')
        """
    ).fetchall()

    message = ""

    if request.method == "POST":

        location = request.form.get(
            "location", ""
        ).strip()

        if not location:

            message = """
            <div class="info warning">
                Please enter a location.
            </div>
            """

        elif not workers:

            message = """
            <div class="info warning">
                No Workers or Inspectors available.
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

            message = f"""
            <div class="info success">
                🎲 Inspection randomly assigned!<br>
                📍 Location: <b>{esc(location)}</b><br>
                👷 Assigned to:
                <b>{esc(selected["name"])}</b>
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

    trs = "".join(
        f"""
        <tr>
            <td>{esc(r["location"])}</td>
            <td>{esc(r["name"])}</td>
            <td>{esc(r["unique_id"])}</td>
            <td>{esc(r["assigned_at"])}</td>
            <td>{esc(r["status"])}</td>
        </tr>
        """
        for r in rows
    )

    body = f"""
    <div class="container">

        <div class="card">

            <h1>🎲 Random Inspection Assignment</h1>

            <p>
                The system randomly selects an eligible Worker or
                Inspector for the inspection.
            </p>

            {message}

            <form method="POST">

                <div class="field">
                    <label>📍 Inspection Location</label>
                    <input
                        name="location"
                        placeholder="Enter location to inspect"
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
                        <th>Time</th>
                        <th>Status</th>
                    </tr>

                    {trs or '<tr><td colspan="5">No assignments yet.</td></tr>'}

                </table>

            </div>

        </div>

    </div>
    """

    return page(body, "Assignments")


# ============================================================
# MY ASSIGNMENTS
# ============================================================

@app.route("/my-assignments")
def my_assignments():

    if (
        not logged_in() or
        session.get("role") not in ("Worker", "Inspector")
    ):
        return "Access denied", 403

    conn = db()

    user = conn.execute(
        "SELECT face_photo FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    rows = conn.execute(
        """
        SELECT *
        FROM assignments
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    trs = ""

    for assignment in rows:

        if assignment["status"] == "Completed":

            action = "✅ Completed"

        elif not user or not user["face_photo"]:

            action = """
            <a class="btn btn-purple" href="/face-registration">
                📷 Register Face First
            </a>
            """

        elif assignment["face_verified"]:

            action = f"""
            <a class="btn btn-green"
               href="/inspection/{assignment["id"]}">
                📋 Start Inspection
            </a>
            """

        else:

            action = f"""
            <a class="btn btn-purple"
               href="/face-verification/{assignment["id"]}">
                📷 Verify & Start
            </a>
            """

        verification = (
            '<span class="badge low">✅ Verified</span>'
            if assignment["face_verified"]
            else '<span class="badge medium">⏳ Required</span>'
        )

        trs += f"""
        <tr>
            <td>📍 {esc(assignment["location"])}</td>
            <td>{esc(assignment["assigned_at"])}</td>
            <td>{verification}</td>
            <td>{esc(assignment["status"])}</td>
            <td>{action}</td>
        </tr>
        """

    body = f"""
    <div class="container">

        <div class="card">

            <h1>📋 My Inspection Assignments</h1>

            <div class="info">
                📷 Register your face profile and complete camera
                verification before starting an inspection.
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

                    {trs or '<tr><td colspan="5">📭 No assignments available.</td></tr>'}

                </table>

            </div>

        </div>

    </div>
    """

    return page(body, "My Assignments")


# ============================================================
# CAMERA VERIFICATION
# ============================================================

@app.route(
    "/face-verification/<int:assignment_id>",
    methods=["GET", "POST"]
)
def face_verification(assignment_id):

    if (
        not logged_in() or
        session.get("role") not in ("Worker", "Inspector")
    ):
        return "Access denied", 403

    conn = db()

    assignment = conn.execute(
        """
        SELECT *
        FROM assignments
        WHERE id=? AND user_id=? AND status='Assigned'
        """,
        (assignment_id, session["user_id"])
    ).fetchone()

    user = conn.execute(
        "SELECT face_photo FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    if not assignment:
        conn.close()
        return "Invalid assignment", 403

    if not user or not user["face_photo"]:
        conn.close()
        return redirect(url_for("face_registration"))

    if request.method == "POST":

        photo = request.files.get("face_photo")

        if not photo or not photo.filename:
            conn.close()
            return "Please capture a verification photo.", 400

        if not allowed_file(photo.filename):
            conn.close()
            return "Invalid image format.", 400

        filename = (
            "verify_"
            + str(session["user_id"])
            + "_"
            + uuid.uuid4().hex
            + ".jpg"
        )

        photo.save(
            os.path.join(FACE_FOLDER, filename)
        )

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
            url_for(
                "inspection",
                assignment_id=assignment_id
            )
        )

    conn.close()

    body = f"""
    <div class="container">

        <div class="card"
             style="max-width:700px;margin:auto">

            <h1>📷 Identity Verification</h1>

            <div class="info">
                📍 Assigned Location:
                <b>{esc(assignment["location"])}</b><br>
                Capture a live camera image to confirm your inspection
                session before starting.
            </div>

            <div class="video-box">
                <video id="video"
                       class="camera"
                       autoplay
                       playsinline>
                </video>
            </div>

            <canvas id="canvas" hidden></canvas>

            <form id="faceForm"
                  method="POST"
                  enctype="multipart/form-data">

                <input id="face_photo"
                       name="face_photo"
                       type="file"
                       hidden>

                <br>

                <button type="button"
                        class="btn btn-purple"
                        onclick="captureFace()">

                    📸 Capture & Verify

                </button>

            </form>

            <p id="message"
               style="color:#b91c1c"></p>

        </div>

    </div>

    <script>

    const video = document.getElementById('video');

    navigator.mediaDevices.getUserMedia({video:true})
    .then(stream => {
        video.srcObject = stream;
    })
    .catch(() => {
        document.getElementById('message').textContent =
        'Please allow camera permission.';
    });

    function captureFace() {

        if (!video.videoWidth) {
            alert('Camera is starting. Please wait.');
            return;
        }

        const canvas =
            document.getElementById('canvas');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        canvas.getContext('2d').drawImage(
            video, 0, 0,
            canvas.width,
            canvas.height
        );

        canvas.toBlob(function(blob) {

            const file = new File(
                [blob],
                'verification.jpg',
                {type:'image/jpeg'}
            );

            const dt = new DataTransfer();

            dt.items.add(file);

            document.getElementById(
                'face_photo'
            ).files = dt.files;

            document.getElementById(
                'faceForm'
            ).submit();

        }, 'image/jpeg');

    }

    </script>
    """

    return page(body, "Face Verification")


# ============================================================
# INSPECTION FORM
# ============================================================

@app.route(
    "/inspection/<int:assignment_id>",
    methods=["GET", "POST"]
)
def inspection(assignment_id):

    if (
        not logged_in() or
        session.get("role") not in ("Worker", "Inspector")
    ):
        return "Access denied", 403

    conn = db()

    assignment = conn.execute(
        """
        SELECT *
        FROM assignments
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

        cleanliness = request.form.get(
            "cleanliness", "Yes"
        )

        safety = request.form.get(
            "safety", "Yes"
        )

        facilities = request.form.get(
            "facilities", "Yes"
        )

        description = request.form.get(
            "description", ""
        ).strip()

        latitude = request.form.get(
            "latitude", ""
        ).strip()

        longitude = request.form.get(
            "longitude", ""
        ).strip()

        photo = request.files.get("photo")
        photo_name = None

        if photo and photo.filename:

            if not allowed_file(photo.filename):
                conn.close()
                return "Invalid photo format.", 400

            ext = secure_filename(
                photo.filename
            ).rsplit(".", 1)[-1].lower()

            photo_name = (
                uuid.uuid4().hex + "." + ext
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

        detected = [
            issue
            for issue, answer in checks
            if answer == "No"
        ]

        for issue_type in detected:

            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM issues
                WHERE LOWER(location)=LOWER(?)
                """,
                (assignment["location"],)
            ).fetchone()[0] + 1

            priority = priority_for(count)

            conn.execute(
                """
                INSERT INTO issues(
                    location,issue_type,description,
                    created_at,status,priority,
                    photo,reporter_id,
                    latitude,longitude,verified
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
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
            "⚠️ Issues reported: " + ", ".join(detected)
            if detected
            else "✅ Inspection completed successfully. No issues found."
        )

        body = f"""
        <div class="container">

            <div class="card" style="text-align:center">

                <h1>✅ Inspection Submitted</h1>

                <div class="info success">
                    📍 {esc(assignment["location"])}
                    <br><br>
                    {esc(result)}
                </div>

                <a class="btn"
                   href="/my-assignments">
                    📋 My Assignments
                </a>

                <a class="btn btn-green"
                   href="/dashboard">
                    📊 Dashboard
                </a>

            </div>

        </div>
        """

        return page(body, "Inspection Submitted")

    conn.close()

    body = f"""
    <div class="container">

        <div class="card">

            <h1>🧑‍🔧 Field Inspection Form</h1>

            <div class="info">
                📍 Location:
                <b>{esc(assignment["location"])}</b><br>
                📷 Camera Verification:
                <b>Completed ✅</b>
            </div>

            <form method="POST"
                  enctype="multipart/form-data"
                  class="form-grid">

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

                        📍 Capture GPS Location

                    </button>
                </div>

                <div class="field full">
                    <label>📝 Observation / Description</label>
                    <textarea
                        name="description"
                        placeholder="Describe the issue or observation..."
                    ></textarea>
                </div>

                <div class="full">
                    <button class="btn"
                            type="submit">

                        📤 Submit Inspection

                    </button>
                </div>

            </form>

        </div>

    </div>

    <script>

    function getLocation() {

        if (!navigator.geolocation) {
            alert('Geolocation is not supported.');
            return;
        }

        navigator.geolocation.getCurrentPosition(
            function(position) {

                document.getElementById(
                    'latitude'
                ).value =
                position.coords.latitude;

                document.getElementById(
                    'longitude'
                ).value =
                position.coords.longitude;

            },
            function() {
                alert(
                    'Please allow location permission.'
                );
            }
        );
    }

    </script>
    """

    return page(body, "Inspection Form")


# ============================================================
# UPLOADED FILES
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

    query = """
    SELECT i.*, u.name AS reporter_name
    FROM issues i
    LEFT JOIN users u ON i.reporter_id=u.id
    """

    params = ()

    if session["role"] != "Authority":
        query += " WHERE i.reporter_id=?"
        params = (session["user_id"],)

    query += " ORDER BY i.id DESC"

    issues = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    total = len(issues)

    reported = sum(
        i["status"] == "Reported"
        for i in issues
    )

    progress = sum(
        i["status"] == "In Progress"
        for i in issues
    )

    resolved = sum(
        i["status"] == "Resolved"
        for i in issues
    )

    high = sum(
        i["priority"] == "High"
        for i in issues
    )

    trs = ""

    for issue in issues:

        if issue["photo"]:
            photo = f"""
            <a href="/uploads/{esc(issue["photo"])}"
               target="_blank">

                <img class="evidence"
                     src="/uploads/{esc(issue["photo"])}">

            </a>
            """
        else:
            photo = "—"

        if (
            issue["latitude"]
            and issue["longitude"]
        ):
            location = (
                f'{esc(issue["location"])}'
                f'<br><small>'
                f'{esc(issue["latitude"])}, '
                f'{esc(issue["longitude"])}'
                f'</small>'
            )
        else:
            location = esc(issue["location"])

        action = "🔒 View Only"

        if session["role"] == "Authority":

            verify = (
                ""
                if issue["verified"]
                else f"""
                <a class="btn btn-purple"
                   href="/verify/{issue["id"]}">
                    🔍 Verify
                </a>
                """
            )

            if issue["status"] == "Reported":

                status_button = f"""
                <a class="btn btn-orange"
                   href="/update/{issue["id"]}/In%20Progress">
                    🟡 Start
                </a>
                """

            elif issue["status"] == "In Progress":

                status_button = f"""
                <a class="btn btn-green"
                   href="/update/{issue["id"]}/Resolved">
                    ✅ Resolve
                </a>
                """

            else:
                status_button = "✅ Resolved"

            action = verify + status_button

        trs += f"""
        <tr>
            <td>📍 {location}</td>
            <td>{esc(issue["issue_type"])}</td>
            <td>{esc(issue["description"]) or "-"}</td>
            <td>{badge(issue["priority"])}</td>
            <td>{photo}</td>
            <td>{esc(issue["status"])}</td>
            <td>{esc(issue["created_at"])}</td>
            <td>{action}</td>
        </tr>
        """

    body = f"""
    <div class="container">

        <h1 style="color:#304a7c">
            📊 Real-Time Monitoring Dashboard
        </h1>

        <p style="color:#64748b">
            Monitor inspection findings and corrective action status.
        </p>

        <div class="stats">

            <div class="stat">
                <div class="num">{total}</div>
                <small>Total Issues</small>
            </div>

            <div class="stat">
                <div class="num">{reported}</div>
                <small>🔴 Reported</small>
            </div>

            <div class="stat">
                <div class="num">{progress}</div>
                <small>🟡 In Progress</small>
            </div>

            <div class="stat">
                <div class="num">{resolved}</div>
                <small>🟢 Resolved</small>
            </div>

            <div class="stat">
                <div class="num">{high}</div>
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

                    {trs or '<tr><td colspan="8">🎉 No issues reported yet.</td></tr>'}

                </table>

            </div>

        </div>

    </div>
    """

    return page(body, "Dashboard")


# ============================================================
# VERIFY AND UPDATE ISSUES
# ============================================================

@app.route("/verify/<int:issue_id>")
def verify_issue(issue_id):

    if not role_required("Authority"):
        return "Access denied", 403

    conn = db()

    conn.execute(
        "UPDATE issues SET verified=1 WHERE id=?",
        (issue_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/update/<int:issue_id>/<status>")
def update_status(issue_id, status):

    if not role_required("Authority"):
        return "Access denied", 403

    if status not in (
        "Reported",
        "In Progress",
        "Resolved"
    ):
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
        """
        SELECT location, COUNT(*) AS reports
        FROM issues
        GROUP BY location
        ORDER BY reports DESC
        """
    ).fetchall()

    workers = conn.execute(
        """
        SELECT
            u.name,
            u.unique_id,
            COUNT(i.id) AS inspections
        FROM users u
        LEFT JOIN issues i ON u.id=i.reporter_id
        WHERE u.role IN ('Worker','Inspector')
        GROUP BY u.id
        ORDER BY inspections DESC
        """
    ).fetchall()

    conn.close()

    location_rows = "".join(
        f"""
        <tr>
            <td>{esc(row["location"])}</td>
            <td>{row["reports"]}</td>
            <td>{badge(priority_for(row["reports"]))}</td>
        </tr>
        """
        for row in locations
    )

    worker_rows = "".join(
        f"""
        <tr>
            <td>{esc(row["name"])}</td>
            <td>{esc(row["unique_id"])}</td>
            <td>{row["inspections"]}</td>
        </tr>
        """
        for row in workers
    )

    body = f"""
    <div class="container">

        <div class="card">

            <h1>📈 Inspection Analytics</h1>

            <div class="info">
                Locations with repeated problems automatically receive
                a higher smart priority.
            </div>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Location</th>
                        <th>Reports</th>
                        <th>Priority</th>
                    </tr>

                    {location_rows or '<tr><td colspan="3">No data available.</td></tr>'}

                </table>

            </div>

        </div>

        <div class="card">

            <h2>👷 Inspection Activity</h2>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Name</th>
                        <th>Unique ID</th>
                        <th>Reports Submitted</th>
                    </tr>

                    {worker_rows or '<tr><td colspan="3">No activity yet.</td></tr>'}

                </table>

            </div>

        </div>

    </div>
    """

    return page(body, "Analytics")


# ============================================================
# CCTV
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

        feed = request.form.get(
            "feed_url", ""
        ).strip()

        if not location or not feed:

            message = """
            <div class="info warning">
                Please enter both location and URL.
            </div>
            """

        elif not (
            feed.startswith("http://")
            or feed.startswith("https://")
        ):

            message = """
            <div class="info warning">
                Please enter a valid HTTP or HTTPS URL.
            </div>
            """

        else:

            conn.execute(
                """
                INSERT INTO cctv_feeds
                (location,feed_url,created_at)
                VALUES(?,?,?)
                """,
                (
                    location,
                    feed,
                    now()
                )
            )

            conn.commit()

            message = """
            <div class="info success">
                ✅ CCTV feed added successfully.
            </div>
            """

    feeds = conn.execute(
        """
        SELECT *
        FROM cctv_feeds
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    rows = "".join(
        f"""
        <tr>
            <td>{esc(feed["location"])}</td>
            <td>{esc(feed["created_at"])}</td>
            <td>
                <a class="btn"
                   href="{esc(feed["feed_url"])}"
                   target="_blank"
                   rel="noopener">
                    📹 Open Feed
                </a>
            </td>
        </tr>
        """
        for feed in feeds
    )

    body = f"""
    <div class="container">

        <div class="card">

            <h1>📹 CCTV Monitoring</h1>

            {message}

            <form method="POST"
                  class="form-grid">

                <div class="field">
                    <label>Camera Location</label>
                    <input name="location" required>
                </div>

                <div class="field">
                    <label>Authorized Monitoring URL</label>
                    <input
                        type="url"
                        name="feed_url"
                        required
                    >
                </div>

                <div class="full">
                    <button class="btn">
                        ➕ Add CCTV Feed
                    </button>
                </div>

            </form>

        </div>

        <div class="card">

            <h2>Configured Feeds</h2>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Location</th>
                        <th>Added</th>
                        <th>Feed</th>
                    </tr>

                    {rows or '<tr><td colspan="3">No feeds configured.</td></tr>'}

                </table>

            </div>

        </div>

    </div>
    """

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

        if session["role"] != "Authority":
            conn.close()
            return "Only Authority can create meetings", 403

        title = request.form.get(
            "title", ""
        ).strip()

        if not title:

            message = """
            <div class="info warning">
                Please enter a meeting title.
            </div>
            """

        else:

            code = uuid.uuid4().hex[:10].upper()

            meeting_url = url_for(
                "meeting_room",
                meeting_code=code,
                _external=True
            )

            conn.execute(
                """
                INSERT INTO meetings
                (title,meeting_url,created_at,created_by,meeting_code)
                VALUES(?,?,?,?,?)
                """,
                (
                    title,
                    meeting_url,
                    now(),
                    session["user_id"],
                    code
                )
            )

            conn.commit()

            message = f"""
            <div class="info success">
                🎥 Meeting created successfully!<br>
                Meeting Code:
                <b>{esc(code)}</b>
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

    rows = "".join(
        f"""
        <tr>
            <td>{esc(meeting["title"])}</td>
            <td>{esc(meeting["authority_name"] or "Authority")}</td>
            <td>{esc(meeting["created_at"])}</td>
            <td>
                <a class="btn btn-purple"
                   href="/meeting/{esc(meeting["meeting_code"])}">
                    🎥 Join
                </a>
            </td>
        </tr>
        """
        for meeting in meeting_list
    )

    body = f"""
    <div class="container">

        {message}

        {form}

        <div class="card">

            <h2>🎥 Available Meetings</h2>

            <div class="table-wrap">

                <table>

                    <tr>
                        <th>Meeting</th>
                        <th>Created By</th>
                        <th>Created</th>
                        <th>Join</th>
                    </tr>

                    {rows or '<tr><td colspan="4">No meetings available.</td></tr>'}

                </table>

            </div>

        </div>

    </div>
    """

    return page(body, "Meetings")


@app.route("/meeting/<meeting_code>")
def meeting_room(meeting_code):

    if not logged_in():
        return redirect(url_for("login"))

    conn = db()

    meeting = conn.execute(
        """
        SELECT *
        FROM meetings
        WHERE meeting_code=?
        """,
        (meeting_code,)
    ).fetchone()

    if not meeting:
        conn.close()
        return "Meeting not found", 404

    conn.execute(
        """
        INSERT OR IGNORE INTO meeting_participants
        (meeting_id,user_id,joined_at)
        VALUES(?,?,?)
        """,
        (
            meeting["id"],
            session["user_id"],
            now()
        )
    )

    conn.commit()

    participants = conn.execute(
        """
        SELECT u.name,u.role
        FROM meeting_participants p
        JOIN users u ON p.user_id=u.id
        WHERE p.meeting_id=?
        """,
        (meeting["id"],)
    ).fetchall()

    conn.close()

    participant_rows = "".join(
        f"""
        <tr>
            <td>{esc(person["name"])}</td>
            <td>{esc(person["role"])}</td>
            <td>🟢 Joined</td>
        </tr>
        """
        for person in participants
    )

    body = f"""
    <div class="container">

        <div class="card" style="text-align:center">

            <h1>🎥 Inspection Coordination Room</h1>

            <div class="info success">

                🟢 You joined successfully!<br><br>

                Meeting:
                <b>{esc(meeting["title"])}</b><br>

                Code:
                <b>{esc(meeting_code)}</b><br>

                Joined as:
                <b>{esc(session["name"])}</b>

            </div>

            <p style="color:#64748b">
                This is a prototype meeting coordination module.
                A WebRTC or video conferencing service can be integrated
                for live video conferencing in production.
            </p>

            <a class="btn"
               href="/meetings">
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

                    {participant_rows}

                </table>

            </div>

        </div>

    </div>
    """

    return page(body, "Meeting Room")


# ============================================================
# API - LATEST MEETING
# ============================================================

@app.route("/api/latest-meeting")
def latest_meeting():

    if not logged_in():
        return jsonify({"logged_in": False}), 401

    if session.get("role") not in (
        "Worker",
        "Inspector"
    ):
        return jsonify({"meeting": None})

    conn = db()

    meeting = conn.execute(
        """
        SELECT id,title,created_at,meeting_url
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
            "created_at": meeting["created_at"],
            "meeting_url": meeting["meeting_url"]
        }
    })


# ============================================================
# ERROR HANDLER
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    body = """
    <div class="container">
        <div class="card">
            <h1>⚠️ File Too Large</h1>
            <p>
                Please upload an image smaller than 10 MB.
            </p>
            <a class="btn" href="/home">
                🏠 Go Home
            </a>
        </div>
    </div>
    """

    return page(body, "Upload Error"), 413


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
