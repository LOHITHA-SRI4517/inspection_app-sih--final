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
# APP CONFIGURATION
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

STYLE = r"""
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Inter,Arial,sans-serif;background:#f5f7fb;color:#172033}
a{text-decoration:none;color:inherit}

.navbar{
    position:sticky;top:0;z-index:50;background:#fff;
    border-bottom:1px solid #e7ebf3;padding:15px 5%;
    display:flex;justify-content:space-between;align-items:center;gap:15px
}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;color:#172554}
.brand-icon{
    width:38px;height:38px;border-radius:11px;background:#2563eb;
    color:#fff;display:grid;place-items:center
}
.navlinks{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.navlinks a{padding:9px 12px;border-radius:9px;color:#475569;font-size:14px}
.navlinks a:hover{background:#eef4ff;color:#1d4ed8}

.container{max-width:1250px;margin:auto;padding:30px 20px}

.hero{
    background:linear-gradient(135deg,#eff6ff,#fff);
    border:1px solid #dbeafe;border-radius:26px;
    padding:65px 30px;text-align:center
}
.hero h1{
    font-size:44px;line-height:1.1;color:#17327c;
    margin:0 auto 16px;max-width:900px
}
.hero p{
    font-size:18px;color:#64748b;max-width:760px;
    margin:0 auto 28px;line-height:1.7
}

.card{
    background:#fff;border:1px solid #e7ebf3;border-radius:18px;
    padding:24px;margin-bottom:22px;
    box-shadow:0 8px 28px rgba(15,23,42,.05)
}

.grid{
    display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
    gap:18px
}

.feature{
    background:#fff;border:1px solid #e7ebf3;
    border-radius:18px;padding:23px
}
.feature-icon{font-size:30px}
.feature h3{margin:10px 0 7px;color:#1e3a8a}
.feature p{color:#64748b;line-height:1.6}

.btn{
    display:inline-block;border:0;background:#2563eb;color:#fff;
    padding:11px 17px;border-radius:9px;cursor:pointer;
    font-weight:700;font-size:14px;margin:3px
}
.btn:hover{filter:brightness(.95)}
.btn-green{background:#059669}
.btn-purple{background:#7c3aed}
.btn-orange{background:#ea580c}
.btn-red{background:#dc2626}
.btn-light{background:#eef4ff;color:#1d4ed8}

.section-title{
    display:flex;justify-content:space-between;align-items:center;
    gap:10px;flex-wrap:wrap
}
.section-title h1,.section-title h2{margin:0;color:#172554}

.stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
    gap:15px;margin:22px 0
}
.stat{
    background:#fff;border:1px solid #e7ebf3;
    border-radius:16px;padding:20px
}
.stat .num{font-size:32px;font-weight:800;color:#2563eb}
.stat small{color:#64748b}

.form-grid{
    display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
    gap:15px
}
.field label{
    display:block;font-weight:700;font-size:14px;
    margin-bottom:6px;color:#334155
}
input,select,textarea{
    width:100%;padding:12px 13px;border:1px solid #cbd5e1;
    border-radius:9px;font-size:15px;background:#fff
}
textarea{min-height:110px;resize:vertical}
.full{grid-column:1/-1}

.info{
    background:#eff6ff;border:1px solid #bfdbfe;
    border-left:5px solid #2563eb;padding:14px 16px;
    border-radius:10px;margin:15px 0;line-height:1.6
}
.success{background:#ecfdf5;border-color:#a7f3d0;border-left-color:#059669}
.warning{background:#fff7ed;border-color:#fed7aa;border-left-color:#ea580c}
.error{color:#b91c1c;font-weight:700}

.badge{
    display:inline-block;padding:5px 9px;border-radius:999px;
    font-size:12px;font-weight:800
}
.low{background:#dcfce7;color:#166534}
.medium{background:#fef3c7;color:#92400e}
.high{background:#fee2e2;color:#991b1b}
.blue{background:#dbeafe;color:#1d4ed8}

.table-wrap{overflow:auto}
table{width:100%;border-collapse:collapse;min-width:760px}
th{background:#172554;color:#fff}
th,td{
    padding:12px;border-bottom:1px solid #e5e7eb;
    text-align:left;vertical-align:middle
}
tr:hover td{background:#f8fafc}

.evidence{
    width:95px;height:70px;object-fit:cover;border-radius:8px;
    border:1px solid #e5e7eb
}

.workflow{
    display:flex;flex-wrap:wrap;justify-content:center;
    gap:8px;align-items:center;font-weight:700;color:#334155
}
.step{
    background:#eff6ff;border:1px solid #bfdbfe;
    padding:10px 13px;border-radius:10px
}

.footer{text-align:center;color:#64748b;padding:30px}
.camera{
    width:100%;background:#0f172a;border-radius:14px;
    min-height:280px;object-fit:cover
}
.login-box{max-width:480px;margin:45px auto}
.role{
    font-size:13px;background:#eef2ff;color:#3730a3;
    padding:5px 9px;border-radius:999px;font-weight:800
}
.empty{text-align:center;padding:35px;color:#64748b}
.pill-row{display:flex;gap:8px;flex-wrap:wrap}

.notice{
    position:fixed;right:18px;bottom:18px;z-index:100;
    background:#172554;color:white;padding:18px;
    border-radius:14px;box-shadow:0 10px 30px rgba(0,0,0,.25);
    display:none;max-width:350px
}
.video-box{background:#111827;border-radius:16px;padding:10px}
.meeting-code{
    font-family:monospace;font-size:20px;
    font-weight:800;letter-spacing:2px
}
.status-flow{
    display:flex;gap:8px;flex-wrap:wrap;margin:15px 0
}

@media(max-width:700px){
    .navbar{align-items:flex-start;flex-direction:column}
    .hero{padding:42px 18px}
    .hero h1{font-size:31px}
    .container{padding:18px 12px}
    .form-grid{grid-template-columns:1fr}
    .full{grid-column:auto}
    .card{padding:18px}
}
</style>
"""


