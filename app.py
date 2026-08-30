from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory
)
import sqlite3
import os
import uuid
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = "smart_inspection_system_2026_secure_key"

DATABASE = "inspection.db"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def require_login():
    return "user_id" in session


def calculate_priority(report_count):

    if report_count >= 4:
        return "High"
    elif report_count >= 2:
        return "Medium"
    return "Low"


def priority_badge(priority):

    classes = {
        "Low": "priority-low",
        "Medium": "priority-medium",
        "High": "priority-high"
    }

    icons = {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🔴"
    }

    return f"""
    <span class="badge {classes.get(priority, '')}">
        {icons.get(priority, '⚪')} {priority}
    </span>
    """


# ============================================================
# DATABASE SETUP
# ============================================================

def create_database():

    conn = get_connection()

    # USERS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # ASSIGNMENTS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            inspection_type TEXT DEFAULT 'Routine',
            assigned_at TEXT NOT NULL,
            status TEXT DEFAULT 'Assigned'
        )
    """)

    # ISSUES / REPORTS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
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
        )
    """)

    # CCTV
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cctv_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            feed_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # MEETINGS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            meeting_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # DEFAULT OFFICER
    users = [
        (
            "OFF001",
            "System Officer",
            "officer123",
            "Officer"
        ),
        (
            "INS001",
            "Inspection Officer",
            "inspector123",
            "Inspector"
        ),
        (
            "WORK001",
            "Field Worker",
            "worker123",
            "Worker"
        )
    ]

    for unique_id, name, password, role in users:

        user = conn.execute(
            "SELECT id FROM users WHERE unique_id = ?",
            (unique_id,)
        ).fetchone()

        if user is None:

            conn.execute("""
                INSERT INTO users
                (unique_id, name, password, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                unique_id,
                name,
                generate_password_hash(password),
                role,
                current_time()
            ))

    conn.commit()
    conn.close()


create_database()


# ============================================================
# WEBSITE DESIGN
# ============================================================

STYLE = """
<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f7fb;
    color: #1e293b;
}

