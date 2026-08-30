from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory, jsonify
)

import sqlite3
import os
import uuid
import random
import html
from datetime import datetime
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


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
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def calculate_priority(report_count):
    """
    Priority Rules:
    1 report       -> Low
    2 or 3 reports -> Medium
    More than 3    -> High
    """

    if report_count > 3:
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


def require_login():
    return "user_id" in session


def role_required(*roles):
    return (
        require_login()
        and session.get("role") in roles
    )


# ============================================================
# DATABASE SETUP
# ============================================================

def create_database():

    conn = get_connection()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ASSIGNMENTS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            status TEXT DEFAULT 'Assigned'
        )
    """)

    # --------------------------------------------------------
    # ISSUES / INSPECTION REPORTS
    # --------------------------------------------------------

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
            longitude TEXT
        )
    """)

    # --------------------------------------------------------
    # CCTV
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cctv_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            feed_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # MEETINGS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            meeting_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by INTEGER,
            meeting_code TEXT UNIQUE
        )
    """)

    # --------------------------------------------------------
    # MEETING PARTICIPANTS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meeting_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            UNIQUE(meeting_id, user_id)
        )
    """)

    # ========================================================
    # DEFAULT USERS
    # ========================================================

    default_users = [
        (
            "ADMIN001",
            "System Authority",
            "admin123",
            "Authority"
        ),
        (
            "INS001",
            "Inspection Officer",
            "inspector123",
            "Inspector"
        ),
        (
            "WORK001",
            "Demo Field Worker",
            "worker123",
            "Worker"
        )
    ]

    for unique_id, name, password, role in default_users:

        existing = conn.execute("""
            SELECT id FROM users
            WHERE unique_id = ?
        """, (unique_id,)).fetchone()

        if existing is None:

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
# WEBSITE STYLE
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
    background: linear-gradient(90deg, #172033, #3159b7);
    color: white;
    padding: 17px 7%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
}

.brand {
    font-size: 19px;
}

.nav-links {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}

.navbar a {
    color: white;
    text-decoration: none;
    padding: 8px;
    font-weight: bold;
    font-size: 14px;
}

.navbar a:hover {
    background: rgba(255,255,255,0.12);
    border-radius: 7px;
}

.container {
    max-width: 1250px;
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
    padding: 85px 25px;
    background:
        linear-gradient(
            135deg,
            #edf3ff,
            #e9eef9
        );
}

.hero h1 {
    font-size: 48px;
    color: #243f78;
    margin-bottom: 20px;
}

.hero p {
    font-size: 18px;
    line-height: 1.6;
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
    font-weight: bold;
}

.btn:hover {
    opacity: 0.9;
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
    grid-template-columns:
        repeat(auto-fit, minmax(230px, 1fr));
    gap: 18px;
}

.feature {
    background: white;
    padding: 25px;
    border-radius: 16px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
}

.feature h3 {
    color: #29467e;
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
    min-height: 110px;
    resize: vertical;
}

h1, h2, h3 {
    color: #1e3a8a;
}

.info {
    background: #eff6ff;
    padding: 16px;
    border-left: 5px solid #2563eb;
    border-radius: 8px;
    margin: 15px 0;
    line-height: 1.6;
}

.notification {
    background: #fff7ed;
    padding: 20px;
    border-left: 5px solid #ea580c;
    border-radius: 10px;
    margin-bottom: 20px;
}

.error {
    color: #dc2626;
    font-weight: bold;
}

.success {
    color: #047857;
    font-weight: bold;
}

.badge {
    padding: 6px 11px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    background: #e0e7ff;
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
    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));
    gap: 18px;
    margin: 20px 0;
}

.stat-card {
    background: white;
    padding: 24px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 5px 18px rgba(0,0,0,0.08);
}

.stat-number {
    font-size: 35px;
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
    width: 110px;
    height: 80px;
    object-fit: cover;
    border-radius: 8px;
}