LAYOUT = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title or 'SIMMS' }}</title>
</head>
<body>

{{ navbar|safe }}

<main class="container">
{{ body|safe }}
</main>

<div id="meetingNotice" class="notice"></div>

<div class="footer">
SIMMS • Smart Real-Time Monitoring & Inspection System
</div>

<script>
(function(){
    const notice = document.getElementById("meetingNotice");
    if (!notice) return;

    function checkMeeting(){
        fetch("/api/latest-meeting")
        .then(response => {
            if (!response.ok) return null;
            return response.json();
        })
        .then(data => {
            if (!data || !data.meeting) return;

            const meeting = data.meeting;
            const seenKey = "seen_meeting_" + meeting.id;

            if (!localStorage.getItem(seenKey)) {
                notice.innerHTML =
                    '<b>🎥 New Team Meeting</b><br><br>' +
                    meeting.title +
                    '<br><br><a class="btn btn-purple" href="' +
                    meeting.meeting_url +
                    '">Join Now</a>' +
                    '<button class="btn btn-light" onclick="closeMeetingNotice(' +
                    meeting.id + ')">Later</button>';

                notice.style.display = "block";
            }
        })
        .catch(() => {});
    }

    window.closeMeetingNotice = function(id){
        localStorage.setItem("seen_meeting_" + id, "1");
        notice.style.display = "none";
    };

    checkMeeting();
    setInterval(checkMeeting, 30000);
})();
</script>

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


def priority_for(count):
    if count > 3:
        return "High"
    if count >= 2:
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

    cls = classes.get(priority, "low")
    icon = icons.get(priority, "⚪")

    return f'<span class="badge {cls}">{icon} {priority}</span>'


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


def nav():
    if not logged_in():
        return """
        <div class="navbar">
            <a class="brand" href="/">
                <span class="brand-icon">🏛️</span> SIMMS
            </a>
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

    if session.get("role") == "Authority":
        links += [
            '<a href="/users">👥 Users</a>',
            '<a href="/assignments">🎲 Assign</a>',
            '<a href="/analytics">📈 Analytics</a>',
            '<a href="/cctv">📹 CCTV</a>'
        ]

    links.append('<a href="/meetings">🎥 Meetings</a>')
    links.append('<a href="/logout">🚪 Logout</a>')

    return f"""
    <div class="navbar">
        <a class="brand" href="/home">
            <span class="brand-icon">🏛️</span> SIMMS
        </a>
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
# DATABASE INITIALIZATION
# ============================================================