.navbar {
    background: linear-gradient(90deg, #0f172a, #1d4ed8);
    color: white;
    padding: 17px 7%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
}

.navbar a {
    color: white;
    text-decoration: none;
    margin-left: 14px;
    font-weight: bold;
}

.container {
    max-width: 1200px;
    margin: auto;
    padding: 30px 20px;
}

.card {
    background: white;
    padding: 28px;
    border-radius: 18px;
    margin-bottom: 25px;
    box-shadow: 0 7px 22px rgba(0,0,0,0.08);
}

.hero {
    text-align: center;
    padding: 75px 25px;
    background: linear-gradient(135deg, #eff6ff, #eef2ff);
}

.hero h1 {
    font-size: 42px;
    color: #1e3a8a;
}

.btn {
    display: inline-block;
    background: #2563eb;
    color: white;
    padding: 12px 18px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    text-decoration: none;
    margin: 4px;
    font-size: 14px;
}

.btn-green {
    background: #059669;
}

.btn-purple {
    background: #7c3aed;
}

.btn-orange {
    background: #ea580c;
}

.btn-red {
    background: #dc2626;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 18px;
}

.feature {
    background: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.06);
}

input, select, textarea {
    width: 100%;
    padding: 12px;
    margin-top: 7px;
    margin-bottom: 16px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 15px;
}

textarea {
    min-height: 100px;
}

h1, h2, h3 {
    color: #1e3a8a;
}

.info {
    background: #eff6ff;
    padding: 15px;
    border-left: 5px solid #2563eb;
    border-radius: 7px;
    margin: 15px 0;
}

.error {
    color: #dc2626;
    font-weight: bold;
}

.badge {
    padding: 6px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
}

.priority-low {
    background: #dcfce7;
    color: #166534;
}

.priority-medium {
    background: #fef3c7;
    color: #92400e;
}

.priority-high {
    background: #fee2e2;
    color: #991b1b;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 18px;
    margin: 20px 0;
}

.stat-card {
    background: white;
    padding: 22px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 5px 18px rgba(0,0,0,0.08);
}

.stat-number {
    font-size: 34px;
    font-weight: bold;
    color: #2563eb;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th {
    background: #1e3a8a;
    color: white;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
}

.evidence-photo {
    width: 100px;
    height: 75px;
    object-fit: cover;
    border-radius: 8px;
}

@media(max-width:700px) {

    .container {
        padding: 15px;
    }

    .card {
        padding: 18px;
    }

    .hero h1 {
        font-size: 29px;
    }
}

</style>
"""


# ============================================================
# NAVBAR
# ============================================================

def navbar():

    if not require_login():
        return ""

    links = """
        <a href="/home">🏠 Home</a>
        <a href="/dashboard">📊 Dashboard</a>
    """

    # Worker and Inspector
    if session["role"] in ["Worker", "Inspector"]:
        links += """
            <a href="/my-assignments">📋 My Assignments</a>
        """

    # Officer
    if session["role"] == "Officer":
        links += """
            <a href="/users">👥 Users</a>
            <a href="/assignments">📌 Assign Inspection</a>
            <a href="/analytics">📈 Analytics</a>
            <a href="/cctv">📹 CCTV</a>
            <a href="/meetings">🎥 Meetings</a>
        """

    links += '<a href="/logout">🚪 Logout</a>'

    return f"""
    <div class="navbar">
        <div>
            <b>🏛️ Smart Monitoring & Inspection</b>
        </div>
        <div>{links}</div>
    </div>
    """


# ============================================================
# LANDING PAGE
# ============================================================

@app.route("/")
def landing():

    return f"""
    {STYLE}

    <div class="navbar">
        <b>🏛️ Smart Monitoring & Inspection System</b>
        <a href="/login">🔐 Login</a>
    </div>

    <div class="hero">

        <h1>Smart Real-Time Monitoring & Inspection System</h1>

        <p style="font-size:18px;">
            A digital platform for field inspection,
            evidence collection and real-time issue monitoring.
        </p>

        <a class="btn" href="/login">
            🔐 Login to System
        </a>

    </div>

    <div class="container">

        <div class="grid">

            <div class="feature">
                <h3>👷 Field Inspection</h3>
                <p>
                    Workers and Inspectors conduct inspections
                    directly from assigned locations.
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

        </div>

    </div>
    """


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if require_login():
        return redirect(url_for("home"))

    error = ""

    if request.method == "POST":

        unique_id = request.form["unique_id"].strip().upper()
        password = request.form["password"]

        conn = get_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE unique_id = ?",
            (unique_id,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        error = "❌ Invalid Unique ID or Password."

    return f"""
    {STYLE}

    <div class="container">

        <div class="card"
             style="max-width:500px; margin:60px auto;">

            <h1 style="text-align:center;">
                🔐 System Login
            </h1>

            <form method="POST">

                <label>🆔 Unique ID</label>
                <input type="text"
                       name="unique_id"
                       placeholder="Enter your ID"
                       required>

                <label>🔑 Password</label>
                <input type="password"
                       name="password"
                       placeholder="Enter your password"
                       required>

                <button class="btn"
                        style="width:100%;"
                        type="submit">
                    Login
                </button>

            </form>

            <p class="error">{error}</p>

            <a href="/">← Back to Home</a>

        </div>

    </div>
    """


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()
    return redirect(url_for("landing"))


# ============================================================
# HOME
# ============================================================

@app.route("/home")
def home():

    if not require_login():
        return redirect(url_for("login"))

    role = session["role"]

    buttons = ""

    if role in ["Worker", "Inspector"]:

        buttons += """
        <a class="btn btn-green"
           href="/my-assignments">
            📋 View My Assignments
        </a>
        """

    if role == "Officer":

        buttons += """
        <a class="btn btn-purple" href="/users">
            👥 Manage Users
        </a>

        <a class="btn btn-orange" href="/assignments">
            📌 Assign Inspection
        </a>

        <a class="btn btn-green" href="/analytics">
            📈 View Analytics
        </a>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card" style="text-align:center;">

            <h1>
                Welcome, {session["name"]}! 👋
            </h1>

            <p>
                Your Role:
                <span class="badge">
                    {role}
                </span>
            </p>

            <div class="info">
                🔐 Features are available based on your authorized role.
            </div>

            {buttons}

            <a class="btn" href="/dashboard">
                📊 Dashboard
            </a>

        </div>

        <div class="card">

            <h2>🎯 System Workflow</h2>

            <p style="font-size:17px; line-height:2;">

                👨‍💼 Officer Assigns
                →
                👷 Worker / 🔍 Inspector Conducts Inspection
                →
                📸 Evidence & GPS
                →
                📤 Report Submission
                →
                👨‍💼 Officer Verification
                →
                ✅ Issue Resolution

            </p>

        </div>

    </div>
    """


# ============================================================
# USER MANAGEMENT - OFFICER
# ============================================================

@app.route("/users", methods=["GET", "POST"])
def users():

    if not require_login() or session["role"] != "Officer":
        return "⛔ Access Denied.", 403

    message = ""

    if request.method == "POST":

        name = request.form["name"].strip()
        password = request.form["password"]
        role = request.form["role"]

        prefixes = {
            "Officer": "OFF",
            "Inspector": "INS",
            "Worker": "WORK"
        }

        unique_id = (
            prefixes[role]
            + uuid.uuid4().hex[:6].upper()
        )

        conn = get_connection()

        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            unique_id,
            name,
            generate_password_hash(password),
            role,
            current_time()
        ))

        conn.commit()
        conn.close()

        message = f"""
        <div class="info">
            ✅ User Created Successfully!<br><br>
            🆔 ID: <b>{unique_id}</b><br>
            👤 Name: <b>{name}</b><br>
            🏷️ Role: <b>{role}</b>
        </div>
        """

    conn = get_connection()

    all_users = conn.execute("""
        SELECT unique_id, name, role
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for user in all_users:

        rows += f"""
        <tr>
            <td>{user["unique_id"]}</td>
            <td>{user["name"]}</td>
            <td>{user["role"]}</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>👥 User Management</h1>

            {message}

            <form method="POST">

                <label>Full Name</label>
                <input name="name" required>

                <label>Password</label>
                <input type="password"
                       name="password"
                       required>

                <label>Role</label>

                <select name="role">
                    <option value="Worker">
                        👷 Worker
                    </option>

                    <option value="Inspector">
                        🔍 Inspector
                    </option>

                    <option value="Officer">
                        👨‍💼 Officer
                    </option>
                </select>

                <button class="btn btn-purple">
                    ➕ Create User
                </button>

            </form>

        </div>

        <div class="card">

            <h2>👥 Registered Users</h2>

            <div style="overflow-x:auto;">

                <table>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Role</th>
                    </tr>
                    {rows}
                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# OFFICER - ASSIGN INSPECTION
# ============================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not require_login() or session["role"] != "Officer":
        return "⛔ Access Denied.", 403

    conn = get_connection()

    workers = conn.execute("""
        SELECT id, name, unique_id, role
        FROM users
        WHERE role IN ('Worker', 'Inspector')
    """).fetchall()

    message = ""

    if request.method == "POST":

        location = request.form["location"].strip()
        inspection_type = request.form["inspection_type"]

        assigned_user_id = request.form.get("user_id")

        if assigned_user_id == "random":

            selected = random.choice(workers)

        else:

            selected = conn.execute("""
                SELECT id, name, unique_id, role
                FROM users
                WHERE id = ?
            """, (assigned_user_id,)).fetchone()

        if selected:

            conn.execute("""
                INSERT INTO assignments
                (user_id, location, inspection_type,
                 assigned_at, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                selected["id"],
                location,
                inspection_type,
                current_time(),
                "Assigned"
            ))

            conn.commit()

            message = f"""
            <div class="info">

                ✅ <b>Inspection Assigned Successfully!</b>
                <br><br>

                📍 Location: <b>{location}</b><br>
                🔍 Type: <b>{inspection_type}</b><br>
                👤 Assigned To: <b>{selected["name"]}</b><br>
                🏷️ Role: <b>{selected["role"]}</b>

            </div>
            """

    assignment_list = conn.execute("""
        SELECT assignments.*, users.name,
               users.unique_id, users.role
        FROM assignments
        JOIN users ON assignments.user_id = users.id
        ORDER BY assignments.id DESC
    """).fetchall()

    conn.close()

    user_options = """
    <option value="random">
        🎲 Random Assignment
    </option>
    """

    for worker in workers:

        user_options += f"""
        <option value="{worker['id']}">
            {worker['name']} -
            {worker['role']}
        </option>
        """

    rows = ""

    for item in assignment_list:

        rows += f"""
        <tr>
            <td>{item["location"]}</td>
            <td>{item["inspection_type"]}</td>
            <td>{item["name"]}</td>
            <td>{item["role"]}</td>
            <td>{item["assigned_at"]}</td>
            <td>{item["status"]}</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📌 Assign Field Inspection</h1>

            <p>
                Assign routine inspections to Workers or
                detailed inspections to Inspectors.
            </p>

            {message}

            <form method="POST">

                <label>📍 Location to Inspect</label>
                <input name="location" required>

                <label>🔍 Inspection Type</label>

                <select name="inspection_type">
                    <option value="Routine">
                        Routine Inspection
                    </option>

                    <option value="Detailed">
                        Detailed Inspection
                    </option>

                    <option value="Follow-up">
                        Follow-up Inspection
                    </option>
                </select>

                <label>👤 Assign To</label>

                <select name="user_id">
                    {user_options}
                </select>

                <button class="btn btn-purple">
                    📌 Assign Inspection
                </button>

            </form>

        </div>

        <div class="card">

            <h2>📋 Assignment History</h2>

            <div style="overflow-x:auto;">

                <table>
                    <tr>
                        <th>Location</th>
                        <th>Type</th>
                        <th>Assigned To</th>
                        <th>Role</th>
                        <th>Time</th>
                        <th>Status</th>
                    </tr>
                    {rows}
                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# WORKER / INSPECTOR - MY ASSIGNMENTS
# ============================================================

@app.route("/my-assignments")
def my_assignments():

    if not require_login():
        return redirect(url_for("login"))

    if session["role"] not in ["Worker", "Inspector"]:
        return "⛔ Access Denied.", 403

    conn = get_connection()

    assignment_list = conn.execute("""
        SELECT *
        FROM assignments
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    rows = ""

    for assignment in assignment_list:

        if assignment["status"] == "Completed":

            action = "✅ Completed"

        else:

            action = f"""
            <a class="btn btn-green"
               href="/inspection/{assignment['id']}">
                🔍 Conduct Inspection
            </a>
            """

        rows += f"""
        <tr>
            <td>📍 {assignment["location"]}</td>
            <td>{assignment["inspection_type"]}</td>
            <td>{assignment["assigned_at"]}</td>
            <td>{assignment["status"]}</td>
            <td>{action}</td>
        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="5"
                style="text-align:center;">
                📭 No assignments available.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📋 My Inspection Assignments</h1>

            <div class="info">
                👷 Complete your assigned field inspection and
                submit evidence directly through the system.
            </div>

            <div style="overflow-x:auto;">

                <table>

                    <tr>
                        <th>Location</th>
                        <th>Type</th>
                        <th>Assigned Time</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>

                    {rows}

                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# WORKER / INSPECTOR - CONDUCT INSPECTION
# ============================================================

@app.route("/inspection/<int:assignment_id>",
           methods=["GET", "POST"])
def inspection(assignment_id):

    if not require_login():
        return redirect(url_for("login"))

    if session["role"] not in ["Worker", "Inspector"]:
        return "⛔ Access Denied.", 403

    conn = get_connection()

    assignment = conn.execute("""
        SELECT *
        FROM assignments
        WHERE id = ?
        AND user_id = ?
        AND status = 'Assigned'
    """, (
        assignment_id,
        session["user_id"]
    )).fetchone()

    if assignment is None:

        conn.close()

        return """
        ⛔ Inspection access denied.
        A valid assigned inspection is required.
        """, 403

    if request.method == "POST":

        location = assignment["location"]

        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]

        description = request.form["description"].strip()

        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")

        # PHOTO UPLOAD
        photo_name = None
        photo = request.files.get("photo")

        if (
            photo
            and photo.filename
            and allowed_file(photo.filename)
        ):

            extension = photo.filename.rsplit(
                ".", 1
            )[1].lower()

            photo_name = (
                uuid.uuid4().hex
                + "."
                + extension
            )

            photo.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    photo_name
                )
            )

        # DETECT ISSUES
        detected_issues = []

        if cleanliness == "No":
            detected_issues.append("Cleanliness")

        if safety == "No":
            detected_issues.append("Safety")

        if facilities == "No":
            detected_issues.append("Facilities")

        # SAVE EACH ISSUE
        for issue_type in detected_issues:

            previous_count = conn.execute("""
                SELECT COUNT(*) AS count
                FROM issues
                WHERE LOWER(location) = LOWER(?)
            """, (location,)).fetchone()["count"]

            priority = calculate_priority(
                previous_count + 1
            )

            conn.execute("""
                INSERT INTO issues (
                    assignment_id,
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assignment_id,
                location,
                issue_type,
                description,
                current_time(),
                "Reported",
                priority,
                photo_name,
                session["user_id"],
                latitude,
                longitude,
                0
            ))

        # COMPLETE ASSIGNMENT
        conn.execute("""
            UPDATE assignments
            SET status = 'Completed'
            WHERE id = ?
        """, (assignment_id,))

        conn.commit()
        conn.close()

        if detected_issues:

            result = (
                "⚠️ Issues Reported: "
                + ", ".join(detected_issues)
            )

        else:

            result = """
            ✅ Inspection completed successfully.
            No issues found!
            """

        return f"""
        {STYLE}
        {navbar()}

        <div class="container">

            <div class="card"
                 style="text-align:center;">

                <h1>✅ Inspection Submitted!</h1>

                <div class="info">

                    📍 Location:
                    <b>{location}</b>

                    <br><br>

                    {result}

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

    conn.close()

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>🔍 Conduct Field Inspection</h1>

            <div class="info">

                📍 Assigned Location:
                <b>{assignment["location"]}</b>
                <br><br>

                🔍 Inspection Type:
                <b>{assignment["inspection_type"]}</b>
                <br><br>

                👤 Conducted By:
                <b>{session["name"]}</b>

            </div>

            <form method="POST"
                  enctype="multipart/form-data">

                <label>
                    🧹 Is the area clean?
                </label>

                <select name="cleanliness">
                    <option value="Yes">
                        Yes ✅
                    </option>
                    <option value="No">
                        No ❌ - Issue Found
                    </option>
                </select>

                <label>
                    🛡️ Is the area safe?
                </label>

                <select name="safety">
                    <option value="Yes">
                        Yes ✅
                    </option>
                    <option value="No">
                        No ❌ - Issue Found
                    </option>
                </select>

                <label>
                    🏢 Are facilities working properly?
                </label>

                <select name="facilities">
                    <option value="Yes">
                        Yes ✅
                    </option>
                    <option value="No">
                        No ❌ - Issue Found
                    </option>
                </select>

                <label>
                    📸 Upload Photo Evidence
                </label>

                <input type="file"
                       name="photo"
                       accept="image/*">

                <label>
                    📍 GPS Coordinates
                </label>

                <input id="latitude"
                       name="latitude"
                       placeholder="Latitude">

                <input id="longitude"
                       name="longitude"
                       placeholder="Longitude">

                <button type="button"
                        class="btn btn-purple"
                        onclick="getLocation()">

                    📍 Get My Current Location

                </button>

                <label>
                    📝 Observation / Description
                </label>

                <textarea name="description"
                    placeholder="Describe issues or observations...">
                </textarea>

                <button class="btn"
                        type="submit">

                    📤 Submit Inspection Report

                </button>

            </form>

        </div>

    </div>

    <script>

    function getLocation() {{

        if (navigator.geolocation) {{

            navigator.geolocation.getCurrentPosition(

                function(position) {{

                    document.getElementById("latitude").value =
                        position.coords.latitude;

                    document.getElementById("longitude").value =
                        position.coords.longitude;

                }},

                function() {{

                    alert(
                        "Unable to get location. "
                        + "Please allow location permission."
                    );

                }}
            );

        }} else {{

            alert(
                "Geolocation is not supported "
                + "by this browser."
            );
        }}
    }}

    </script>
    """