.high-alert {
    background: #fff1f2;
    border-left: 5px solid #dc2626;
    padding: 18px;
    border-radius: 10px;
    margin-bottom: 20px;
}

@media(max-width:700px) {

    .container {
        padding: 15px;
    }

    .card {
        padding: 18px;
    }

    .hero h1 {
        font-size: 31px;
    }

    table {
        font-size: 13px;
    }
}

</style>
"""


# ============================================================
# 🔔 MEETING NOTIFICATION SCRIPT
# ============================================================

def notification_script():

    if not require_login():
        return ""

    # Authority creates meetings, so notification is for
    # Workers and Inspectors only
    if session.get("role") not in ["Worker", "Inspector"]:
        return ""

    return """
    <script>

    let lastMeetingId =
        localStorage.getItem("smartInspectionLastMeeting");

    // Ask browser notification permission
    if (
        "Notification" in window &&
        Notification.permission === "default"
    ) {
        Notification.requestPermission();
    }


    function checkForNewMeeting() {

        fetch("/api/latest-meeting")

        .then(response => response.json())

        .then(data => {

            if (!data.meeting) {
                return;
            }

            const meeting = data.meeting;
            const meetingId = String(meeting.id);


            // First visit:
            // Store the current meeting as reference
            if (lastMeetingId === null) {

                localStorage.setItem(
                    "smartInspectionLastMeeting",
                    meetingId
                );

                lastMeetingId = meetingId;
                return;
            }


            // A new meeting was created
            if (meetingId !== lastMeetingId) {

                // Website popup
                alert(
                    "🔔 NEW TEAM MEETING!\\n\\n" +
                    "👤 Created by: " +
                    meeting.authority_name +
                    "\\n\\n🎥 Meeting: " +
                    meeting.title +
                    "\\n\\nPlease attend the meeting!"
                );


                // Browser notification
                if (
                    "Notification" in window &&
                    Notification.permission === "granted"
                ) {

                    const notification =
                        new Notification(
                            "🔔 New Inspection Meeting",
                            {
                                body:
                                    meeting.authority_name +
                                    " created: " +
                                    meeting.title
                            }
                        );

                    notification.onclick = function() {
                        window.focus();
                        window.location.href =
                            meeting.meeting_url;
                    };
                }


                localStorage.setItem(
                    "smartInspectionLastMeeting",
                    meetingId
                );

                lastMeetingId = meetingId;
            }

        })

        .catch(error => {
            console.log(
                "Notification error:",
                error
            );
        });
    }


    // Check every 3 seconds
    setInterval(checkForNewMeeting, 3000);

    </script>
    """


# ============================================================
# NAVBAR - ROLE BASED
# ============================================================

def navbar():

    if not require_login():
        return ""

    role = session.get("role")

    links = """
        <a href="/home">🏠 Home</a>
    """

    # Authority links
    if role == "Authority":

        links += """
            <a href="/dashboard">📊 Dashboard</a>
            <a href="/users">👥 Users</a>
            <a href="/assignments">🎲 Assign</a>
            <a href="/analytics">📈 Analytics</a>
            <a href="/cctv">📹 CCTV</a>
        """

    # Worker and Inspector links
    elif role in ["Worker", "Inspector"]:

        links += """
            <a href="/my-assignments">
                📋 My Assignments
            </a>

            <a href="/dashboard">
                📊 My Reports
            </a>
        """

    links += """
        <a href="/meetings">🎥 Meetings</a>
        <a href="/logout">🚪 Logout</a>
    """

    return f"""
    <div class="navbar">

        <div class="brand">
            🏛️ <b>Smart Monitoring & Inspection System</b>
        </div>

        <div class="nav-links">
            {links}
        </div>

    </div>

    {notification_script()}
    """


# ============================================================
# LANDING PAGE
# ============================================================

@app.route("/")
def landing():

    return f"""
    {STYLE}

    <div class="navbar">

        <div class="brand">
            🏛️ <b>Smart Monitoring & Inspection System</b>
        </div>

        <a href="/login">🔐 Login</a>

    </div>


    <div class="hero">

        <h1>
            Smart Real-Time Monitoring & Inspection System
        </h1>

        <p>
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
                    Workers and Inspectors conduct
                    inspections at assigned locations.
                </p>
            </div>

            <div class="feature">
                <h3>📸 Evidence Capture</h3>
                <p>
                    Upload photographic evidence
                    with inspection reports.
                </p>
            </div>

            <div class="feature">
                <h3>📍 GPS Location</h3>
                <p>
                    Capture field location details
                    during inspections.
                </p>
            </div>

            <div class="feature">
                <h3>🚨 Smart Priority</h3>
                <p>
                    Repeated problems automatically
                    receive higher priority.
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

        unique_id = request.form[
            "unique_id"
        ].strip().upper()

        password = request.form["password"]

        conn = get_connection()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE unique_id = ?
        """, (unique_id,)).fetchone()

        conn.close()

        if (
            user
            and check_password_hash(
                user["password"],
                password
            )
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
             style="max-width:500px; margin:70px auto;">

            <h1 style="text-align:center;">
                🔐 System Login
            </h1>

            <form method="POST">

                <label>🆔 Unique ID</label>
                <input
                    type="text"
                    name="unique_id"
                    required
                >

                <label>🔑 Password</label>
                <input
                    type="password"
                    name="password"
                    required
                >

                <button
                    class="btn"
                    style="width:100%;"
                    type="submit"
                >
                    Login
                </button>

            </form>

            <p class="error">{error}</p>

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

    # --------------------------------------------------------
    # AUTHORITY HOME
    # --------------------------------------------------------

    if role == "Authority":

        buttons = """
            <a class="btn" href="/dashboard">
                📊 Monitoring Dashboard
            </a>

            <a class="btn btn-purple" href="/users">
                👥 Manage Users
            </a>

            <a class="btn btn-orange" href="/assignments">
                🎲 Assign Inspection
            </a>

            <a class="btn btn-green" href="/analytics">
                📈 Analytics
            </a>
        """

        work = """
            👑 Manage the inspection system, monitor all
            reports, assign field inspections and coordinate
            the inspection team.
        """

    # --------------------------------------------------------
    # WORKER / INSPECTOR HOME
    # --------------------------------------------------------

    else:

        buttons = """
            <a class="btn btn-green"
               href="/my-assignments">
                📋 My Assignments
            </a>

            <a class="btn btn-purple"
               href="/meetings">
                🎥 Team Meetings
            </a>
        """

        work = """
            👷 Complete your assigned inspections,
            collect evidence and submit reports.
            You can only access your own work.
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card" style="text-align:center;">

            <h1>
                Welcome, {html.escape(session["name"])}! 👋
            </h1>

            <p>
                Role:
                <span class="badge">
                    {role}
                </span>
            </p>

            <div class="info">
                {work}
            </div>

            {buttons}

        </div>


        <div class="card">

            <h2>🎯 Smart Inspection Workflow</h2>

            <p style="font-size:17px; line-height:2;">

                👑 Authority Assigns Inspection →
                👷 Worker/Inspector Receives Assignment →
                🔍 Field Inspection →
                📸 Evidence Collection →
                📤 Report Submission →
                🤖 Smart Priority Detection →
                📊 Authority Monitoring →
                🎥 Team Coordination →
                ✅ Resolution

            </p>

        </div>

    </div>
    """


# ============================================================
# USER MANAGEMENT - AUTHORITY ONLY
# ============================================================

@app.route("/users", methods=["GET", "POST"])
def users():

    if not role_required("Authority"):
        return "⛔ Access Denied.", 403

    message = ""

    if request.method == "POST":

        name = request.form["name"].strip()
        password = request.form["password"]
        role = request.form["role"]

        prefixes = {
            "Authority": "AUTH",
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

            ✅ <b>User Created Successfully!</b>

            <br><br>
            🆔 ID: <b>{unique_id}</b><br>
            👤 Name: <b>{html.escape(name)}</b><br>
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
            <td>{html.escape(user["name"])}</td>
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
                <input
                    type="password"
                    name="password"
                    required
                >

                <label>Role</label>

                <select name="role">

                    <option value="Worker">
                        Worker
                    </option>

                    <option value="Inspector">
                        Inspector
                    </option>

                    <option value="Authority">
                        Authority
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
# RANDOM INSPECTION ASSIGNMENT - AUTHORITY ONLY
# ============================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not role_required("Authority"):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    staff = conn.execute("""
        SELECT id, name, unique_id, role
        FROM users
        WHERE role IN ('Worker', 'Inspector')
    """).fetchall()

    message = ""

    if request.method == "POST":

        location = request.form[
            "location"
        ].strip()

        if not staff:

            message = """
            <p class="error">
                ❌ No Workers or Inspectors available.
            </p>
            """

        else:

            # RANDOM STAFF SELECTION
            selected = random.choice(staff)

            conn.execute("""
                INSERT INTO assignments
                (user_id, location, assigned_at, status)
                VALUES (?, ?, ?, ?)
            """, (
                selected["id"],
                location,
                current_time(),
                "Assigned"
            ))

            conn.commit()

            message = f"""
            <div class="info">

                🎲 <b>Inspection Randomly Assigned!</b>

                <br><br>

                📍 Location:
                <b>{html.escape(location)}</b><br>

                👤 Assigned To:
                <b>{html.escape(selected["name"])}</b><br>

                🏷️ Role:
                <b>{selected["role"]}</b><br>

                🆔 ID:
                <b>{selected["unique_id"]}</b>

            </div>
            """

    assignment_list = conn.execute("""
        SELECT
            assignments.*,
            users.name,
            users.unique_id,
            users.role
        FROM assignments
        JOIN users
        ON assignments.user_id = users.id
        ORDER BY assignments.id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for item in assignment_list:

        rows += f"""
        <tr>
            <td>📍 {html.escape(item["location"])}</td>
            <td>{html.escape(item["name"])}</td>
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

            <h1>🎲 Random Inspection Assignment</h1>

            <div class="info">

                The system randomly selects an available
                Worker or Inspector for the inspection.

            </div>

            {message}

            <form method="POST">

                <label>📍 Location to Inspect</label>

                <input
                    name="location"
                    placeholder="Enter inspection location"
                    required
                >

                <button class="btn btn-purple">
                    🎲 Randomly Assign Inspection
                </button>

            </form>

        </div>


        <div class="card">

            <h2>📋 All Assignment History</h2>

            <div style="overflow-x:auto;">

                <table>

                    <tr>
                        <th>Location</th>
                        <th>Assigned To</th>
                        <th>Role</th>
                        <th>Assigned Time</th>
                        <th>Status</th>
                    </tr>

                    {rows}

                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# MY ASSIGNMENTS - WORKER / INSPECTOR ONLY
# ============================================================

@app.route("/my-assignments")
def my_assignments():

    if not role_required("Worker", "Inspector"):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    assignment_list = conn.execute("""
        SELECT *
        FROM assignments
        WHERE user_id = ?
        ORDER BY id DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    rows = ""

    for assignment in assignment_list:

        if assignment["status"] == "Completed":

            action = """
                <span class="badge">
                    ✅ Inspection Completed
                </span>
            """

        else:

            action = f"""
                <a class="btn btn-green"
                   href="/inspection/{assignment['id']}">
                    🔍 Conduct Inspection
                </a>
            """

        rows += f"""
        <tr>

            <td>
                📍 {html.escape(assignment["location"])}
            </td>

            <td>
                {assignment["assigned_at"]}
            </td>

            <td>
                {assignment["status"]}
            </td>

            <td>
                {action}
            </td>

        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="4"
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

                🔐 You can access only inspections
                assigned specifically to you.

            </div>

            <div style="overflow-x:auto;">

                <table>

                    <tr>
                        <th>Location</th>
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
# FIELD INSPECTION
# ============================================================

@app.route(
    "/inspection/<int:assignment_id>",
    methods=["GET", "POST"]
)
def inspection(assignment_id):

    if not role_required("Worker", "Inspector"):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    # IMPORTANT:
    # User can access only THEIR OWN assignment
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
        return "⛔ Inspection access denied.", 403

    # --------------------------------------------------------
    # SUBMIT INSPECTION
    # --------------------------------------------------------

    if request.method == "POST":

        location = assignment["location"]

        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]

        description = request.form[
            "description"
        ].strip()

        latitude = request.form.get(
            "latitude", ""
        )

        longitude = request.form.get(
            "longitude", ""
        )

        # ----------------------------------------------------
        # PHOTO UPLOAD
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # DETECT ISSUES
        # ----------------------------------------------------

        detected_issues = []

        if cleanliness == "No":
            detected_issues.append("Cleanliness")

        if safety == "No":
            detected_issues.append("Safety")

        if facilities == "No":
            detected_issues.append("Facilities")

        # ----------------------------------------------------
        # SAVE EACH DETECTED ISSUE
        # ----------------------------------------------------

        for issue_type in detected_issues:

            previous_count = conn.execute("""
                SELECT COUNT(*) AS count
                FROM issues
                WHERE LOWER(location) =
                      LOWER(?)
            """, (
                location,
            )).fetchone()["count"]

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
                    longitude
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                longitude
            ))

        # Mark assignment completed
        conn.execute("""
            UPDATE assignments
            SET status = 'Completed'
            WHERE id = ?
        """, (
            assignment_id,
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>🔍 Field Inspection</h1>

            <div class="info">

                📍 Assigned Location:
                <b>
                    {html.escape(assignment["location"])}
                </b>

                <br><br>

                👤 Inspector/Worker:
                <b>
                    {html.escape(session["name"])}
                </b>

            </div>

            <form
                method="POST"
                enctype="multipart/form-data"
            >

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

                <input
                    type="file"
                    name="photo"
                    accept="image/*"
                >


                <label>
                    📍 GPS Coordinates
                </label>

                <input
                    id="latitude"
                    name="latitude"
                    placeholder="Latitude"
                    readonly
                >

                <input
                    id="longitude"
                    name="longitude"
                    placeholder="Longitude"
                    readonly
                >

                <button
                    type="button"
                    class="btn btn-purple"
                    onclick="getLocation()"
                >
                    📍 Capture My Location
                </button>


                <label>
                    📝 Inspection Description
                </label>

                <textarea
                    name="description"
                    placeholder="Describe any issues found..."
                ></textarea>


                <button
                    class="btn btn-green"
                    type="submit"
                >
                    📤 Submit Inspection Report
                </button>

            </form>

        </div>

    </div>


    <script>

    function getLocation() {

        if (navigator.geolocation) {

            navigator.geolocation.getCurrentPosition(

                function(position) {

                    document.getElementById(
                        "latitude"
                    ).value =
                        position.coords.latitude;

                    document.getElementById(
                        "longitude"
                    ).value =
                        position.coords.longitude;

                    alert(
                        "📍 Location captured successfully!"
                    );
                },

                function() {

                    alert(
                        "❌ Please allow location permission."
                    );
                }
            );
        }

        else {

            alert(
                "Geolocation is not supported."
            );
        }
    }

    </script>
    """