def add_column_if_missing(conn, table, column, definition):
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
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
        created_at TEXT NOT NULL
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

    CREATE TABLE IF NOT EXISTS assignments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        location TEXT NOT NULL,
        assigned_at TEXT NOT NULL,
        status TEXT DEFAULT 'Assigned',
        face_verified INTEGER DEFAULT 0,
        face_photo TEXT,
        verified_at TEXT
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
        UNIQUE(meeting_id,user_id)
    );
    """)

    # Backward compatibility for older database versions
    columns_to_check = [
        ("assignments", "face_verified", "INTEGER DEFAULT 0"),
        ("assignments", "face_photo", "TEXT"),
        ("assignments", "verified_at", "TEXT"),

        ("issues", "priority", "TEXT DEFAULT 'Low'"),
        ("issues", "photo", "TEXT"),
        ("issues", "reporter_id", "INTEGER"),
        ("issues", "latitude", "TEXT"),
        ("issues", "longitude", "TEXT"),
        ("issues", "verified", "INTEGER DEFAULT 0"),

        ("meetings", "created_by", "INTEGER"),
        ("meetings", "meeting_code", "TEXT")
    ]

    for table, column, definition in columns_to_check:
        add_column_if_missing(conn, table, column, definition)

    # Demo users
    defaults = [
        ("ADMIN001", "System Authority", "admin123", "Authority"),
        ("INS001", "Inspection Officer", "inspector123", "Inspector"),
        ("WORK001", "Demo Field Worker", "worker123", "Worker")
    ]

    for uid, name, password, role in defaults:
        existing = conn.execute(
            "SELECT 1 FROM users WHERE unique_id=?",
            (uid,)
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO users(
                    unique_id,name,password,role,created_at
                )
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
# LANDING PAGE
# ============================================================

@app.route("/")
def landing():
    body = """
    <section class="hero">
        <div class="pill-row" style="justify-content:center">
            <span class="role">SMART INDIA HACKATHON • SIH26095</span>
        </div>

        <h1>Smart Real-Time Monitoring & Inspection System</h1>

        <p>
            Centralized digital inspection platform for surprise assignments,
            identity confirmation, geo-tagged evidence, real-time monitoring
            and faster corrective action.
        </p>

        <a class="btn" href="/login">🔐 Login to System</a>
        <a class="btn btn-light" href="#features">Explore Features</a>
    </section>

    <section id="features" class="grid" style="margin-top:22px">
        <div class="feature">
            <div class="feature-icon">🎲</div>
            <h3>Random Assignment</h3>
            <p>Inspection duties are assigned automatically to reduce predictable reporting.</p>
        </div>

        <div class="feature">
            <div class="feature-icon">📷</div>
            <h3>Camera Verification</h3>
            <p>A worker captures verification evidence before starting an assigned inspection.</p>
        </div>

        <div class="feature">
            <div class="feature-icon">📍</div>
            <h3>Geo-Tagged Evidence</h3>
            <p>Capture inspection findings with GPS coordinates, time and photo evidence.</p>
        </div>

        <div class="feature">
            <div class="feature-icon">📊</div>
            <h3>Live Dashboard</h3>
            <p>Officials can monitor assignments, findings, priorities and corrective action.</p>
        </div>
    </section>

    <div class="card" style="margin-top:22px">
        <h2>Inspection Workflow</h2>
        <div class="workflow">
            <span class="step">1. Assign</span> →
            <span class="step">2. Verify</span> →
            <span class="step">3. Inspect</span> →
            <span class="step">4. Capture</span> →
            <span class="step">5. Analyze</span> →
            <span class="step">6. Resolve</span>
        </div>
    </div>
    """

    return page(body, "SIMMS • Smart Inspection")


# ============================================================
# LOGIN
# ============================================================

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

        error = "Invalid Unique ID or Password."

    error_html = ""
    if error:
        error_html = f"""
        <div class="info" style="color:#b91c1c">
            ❌ {esc(error)}
        </div>
        """

    body = f"""
    <div class="card login-box">
        <div style="text-align:center">
            <div class="brand-icon" style="margin:auto">🔐</div>
            <h1 style="color:#172554">System Login</h1>
            <p style="color:#64748b">
                Sign in to access your inspection workspace.
            </p>
        </div>

        {error_html}

        <form method="POST">
            <div class="field">
                <label>Unique ID</label>
                <input name="unique_id"
                       placeholder="ADMIN001 / INS001 / WORK001"
                       required>
            </div>

            <div class="field">
                <label>Password</label>
                <input type="password"
                       name="password"
                       placeholder="Enter password"
                       required>
            </div>

            <button class="btn" style="width:100%;margin-top:10px">
                Login
            </button>
        </form>

        <div class="info" style="margin-top:18px">
            <b>Demo accounts</b><br>
            Authority: ADMIN001 / admin123<br>
            Inspector: INS001 / inspector123<br>
            Worker: WORK001 / worker123
        </div>

        <a href="/">← Back to home</a>
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
        <a class="btn btn-light" href="/meetings">
            🎥 Meetings
        </a>
        """
    else:
        buttons += """
        <a class="btn btn-orange" href="/assignments">
            🎲 Assign Inspection
        </a>
        <a class="btn btn-purple" href="/users">
            👥 Users
        </a>
        <a class="btn btn-green" href="/analytics">
            📈 Analytics
        </a>
        """

    body = f"""
    <div class="card">
        <div class="section-title">
            <div>
                <h1>Welcome, {esc(session["name"])} 👋</h1>
                <p style="color:#64748b">Your SIMMS workspace</p>
            </div>
            <span class="role">{esc(role)}</span>
        </div>

        <div class="info">
            🔐 Role-based access is enabled.
            Your available modules are shown below.
        </div>

        <div class="pill-row">{buttons}</div>
    </div>

    <div class="card">
        <h2>🎯 Inspection Workflow</h2>
        <div class="workflow">
            <span class="step">Authority Assigns</span> →
            <span class="step">Camera Verify</span> →
            <span class="step">Field Inspection</span> →
            <span class="step">GPS + Evidence</span> →
            <span class="step">Priority Analysis</span> →
            <span class="step">Verify & Resolve</span>
        </div>
    </div>
    """

    return page(body, "Home")


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
                Please enter a valid name, password of at least
                4 characters and a valid role.
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
                INSERT INTO users(
                    unique_id,name,password,role,created_at
                ) VALUES(?,?,?,?,?)
                """,
                (
                    uid, name,
                    generate_password_hash(password),
                    role, now()
                )
            )
            conn.commit()
            conn.close()

            message = f"""
            <div class="info success">
                ✅ User created successfully.<br>
                ID: <b>{esc(uid)}</b> •
                Name: <b>{esc(name)}</b> •
                Role: <b>{esc(role)}</b>
            </div>
            """

    conn = db()
    rows = conn.execute(
        "SELECT unique_id,name,role,created_at FROM users ORDER BY id DESC"
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
                <input type="password" name="password" required>
            </div>

            <div class="field">
                <label>Role</label>
                <select name="role">
                    <option>Worker</option>
                    <option>Inspector</option>
                    <option>Authority</option>
                </select>
            </div>

            <div class="field" style="display:flex;align-items:end">
                <button class="btn btn-purple">➕ Create User</button>
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
    """

    return page(body, "Users")


# ============================================================
# RANDOM ASSIGNMENTS
# ============================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():
    if not role_required("Authority"):
        return "Access denied", 403

    message = ""
    conn = db()

    workers = conn.execute(
        """
        SELECT id,name,unique_id
        FROM users
        WHERE role IN ('Worker','Inspector')
        """
    ).fetchall()

    if request.method == "POST":
        location = request.form.get("location", "").strip()

        if not location:
            message = """
            <div class="info warning">Enter an inspection location.</div>
            """

        elif not workers:
            message = """
            <div class="info warning">
                No Worker or Inspector accounts are available.
            </div>
            """

        else:
            selected = random.choice(workers)

            conn.execute(
                """
                INSERT INTO assignments(
                    user_id,location,assigned_at,status,face_verified
                )
                VALUES(?,?,?,?,0)
                """,
                (
                    selected["id"],
                    location,
                    now(),
                    "Assigned"
                )
            )

            conn.commit()

            message = f"""
            <div class="info success">
                🎲 Inspection assigned successfully!<br>
                📍 <b>{esc(location)}</b><br>
                👷 Assigned to <b>{esc(selected["name"])}</b>
                ({esc(selected["unique_id"])})
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

    trs = ""

    for r in rows:
        if r["status"] == "Completed":
            workflow_status = '<span class="badge low">✅ Completed</span>'
        elif r["face_verified"]:
            workflow_status = '<span class="badge blue">📷 Verified</span>'
        else:
            workflow_status = '<span class="badge medium">⏳ Verification Pending</span>'

        trs += f"""
        <tr>
            <td>{esc(r["location"])}</td>
            <td>{esc(r["name"])}</td>
            <td>{esc(r["unique_id"])}</td>
            <td>{esc(r["assigned_at"])}</td>
            <td>{workflow_status}</td>
            <td>{esc(r["status"])}</td>
        </tr>
        """

    body = f"""
    <div class="card">
        <h1>🎲 Automated Inspection Assignment</h1>
        <p style="color:#64748b">
            Randomly assign a field inspection to an eligible
            Worker or Inspector.
        </p>

        {message}

        <form method="POST">
            <div class="field">
                <label>📍 Location to Inspect</label>
                <input name="location"
                       placeholder="Example: District Institute, Raipur"
                       required>
            </div>
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
                    <th>Verification</th>
                    <th>Status</th>
                </tr>
                {trs or '<tr><td colspan="6" class="empty">No assignments yet.</td></tr>'}
            </table>
        </div>
    </div>
    """

    return page(body, "Assignments")


# ============================================================
# WORKER ASSIGNMENTS
# ============================================================

@app.route("/my-assignments")
def my_assignments():
    if (
        not logged_in() or
        session.get("role") not in ("Worker", "Inspector")
    ):
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

    trs = ""

    for r in rows:
        if r["status"] == "Completed":
            action = '<span class="badge low">✅ Completed</span>'

        elif r["face_verified"]:
            action = f"""
            <a class="btn btn-green"
               href="/inspection/{r['id']}">
               📋 Start Inspection
            </a>
            """

        else:
            action = f"""
            <a class="btn btn-purple"
               href="/face-verification/{r['id']}">
               📷 Verify Identity
            </a>
            """

        verification = (
            '<span class="badge low">📷 Verified</span>'
            if r["face_verified"]
            else '<span class="badge medium">⏳ Required</span>'
        )

        trs += f"""
        <tr>
            <td>📍 {esc(r["location"])}</td>
            <td>{esc(r["assigned_at"])}</td>
            <td>{verification}</td>
            <td>{esc(r["status"])}</td>
            <td>{action}</td>
        </tr>
        """

    body = f"""
    <div class="card">
        <div class="section-title">
            <h1>📋 My Inspection Assignments</h1>
            <span class="role">{esc(session["role"])}</span>
        </div>

        <div class="info">
            🔐 Complete camera identity verification before starting
            an assigned inspection.
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
                {trs or '<tr><td colspan="5" class="empty">📭 No assignments available.</td></tr>'}
            </table>
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
            return "Please capture your verification photo.", 400

        if not allowed_file(photo.filename):
            conn.close()
            return "Invalid image format.", 400

        filename = (
            "face_" +
            str(session["user_id"]) +
            "_" +
            uuid.uuid4().hex +
            ".jpg"
        )

        photo.save(os.path.join(FACE_FOLDER, filename))

        conn.execute(
            """
            UPDATE assignments
            SET face_verified=1,
                face_photo=?,
                verified_at=?
            WHERE id=? AND user_id=?
            """,
            (
                filename,
                now(),
                assignment_id,
                session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        return redirect(
            url_for("inspection", assignment_id=assignment_id)
        )

    conn.close()

    body = f"""
    <div class="card" style="max-width:700px;margin:auto">
        <h1>📷 Security Camera Verification</h1>

        <div class="info">
            Assigned location: <b>{esc(assignment["location"])}</b><br>
            📸 Your captured photo will be stored as verification
            evidence for this inspection assignment.
        </div>

        <div class="video-box">
            <video id="video"
                   class="camera"
                   autoplay
                   playsinline></video>
        </div>

        <canvas id="canvas" hidden></canvas>

        <form id="faceForm"
              method="POST"
              enctype="multipart/form-data">

            <input id="face_photo"
                   name="face_photo"
                   type="file"
                   accept="image/*"
                   hidden>

            <button type="button"
                    class="btn btn-purple"
                    onclick="captureFace()">
                📸 Capture & Verify
            </button>
        </form>

        <p id="message" class="error"></p>
    </div>

    <script>
    const video = document.getElementById("video");

    if (navigator.mediaDevices &&
        navigator.mediaDevices.getUserMedia) {

        navigator.mediaDevices.getUserMedia({
            video: true
        })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(() => {
            document.getElementById("message").textContent =
                "❌ Camera access denied. Please allow camera permission.";
        });

    } else {
        document.getElementById("message").textContent =
            "❌ Camera is not supported by this browser.";
    }

    function captureFace(){
        if (!video.videoWidth) {
            alert("Please wait for the camera to start.");
            return;
        }

        const canvas = document.getElementById("canvas");

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        canvas.getContext("2d").drawImage(
            video, 0, 0,
            canvas.width, canvas.height
        );

        canvas.toBlob(blob => {
            if (!blob) {
                alert("Could not capture image.");
                return;
            }

            const file = new File(
                [blob],
                "face.jpg",
                {type:"image/jpeg"}
            );

            const dt = new DataTransfer();
            dt.items.add(file);

            document.getElementById("face_photo").files =
                dt.files;

            const stream = video.srcObject;

            if (stream) {
                stream.getTracks().forEach(
                    track => track.stop()
                );
            }

            document.getElementById("faceForm").submit();

        }, "image/jpeg");
    }
    </script>
    """

    return page(body, "Camera Verification")


# ============================================================
# WORKER INSPECTION FORM
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

        location = assignment["location"]

        cleanliness = request.form.get("cleanliness", "Yes")
        safety = request.form.get("safety", "Yes")
        facilities = request.form.get("facilities", "Yes")

        description = request.form.get(
            "description", ""
        ).strip()

        latitude = request.form.get(
            "latitude", ""
        ).strip()

        longitude = request.form.get(
            "longitude", ""
        ).strip()

        # GPS IS REQUIRED
        if not latitude or not longitude:
            conn.close()
            return """
            GPS location is required.
            Please allow location permission before submitting.
            """, 400

        photo_name = None
        photo = request.files.get("photo")

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                conn.close()
                return "Invalid photo format.", 400

            ext = secure_filename(
                photo.filename
            ).rsplit(".", 1)[-1].lower()

            photo_name = uuid.uuid4().hex + "." + ext

            photo.save(
                os.path.join(UPLOAD_FOLDER, photo_name)
            )

        detected = [
            issue
            for issue, answer in (
                ("Cleanliness", cleanliness),
                ("Safety", safety),
                ("Facilities", facilities)
            )
            if answer == "No"
        ]

        for issue_type in detected:

            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM issues
                WHERE LOWER(location)=LOWER(?)
                """,
                (location,)
            ).fetchone()[0] + 1

            priority = priority_for(count)

            conn.execute(
                """
                INSERT INTO issues(
                    location,issue_type,description,
                    created_at,status,priority,photo,
                    reporter_id,latitude,longitude,verified
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,0)
                """,
                (
                    location,
                    issue_type,
                    description,
                    now(),
                    "Reported",
                    priority,
                    photo_name,
                    session["user_id"],
                    latitude,
                    longitude
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

        if detected:
            result = "⚠️ Issues reported: " + ", ".join(detected)
        else:
            result = "✅ Inspection completed. No issues found."

        body = f"""
        <div class="card" style="text-align:center">
            <h1>✅ Inspection Submitted</h1>

            <div class="info success">
                📍 {esc(location)}<br><br>
                {esc(result)}<br><br>
                📍 GPS location recorded successfully.
            </div>

            <a class="btn" href="/my-assignments">
                📋 My Assignments
            </a>

            <a class="btn btn-green" href="/dashboard">
                📊 Dashboard
            </a>
        </div>
        """

        return page(body, "Inspection Submitted")

    conn.close()

    body = f"""
    <div class="card">

        <h1>📋 Worker Inspection Form</h1>

        <div class="info success">
            📍 Location: <b>{esc(assignment["location"])}</b><br>
            📷 Camera Verification: <b>Completed ✅</b><br>
            📍 GPS Location: <b>Required before submission</b>
        </div>

        <div class="status-flow">
            <span class="badge blue">1. Assigned ✓</span>
            <span class="badge blue">2. Camera Verified ✓</span>
            <span class="badge medium">3. Inspection in Progress</span>
        </div>

        <form method="POST"
              enctype="multipart/form-data"
              class="form-grid"
              onsubmit="return validateLocation()">

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
                <label>📸 Photo Evidence (Optional)</label>
                <input type="file"
                       name="photo"
                       accept="image/*">
            </div>

            <div class="field">
                <label>Latitude *</label>
                <input id="latitude"
                       name="latitude"
                       placeholder="GPS Latitude"
                       readonly
                       required>
            </div>

            <div class="field">
                <label>Longitude *</label>
                <input id="longitude"
                       name="longitude"
                       placeholder="GPS Longitude"
                       readonly
                       required>
            </div>

            <div class="full">
                <button type="button"
                        class="btn btn-purple"
                        onclick="getLocation()">
                    📍 Get My Current Location
                </button>

                <span id="locationStatus"
                      style="font-size:14px;color:#64748b">
                    GPS location not captured yet.
                </span>
            </div>

            <div class="field full">
                <label>📝 Description</label>
                <textarea name="description"
                    placeholder="Describe the issue or observation...">
                </textarea>
            </div>

            <div class="full">
                <button class="btn" type="submit">
                    📤 Submit Inspection
                </button>
            </div>

        </form>
    </div>

    <script>
    function getLocation(){

        const status =
            document.getElementById("locationStatus");

        if (!navigator.geolocation) {
            alert(
                "Geolocation is not supported by this browser."
            );
            return;
        }

        status.textContent = "📍 Getting your location...";

        navigator.geolocation.getCurrentPosition(

            position => {
                document.getElementById("latitude").value =
                    position.coords.latitude;

                document.getElementById("longitude").value =
                    position.coords.longitude;

                status.textContent =
                    "✅ GPS location captured successfully.";
            },

            () => {
                status.textContent =
                    "❌ Location access denied. Please allow location permission.";
            },

            {
                enableHighAccuracy:true,
                timeout:10000,
                maximumAge:0
            }
        );
    }

    function validateLocation(){
        const lat =
            document.getElementById("latitude").value;

        const lon =
            document.getElementById("longitude").value;

        if (!lat || !lon) {
            alert(
                "Please capture your GPS location before submitting."
            );
            return false;
        }

        return true;
    }
    </script>
    """

    return page(body, "Worker Inspection Form")


# ============================================================
# FILE SERVING
# ============================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/faces/<path:filename>")
def face_file(filename):
    if not role_required("Authority"):
        return "Access denied", 403

    return send_from_directory(FACE_FOLDER, filename)


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))

    conn = db()

    # Issue reports visible based on role
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

    # Assignment statistics
    if session["role"] == "Authority":
        assignment_stats = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='Assigned' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN face_verified=1 THEN 1 ELSE 0 END) AS verified
            FROM assignments
        """).fetchone()
    else:
        assignment_stats = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='Assigned' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN face_verified=1 THEN 1 ELSE 0 END) AS verified
            FROM assignments
            WHERE user_id=?
        """, (session["user_id"],)).fetchone()

    conn.close()

    total = len(issues)
    reported = sum(i["status"] == "Reported" for i in issues)
    progress = sum(i["status"] == "In Progress" for i in issues)
    resolved = sum(i["status"] == "Resolved" for i in issues)
    high = sum(i["priority"] == "High" for i in issues)

    assignments_total = assignment_stats["total"] or 0
    assignments_pending = assignment_stats["pending"] or 0
    assignments_completed = assignment_stats["completed"] or 0
    assignments_verified = assignment_stats["verified"] or 0

    trs = ""

    for issue in issues:

        if issue["photo"]:
            photo = (
                f'<a href="/uploads/{esc(issue["photo"])}" '
                f'target="_blank">'
                f'<img class="evidence" '
                f'src="/uploads/{esc(issue["photo"])}">'
                f'</a>'
            )
        else:
            photo = "—"

        loc = esc(issue["location"])

        if issue["latitude"] and issue["longitude"]:
            loc += (
                f'<br><small>📍 {esc(issue["latitude"])}, '
                f'{esc(issue["longitude"])}</small>'
            )

        action = "🔒 View Only"

        if session["role"] == "Authority":

            verify = (
                ""
                if issue["verified"]
                else f"""
                <a class="btn btn-purple"
                   href="/verify/{issue['id']}">
                   🔍 Verify
                </a>
                """
            )

            if issue["status"] == "Reported":
                status_action = f"""
                <a class="btn btn-orange"
                   href="/update/{issue['id']}/In%20Progress">
                   🟡 Start
                </a>
                """

            elif issue["status"] == "In Progress":
                status_action = f"""
                <a class="btn btn-green"
                   href="/update/{issue['id']}/Resolved">
                   ✅ Resolve
                </a>
                """

            else:
                status_action = "✅ Resolved"

            action = verify + status_action

        trs += f"""
        <tr>
            <td>📍 {loc}</td>
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
    <div class="section-title">
        <div>
            <h1>📊 Real-Time Monitoring Dashboard</h1>
            <p style="color:#64748b">
                Monitor assignments, verification, findings and corrective action.
            </p>
        </div>
    </div>

    <h3 style="color:#172554">📋 Assignment Monitoring</h3>

    <div class="stats">
        <div class="stat">
            <div class="num">{assignments_total}</div>
            <small>Total Assignments</small>
        </div>

        <div class="stat">
            <div class="num">{assignments_pending}</div>
            <small>⏳ Pending Inspections</small>
        </div>

        <div class="stat">
            <div class="num">{assignments_verified}</div>
            <small>📷 Camera Verified</small>
        </div>

        <div class="stat">
            <div class="num">{assignments_completed}</div>
            <small>✅ Completed Inspections</small>
        </div>
    </div>

    <h3 style="color:#172554">🚨 Issue Monitoring</h3>

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

                {trs or '<tr><td colspan="8" class="empty">🎉 No inspection issues found.</td></tr>'}
            </table>
        </div>
    </div>
    """

    return page(body, "Dashboard")