# ============================================================
# SERVE UPLOADED PHOTOS
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not require_login():
        return redirect(url_for("login"))

    conn = get_connection()

    # OFFICER CAN SEE ALL REPORTS
    if session["role"] == "Officer":

        issues = conn.execute("""
            SELECT issues.*,
                   users.name AS reporter_name
            FROM issues
            LEFT JOIN users
            ON issues.reporter_id = users.id
            ORDER BY issues.id DESC
        """).fetchall()

    # WORKER / INSPECTOR SEE OWN REPORTS
    else:

        issues = conn.execute("""
            SELECT issues.*,
                   users.name AS reporter_name
            FROM issues
            LEFT JOIN users
            ON issues.reporter_id = users.id
            WHERE issues.reporter_id = ?
            ORDER BY issues.id DESC
        """, (
            session["user_id"],
        )).fetchall()

    conn.close()

    total = len(issues)

    reported = sum(
        1 for issue in issues
        if issue["status"] == "Reported"
    )

    progress = sum(
        1 for issue in issues
        if issue["status"] == "In Progress"
    )

    resolved = sum(
        1 for issue in issues
        if issue["status"] == "Resolved"
    )

    high = sum(
        1 for issue in issues
        if issue["priority"] == "High"
    )

    rows = ""

    for issue in issues:

        photo_html = "No Photo"

        if issue["photo"]:

            filename = issue["photo"]

            photo_html = f"""
            <a href="/uploads/{filename}"
               target="_blank">

                <img class="evidence-photo"
                     src="/uploads/{filename}"
                     alt="Evidence">

            </a>
            """

        location_html = f"""
        📍 {issue["location"]}
        """

        if issue["latitude"] and issue["longitude"]:

            location_html += f"""
            <br>
            <small>
                {issue["latitude"]},
                {issue["longitude"]}
            </small>
            """

        if session["role"] == "Officer":

            # VERIFY ACTION
            if issue["verified"] == 0:

                verify_action = f"""
                <a class="btn btn-purple"
                   href="/verify/{issue['id']}">
                    🔍 Verify
                </a>
                """

            else:

                verify_action = "✅ Verified"

            # STATUS ACTION
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

            action = (
                verify_action
                + "<br>"
                + status_action
            )

        else:

            action = "🔒 View Only"

        rows += f"""
        <tr>

            <td>{location_html}</td>
            <td>{issue["issue_type"]}</td>
            <td>{issue["description"] or "-"}</td>
            <td>{priority_badge(issue["priority"])}</td>
            <td>{photo_html}</td>
            <td>{issue["status"]}</td>
            <td>{issue["created_at"]}</td>
            <td>{action}</td>

        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="8"
                style="text-align:center;">
                🎉 No inspection issues found.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <h1>📊 Real-Time Monitoring Dashboard</h1>

        <div class="dashboard-grid">

            <div class="stat-card">
                <div class="stat-number">{total}</div>
                <p>Total Issues</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{reported}</div>
                <p>🔴 Reported</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{progress}</div>
                <p>🟡 In Progress</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{resolved}</div>
                <p>🟢 Resolved</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{high}</div>
                <p>🔴 High Priority</p>
            </div>

        </div>

        <div class="card">

            <h2>🚨 Inspection Reports</h2>

            <div style="overflow-x:auto;">

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

                    {rows}

                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# OFFICER - VERIFY ISSUE
# ============================================================

@app.route("/verify/<int:issue_id>")
def verify_issue(issue_id):

    if (
        not require_login()
        or session["role"] != "Officer"
    ):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    conn.execute("""
        UPDATE issues
        SET verified = 1
        WHERE id = ?
    """, (issue_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ============================================================
# OFFICER - UPDATE ISSUE STATUS
# ============================================================

@app.route("/update/<int:issue_id>/<status>")
def update_status(issue_id, status):

    if (
        not require_login()
        or session["role"] != "Officer"
    ):
        return "⛔ Access Denied.", 403

    allowed_statuses = [
        "Reported",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:
        return "❌ Invalid Status."

    conn = get_connection()

    conn.execute("""
        UPDATE issues
        SET status = ?
        WHERE id = ?
    """, (
        status,
        issue_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ============================================================
# ANALYTICS - OFFICER
# ============================================================

@app.route("/analytics")
def analytics():

    if (
        not require_login()
        or session["role"] != "Officer"
    ):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    locations = conn.execute("""
        SELECT location,
               COUNT(*) AS reports
        FROM issues
        GROUP BY location
        ORDER BY reports DESC
    """).fetchall()

    inspectors = conn.execute("""
        SELECT
            users.name,
            users.unique_id,
            users.role,
            COUNT(assignments.id) AS inspections
        FROM users
        LEFT JOIN assignments
        ON users.id = assignments.user_id
        WHERE users.role IN ('Worker', 'Inspector')
        GROUP BY users.id
        ORDER BY inspections DESC
    """).fetchall()

    conn.close()

    location_rows = ""

    for item in locations:

        priority = calculate_priority(
            item["reports"]
        )

        location_rows += f"""
        <tr>
            <td>{item["location"]}</td>
            <td>{item["reports"]}</td>
            <td>{priority_badge(priority)}</td>
        </tr>
        """

    worker_rows = ""

    for worker in inspectors:

        worker_rows += f"""
        <tr>
            <td>{worker["name"]}</td>
            <td>{worker["unique_id"]}</td>
            <td>{worker["role"]}</td>
            <td>{worker["inspections"]}</td>
        </tr>
        """

    if not location_rows:

        location_rows = """
        <tr>
            <td colspan="3">
                No data available.
            </td>
        </tr>
        """

    if not worker_rows:

        worker_rows = """
        <tr>
            <td colspan="4">
                No inspection activity available.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📈 Inspection Analytics</h1>

            <div class="info">

                🤖 Locations with repeated problems
                automatically receive increased priority.

            </div>

            <h2>🚨 Repeat Problem Locations</h2>

            <table>

                <tr>
                    <th>Location</th>
                    <th>Reports</th>
                    <th>Priority</th>
                </tr>

                {location_rows}

            </table>

        </div>

        <div class="card">

            <h2>👷 Inspection Activity</h2>

            <table>

                <tr>
                    <th>Name</th>
                    <th>ID</th>
                    <th>Role</th>
                    <th>Assigned Inspections</th>
                </tr>

                {worker_rows}

            </table>

        </div>

    </div>
    """


# ============================================================
# CCTV MONITORING - OFFICER
# ============================================================

@app.route("/cctv", methods=["GET", "POST"])
def cctv():

    if (
        not require_login()
        or session["role"] != "Officer"
    ):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    if request.method == "POST":

        location = request.form["location"].strip()
        feed_url = request.form["feed_url"].strip()

        conn.execute("""
            INSERT INTO cctv_feeds
            (location, feed_url, created_at)
            VALUES (?, ?, ?)
        """, (
            location,
            feed_url,
            current_time()
        ))

        conn.commit()

    feeds = conn.execute("""
        SELECT *
        FROM cctv_feeds
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for feed in feeds:

        rows += f"""
        <tr>
            <td>{feed["location"]}</td>
            <td>
                <a class="btn"
                   href="{feed["feed_url"]}"
                   target="_blank">
                    📹 Open Feed
                </a>
            </td>
        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="2">
                No feeds added yet.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📹 CCTV Monitoring</h1>

            <form method="POST">

                <label>Camera Location</label>
                <input name="location" required>

                <label>Authorized Monitoring URL</label>
                <input type="url"
                       name="feed_url"
                       required>

                <button class="btn">
                    ➕ Add Feed
                </button>

            </form>

        </div>

        <div class="card">

            <table>

                <tr>
                    <th>Location</th>
                    <th>Feed</th>
                </tr>

                {rows}

            </table>

        </div>

    </div>
    """