# ============================================================
# SERVE UPLOADED EVIDENCE
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

    role = session["role"]

    # --------------------------------------------------------
    # AUTHORITY SEES ALL REPORTS
    # --------------------------------------------------------

    if role == "Authority":

        issues = conn.execute("""
            SELECT
                issues.*,
                users.name AS reporter_name
            FROM issues
            LEFT JOIN users
            ON issues.reporter_id = users.id
            ORDER BY issues.id DESC
        """).fetchall()

    # --------------------------------------------------------
    # WORKER / INSPECTOR SEES ONLY OWN REPORTS
    # --------------------------------------------------------

    else:

        issues = conn.execute("""
            SELECT
                issues.*,
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

    high_issues = [
        issue for issue in issues
        if issue["priority"] == "High"
    ]

    # --------------------------------------------------------
    # HIGH PRIORITY ALERT - AUTHORITY
    # --------------------------------------------------------

    high_alert = ""

    if role == "Authority" and high_issues:

        high_alert = f"""
        <div class="high-alert">

            <h2>🚨 High Priority Alert!</h2>

            <p>
                <b>{len(high_issues)}</b>
                high priority issue(s) require
                immediate attention.
            </p>

        </div>
        """

    rows = ""

    for issue in issues:

        photo_html = "No Photo"

        if issue["photo"]:

            photo_html = f"""
            <img
                class="evidence-photo"
                src="/uploads/{issue['photo']}"
                alt="Evidence"
            >
            """

        reporter = ""

        if role == "Authority":

            reporter = f"""
                <td>
                    {html.escape(issue["reporter_name"] or "Unknown")}
                </td>
            """

        rows += f"""
        <tr>

            <td>
                📍 {html.escape(issue["location"])}
            </td>

            <td>
                {html.escape(issue["issue_type"])}
            </td>

            <td>
                {html.escape(issue["description"] or "-")}
            </td>

            <td>
                {priority_badge(issue["priority"])}
            </td>

            <td>
                {photo_html}
            </td>

            <td>
                {issue["status"]}
            </td>

            {reporter}

        </tr>
        """

    if not rows:

        colspan = 7 if role == "Authority" else 6

        rows = f"""
        <tr>

            <td
                colspan="{colspan}"
                style="text-align:center;"
            >
                🎉 No inspection issues found.
            </td>

        </tr>
        """

    reporter_heading = ""

    if role == "Authority":
        reporter_heading = "<th>Reported By</th>"

    title = (
        "📊 Real-Time Monitoring Dashboard"
        if role == "Authority"
        else "📊 My Inspection Reports"
    )

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <h1>{title}</h1>

        {high_alert}

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
                        {reporter_heading}
                    </tr>

                    {rows}

                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# ANALYTICS - AUTHORITY ONLY
# ============================================================

@app.route("/analytics")
def analytics():

    if not role_required("Authority"):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    locations = conn.execute("""
        SELECT
            location,
            COUNT(*) AS reports
        FROM issues
        GROUP BY location
        ORDER BY reports DESC
    """).fetchall()

    conn.close()

    rows = ""

    for item in locations:

        priority = calculate_priority(
            item["reports"]
        )

        rows += f"""
        <tr>

            <td>
                📍 {html.escape(item["location"])}
            </td>

            <td>
                {item["reports"]}
            </td>

            <td>
                {priority_badge(priority)}
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

                Priority is automatically calculated
                based on repeated reports at the same
                location.

                <br><br>

                🟢 1 Report = Low |
                🟡 2–3 Reports = Medium |
                🔴 More than 3 = High

            </div>

            <table>

                <tr>
                    <th>Location</th>
                    <th>Total Reports</th>
                    <th>Priority</th>
                </tr>

                {rows}

            </table>

        </div>

    </div>
    """


# ============================================================
# CCTV - AUTHORITY ONLY
# ============================================================

@app.route("/cctv", methods=["GET", "POST"])
def cctv():

    if not role_required("Authority"):
        return "⛔ Access Denied.", 403

    conn = get_connection()

    if request.method == "POST":

        location = request.form[
            "location"
        ].strip()

        feed_url = request.form[
            "feed_url"
        ].strip()

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

            <td>
                {html.escape(feed["location"])}
            </td>

            <td>

                <a
                    class="btn"
                    href="{html.escape(feed["feed_url"])}"
                    target="_blank"
                >
                    📹 Open Feed
                </a>

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

                <label>
                    Camera Location
                </label>

                <input
                    name="location"
                    required
                >

                <label>
                    Authorized Monitoring URL
                </label>

                <input
                    type="url"
                    name="feed_url"
                    required
                >

                <button class="btn">
                    ➕ Add CCTV Feed
                </button>

            </form>

        </div>


        <div class="card">

            <h2>📹 Registered CCTV Feeds</h2>

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
# 🔔 LATEST MEETING API
# ============================================================

@app.route("/api/latest-meeting")
def latest_meeting_notification():

    if not require_login():

        return jsonify({
            "logged_in": False
        }), 401

    if session["role"] not in [
        "Worker",
        "Inspector"
    ]:

        return jsonify({
            "meeting": None
        })

    conn = get_connection()

    meeting = conn.execute("""
        SELECT
            meetings.id,
            meetings.title,
            meetings.created_at,
            meetings.meeting_url,
            users.name AS authority_name

        FROM meetings

        LEFT JOIN users
        ON meetings.created_by = users.id

        ORDER BY meetings.id DESC
        LIMIT 1

    """).fetchone()

    conn.close()

    if meeting is None:

        return jsonify({
            "meeting": None
        })

    return jsonify({
        "meeting": {

            "id": meeting["id"],
            "title": meeting["title"],
            "created_at": meeting["created_at"],
            "meeting_url": meeting["meeting_url"],

            "authority_name":
                meeting["authority_name"]
                or "Authority"
        }
    })


# ============================================================
# MEETINGS
# ============================================================

@app.route("/meetings", methods=["GET", "POST"])
def meetings():

    if not require_login():
        return redirect(url_for("login"))

    conn = get_connection()
    message = ""

    # --------------------------------------------------------
    # AUTHORITY CREATES MEETING
    # --------------------------------------------------------

    if request.method == "POST":

        if session["role"] != "Authority":

            conn.close()

            return (
                "⛔ Only Authority can create meetings.",
                403
            )

        title = request.form["title"].strip()

        # RANDOM UNIQUE MEETING CODE
        meeting_code = uuid.uuid4().hex[:16].upper()

        # RANDOM UNIQUE INTERNAL LINK
        meeting_url = url_for(
            "meeting_room",
            meeting_code=meeting_code,
            _external=True
        )

        conn.execute("""
            INSERT INTO meetings
            (
                title,
                meeting_url,
                created_at,
                created_by,
                meeting_code
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            meeting_url,
            current_time(),
            session["user_id"],
            meeting_code
        ))

        conn.commit()

        message = f"""
        <div class="info">

            🎉 <b>Meeting Created Successfully!</b>

            <br><br>

            🔔 Workers and Inspectors who are currently
            using the system will receive a popup
            notification automatically.

            <br><br>

            🎥 Meeting:
            <b>{html.escape(title)}</b>

            <br><br>

            🔗 A unique random meeting link has
            been generated successfully.

        </div>
        """

    # --------------------------------------------------------
    # GET ALL MEETINGS
    # --------------------------------------------------------

    meeting_list = conn.execute("""
        SELECT
            meetings.*,
            users.name AS authority_name

        FROM meetings

        LEFT JOIN users
        ON meetings.created_by = users.id

        ORDER BY meetings.id DESC

    """).fetchall()

    conn.close()

    rows = ""

    for meeting in meeting_list:

        authority_name = (
            meeting["authority_name"]
            or "System Authority"
        )

        rows += f"""
        <tr>

            <td>
                {html.escape(meeting["title"])}
            </td>

            <td>
                {html.escape(authority_name)}
            </td>

            <td>
                {meeting["created_at"]}
            </td>

            <td>

                <a
                    class="btn btn-purple"
                    href="{meeting["meeting_url"]}"
                >
                    🎥 Join Meeting
                </a>

            </td>

        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td
                colspan="4"
                style="text-align:center;"
            >
                📭 No meetings available.
            </td>
        </tr>
        """

    # --------------------------------------------------------
    # AUTHORITY CREATE FORM
    # --------------------------------------------------------

    create_form = ""

    if session["role"] == "Authority":

        create_form = """
        <div class="card">

            <h1>🎥 Create Team Meeting</h1>

            <div class="info">

                🔗 A new random unique meeting link
                will be automatically generated.

                <br><br>

                🔔 Workers and Inspectors currently
                logged into the website will receive
                a popup notification.

            </div>

            <form method="POST">

                <label>
                    📝 Meeting Title
                </label>

                <input
                    name="title"
                    placeholder="Example: Emergency Inspection Review"
                    required
                >

                <button
                    class="btn btn-purple"
                    type="submit"
                >
                    🔔 Create Meeting & Notify Team
                </button>

            </form>

        </div>
        """

    # --------------------------------------------------------
    # LATEST MEETING CARD FOR STAFF
    # --------------------------------------------------------

    notification = ""

    if (
        session["role"] in ["Worker", "Inspector"]
        and meeting_list
    ):

        latest = meeting_list[0]

        notification = f"""
        <div class="notification">

            <h2>🔔 Latest Team Meeting</h2>

            <p>

                🎥
                <b>
                    {html.escape(latest["title"])}
                </b>

                <br><br>

                A meeting has been created by the
                Authority. Please attend if required.

            </p>

            <a
                class="btn btn-purple"
                href="{latest["meeting_url"]}"
            >
                🎥 Attend Meeting
            </a>

        </div>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        {message}

        {notification}

        {create_form}

        <div class="card">

            <h2>🎥 Available Meetings</h2>

            <div style="overflow-x:auto;">

                <table>

                    <tr>
                        <th>Meeting</th>
                        <th>Created By</th>
                        <th>Created Time</th>
                        <th>Join</th>
                    </tr>

                    {rows}

                </table>

            </div>

        </div>

    </div>
    """