# ============================================================
# ISSUE VERIFICATION AND STATUS
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

    locations = conn.execute("""
        SELECT location,COUNT(*) AS reports
        FROM issues
        GROUP BY location
        ORDER BY reports DESC
    """).fetchall()

    workers = conn.execute("""
        SELECT
            u.name,
            u.unique_id,
            COUNT(i.id) AS inspections
        FROM users u
        LEFT JOIN issues i ON u.id=i.reporter_id
        WHERE u.role IN ('Worker','Inspector')
        GROUP BY u.id
        ORDER BY inspections DESC
    """).fetchall()

    conn.close()

    locrows = "".join(
        f"""
        <tr>
            <td>{esc(row["location"])}</td>
            <td>{row["reports"]}</td>
            <td>{badge(priority_for(row["reports"]))}</td>
        </tr>
        """
        for row in locations
    )

    if not locrows:
        locrows = """
        <tr>
            <td colspan="3" class="empty">No data available.</td>
        </tr>
        """

    wrows = "".join(
        f"""
        <tr>
            <td>{esc(row["name"])}</td>
            <td>{esc(row["unique_id"])}</td>
            <td>{row["inspections"]}</td>
        </tr>
        """
        for row in workers
    )

    if not wrows:
        wrows = """
        <tr>
            <td colspan="3" class="empty">No data available.</td>
        </tr>
        """

    body = f"""
    <div class="card">
        <h1>📈 Inspection Analytics</h1>

        <div class="info">
            Repeated findings at the same location automatically
            increase the prototype priority score.
        </div>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Location</th>
                    <th>Reports</th>
                    <th>Priority</th>
                </tr>
                {locrows}
            </table>
        </div>
    </div>

    <div class="card">
        <h2>👷 Inspection Activity</h2>

        <div class="table-wrap">
            <table>
                <tr>
                    <th>Name</th>
                    <th>ID</th>
                    <th>Reports Submitted</th>
                </tr>
                {wrows}
            </table>
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
                Enter both camera location and URL.
            </div>
            """

        else:
            conn.execute(
                """
                INSERT INTO cctv_feeds(
                    location,feed_url,created_at
                )
                VALUES(?,?,?)
                """,
                (location, feed, now())
            )

            conn.commit()

            message = """
            <div class="info success">
                ✅ CCTV feed added successfully.
            </div>
            """

    feeds = conn.execute(
        "SELECT * FROM cctv_feeds ORDER BY id DESC"
    ).fetchall()

    conn.close()

    rows = ""

    for feed in feeds:
        rows += f"""
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

    if not rows:
        rows = """
        <tr>
            <td colspan="3" class="empty">
                No CCTV feeds configured.
            </td>
        </tr>
        """

    body = f"""
    <div class="card">
        <h1>📹 CCTV Monitoring</h1>
        {message}

        <form class="form-grid" method="POST">

            <div class="field">
                <label>Camera Location</label>
                <input name="location" required>
            </div>

            <div class="field">
                <label>Authorized Monitoring URL</label>
                <input type="url" name="feed_url" required>
            </div>

            <div class="full">
                <button class="btn">➕ Add Feed</button>
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
                {rows}
            </table>
        </div>
    </div>
    """

    return page(body, "CCTV")


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
                Enter a meeting title.
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
                INSERT INTO meetings(
                    title,meeting_url,created_at,
                    created_by,meeting_code
                )
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
                🎉 Meeting created successfully!<br>
                Meeting code:
                <span class="meeting-code">{esc(code)}</span><br>
                Workers and Inspectors will see a meeting notification
                when they open the system.
            </div>
            """

    meetings_list = conn.execute("""
        SELECT m.*,u.name AS authority_name
        FROM meetings m
        LEFT JOIN users u ON m.created_by=u.id
        ORDER BY m.id DESC
    """).fetchall()

    conn.close()

    form = ""

    if session["role"] == "Authority":
        form = """
        <div class="card">
            <h1>🎥 Create Team Meeting</h1>
            <p style="color:#64748b">
                Create a meeting room for inspection coordination.
            </p>

            <form method="POST">
                <div class="field">
                    <label>Meeting Title</label>
                    <input name="title"
                           placeholder="Emergency Inspection Review"
                           required>
                </div>

                <button class="btn btn-purple">
                    🔔 Create Meeting
                </button>
            </form>
        </div>
        """

    rows = ""

    for meeting in meetings_list:
        rows += f"""
        <tr>
            <td>{esc(meeting["title"])}</td>
            <td>{esc(meeting["authority_name"] or "Authority")}</td>
            <td>{esc(meeting["created_at"])}</td>
            <td>
                <a class="btn btn-purple"
                   href="{esc(meeting["meeting_url"])}">
                   🎥 Join
                </a>
            </td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="4" class="empty">
                No meetings available.
            </td>
        </tr>
        """

    body = f"""
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
                {rows}
            </table>
        </div>
    </div>
    """

    return page(body, "Meetings")