# ============================================================
# VIDEO MEETINGS - OFFICER
# ============================================================

@app.route("/meetings", methods=["GET", "POST"])
def meetings():

    if (
        not require_login()
        or session["role"] != "Officer"
    ):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    if request.method == "POST":

        title = request.form["title"].strip()
        meeting_url = request.form["meeting_url"].strip()

        conn.execute("""
            INSERT INTO meetings
            (title, meeting_url, created_at)
            VALUES (?, ?, ?)
        """, (
            title,
            meeting_url,
            current_time()
        ))

        conn.commit()

    meeting_list = conn.execute("""
        SELECT *
        FROM meetings
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for meeting in meeting_list:

        rows += f"""
        <tr>
            <td>{meeting["title"]}</td>
            <td>{meeting["created_at"]}</td>
            <td>
                <a class="btn btn-purple"
                   href="{meeting["meeting_url"]}"
                   target="_blank">
                    🎥 Join Meeting
                </a>
            </td>
        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="3">
                No meetings available.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>🎥 Video Conference Coordination</h1>

            <form method="POST">

                <label>Meeting Title</label>
                <input name="title" required>

                <label>Meeting URL</label>
                <input type="url"
                       name="meeting_url"
                       required>

                <button class="btn btn-purple">
                    ➕ Add Meeting
                </button>

            </form>

        </div>

        <div class="card">

            <h2>🎥 Available Meetings</h2>

            <table>

                <tr>
                    <th>Meeting</th>
                    <th>Created</th>
                    <th>Join</th>
                </tr>

                {rows}

            </table>

        </div>

    </div>
    """


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print(" Smart Monitoring & Inspection System Starting...")
    print(" Open: http://127.0.0.1:5000")
    print("=" * 60)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