# ============================================================
# MEETING ROOM
# ============================================================

@app.route("/meeting/<meeting_code>")
def meeting_room(meeting_code):

    if not require_login():
        return redirect(url_for("login"))

    conn = get_connection()

    meeting = conn.execute("""
        SELECT
            meetings.*,
            users.name AS authority_name

        FROM meetings

        LEFT JOIN users
        ON meetings.created_by = users.id

        WHERE meetings.meeting_code = ?

    """, (
        meeting_code,
    )).fetchone()

    if meeting is None:

        conn.close()

        return "❌ Meeting not found.", 404

    # Record participant
    conn.execute("""
        INSERT OR IGNORE INTO meeting_participants
        (meeting_id, user_id, joined_at)
        VALUES (?, ?, ?)
    """, (
        meeting["id"],
        session["user_id"],
        current_time()
    ))

    conn.commit()

    participants = conn.execute("""
        SELECT
            users.name,
            users.role,
            meeting_participants.joined_at

        FROM meeting_participants

        JOIN users
        ON meeting_participants.user_id = users.id

        WHERE meeting_participants.meeting_id = ?

        ORDER BY meeting_participants.joined_at ASC

    """, (
        meeting["id"],
    )).fetchall()

    conn.close()

    participant_rows = ""

    for participant in participants:

        participant_rows += f"""
        <tr>

            <td>
                👤 {html.escape(participant["name"])}
            </td>

            <td>
                {participant["role"]}
            </td>

            <td>
                🟢 Joined
            </td>

        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div
            class="card"
            style="text-align:center;"
        >

            <h1>
                🎥 Smart Inspection Meeting Room
            </h1>

            <div class="info">

                🟢
                <b>You have successfully joined!</b>

                <br><br>

                🎥 Meeting:
                <b>
                    {html.escape(meeting["title"])}
                </b>

                <br><br>

                👤 Joined as:
                <b>
                    {html.escape(session["name"])}
                </b>

                ({session["role"]})

            </div>

            <p>

                🤝 This meeting module helps the
                inspection team coordinate and keeps
                track of participants.

            </p>

            <a
                class="btn"
                href="/meetings"
            >
                ← Back to Meetings
            </a>

        </div>


        <div class="card">

            <h2>
                👥 Meeting Participants
            </h2>

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
    """


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print(
        " Smart Monitoring & Inspection System is Starting..."
    )
    print(" Open: http://127.0.0.1:5000")
    print("=" * 60)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