# ============================================================
# MEETING ROOM
# ============================================================

@app.route("/meeting/<meeting_code>")
def meeting_room(meeting_code):
    if not logged_in():
        return redirect(url_for("login"))

    conn = db()

    meeting = conn.execute("""
        SELECT m.*,u.name AS authority_name
        FROM meetings m
        LEFT JOIN users u ON m.created_by=u.id
        WHERE m.meeting_code=?
    """, (meeting_code,)).fetchone()

    if not meeting:
        conn.close()
        return "Meeting not found", 404

    conn.execute(
        """
        INSERT OR IGNORE INTO meeting_participants(
            meeting_id,user_id,joined_at
        )
        VALUES(?,?,?)
        """,
        (
            meeting["id"],
            session["user_id"],
            now()
        )
    )

    conn.commit()

    participants = conn.execute("""
        SELECT u.name,u.role,p.joined_at
        FROM meeting_participants p
        JOIN users u ON p.user_id=u.id
        WHERE p.meeting_id=?
        ORDER BY p.joined_at
    """, (meeting["id"],)).fetchall()

    conn.close()

    rows = "".join(
        f"""
        <tr>
            <td>{esc(p["name"])}</td>
            <td>{esc(p["role"])}</td>
            <td>🟢 Joined</td>
        </tr>
        """
        for p in participants
    )

    body = f"""
    <div class="card" style="text-align:center">
        <h1>🎥 Smart Inspection Meeting Room</h1>

        <div class="info success">
            🟢 You joined successfully.<br><br>

            Meeting: <b>{esc(meeting["title"])}</b><br>

            Code:
            <span class="meeting-code">
                {esc(meeting_code)}
            </span><br>

            Joined as:
            <b>{esc(session["name"])}</b>
            ({esc(session["role"])})
        </div>

        <p style="color:#64748b">
            Prototype coordination room. A production system can
            integrate a secure video conferencing provider or WebRTC.
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
                {rows}
            </table>
        </div>
    </div>
    """

    return page(body, "Meeting Room")


# ============================================================
# MEETING NOTIFICATION API
# ============================================================

@app.route("/api/latest-meeting")
def latest_meeting():
    if not logged_in():
        return jsonify({"logged_in": False}), 401

    if session.get("role") not in ("Worker", "Inspector"):
        return jsonify({"meeting": None})

    conn = db()

    meeting = conn.execute("""
        SELECT
            m.id,
            m.title,
            m.created_at,
            m.meeting_url,
            u.name AS authority_name
        FROM meetings m
        LEFT JOIN users u ON m.created_by=u.id
        ORDER BY m.id DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    if not meeting:
        return jsonify({"meeting": None})

    return jsonify({
        "meeting": {
            "id": meeting["id"],
            "title": meeting["title"],
            "created_at": meeting["created_at"],
            "meeting_url": meeting["meeting_url"],
            "authority_name":
                meeting["authority_name"] or "Authority"
        }
    })


# ============================================================
# ERROR HANDLER
# ============================================================

@app.errorhandler(413)
def too_large(error):
    return page(
        """
        <div class="card">
            <h1>File too large</h1>
            <p>Please upload an image smaller than 10 MB.</p>
        </div>
        """,
        "Upload Error"
    ), 413


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
