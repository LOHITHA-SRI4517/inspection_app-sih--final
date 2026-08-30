from flask import (
    Flask, request, redirect, url_for,
    session, send_from_directory, jsonify
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
FACE_FOLDER = "face_captures"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["FACE_FOLDER"] = FACE_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FACE_FOLDER, exist_ok=True)


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

    return (
        f'<span class="badge {classes.get(priority, "")}">'
        f'{icons.get(priority, "⚪")} {priority}</span>'
    )


def require_login():
    return "user_id" in session


# ============================================================
# DATABASE SETUP
# ============================================================

def add_column_if_missing(conn, table, column, definition):

    columns = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    column_names = [item["name"] for item in columns]

    if column not in column_names:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


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

    # ISSUES
    conn.execute("""
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
        )
    """)

    # ASSIGNMENTS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            status TEXT DEFAULT 'Assigned',
            face_verified INTEGER DEFAULT 0
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
            created_at TEXT NOT NULL,
            created_by INTEGER,
            meeting_code TEXT
        )
    """)

    # MEETING PARTICIPANTS
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meeting_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            UNIQUE(meeting_id, user_id)
        )
    """)

    # Support old database versions
    add_column_if_missing(
        conn, "assignments",
        "face_verified", "INTEGER DEFAULT 0"
    )

    add_column_if_missing(
        conn, "issues",
        "priority", "TEXT DEFAULT 'Low'"
    )

    add_column_if_missing(
        conn, "issues",
        "photo", "TEXT"
    )

    add_column_if_missing(
        conn, "issues",
        "reporter_id", "INTEGER"
    )

    add_column_if_missing(
        conn, "issues",
        "latitude", "TEXT"
    )

    add_column_if_missing(
        conn, "issues",
        "longitude", "TEXT"
    )

    add_column_if_missing(
        conn, "issues",
        "verified", "INTEGER DEFAULT 0"
    )

    add_column_if_missing(
        conn, "meetings",
        "created_by", "INTEGER"
    )

    add_column_if_missing(
        conn, "meetings",
        "meeting_code", "TEXT"
    )

    # DEFAULT AUTHORITY
    user = conn.execute(
        "SELECT id FROM users WHERE unique_id = ?",
        ("ADMIN001",)
    ).fetchone()

    if user is None:
        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "ADMIN001",
            "System Authority",
            generate_password_hash("admin123"),
            "Authority",
            current_time()
        ))

    # DEFAULT INSPECTOR
    user = conn.execute(
        "SELECT id FROM users WHERE unique_id = ?",
        ("INS001",)
    ).fetchone()

    if user is None:
        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "INS001",
            "Inspection Officer",
            generate_password_hash("inspector123"),
            "Inspector",
            current_time()
        ))

    # DEFAULT WORKER
    user = conn.execute(
        "SELECT id FROM users WHERE unique_id = ?",
        ("WORK001",)
    ).fetchone()

    if user is None:
        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "WORK001",
            "Demo Field Worker",
            generate_password_hash("worker123"),
            "Worker",
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

* { box-sizing: border-box; }

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
    gap: 10px;
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
    padding: 70px 25px;
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

.btn-green { background: #059669; }
.btn-purple { background: #7c3aed; }
.btn-orange { background: #ea580c; }
.btn-red { background: #dc2626; }

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

textarea { min-height: 100px; }

h1, h2, h3 { color: #1e3a8a; }

.info {
    background: #eff6ff;
    padding: 15px;
    border-left: 5px solid #2563eb;
    border-radius: 7px;
    margin: 15px 0;
}

.notification {
    background: #fff7ed;
    padding: 18px;
    border-left: 5px solid #ea580c;
    border-radius: 10px;
    margin-bottom: 20px;
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
    max-height: 80px;
    object-fit: cover;
    border-radius: 8px;
}

@media(max-width:700px) {
    .container { padding: 15px; }
    .card { padding: 18px; }
    .hero h1 { font-size: 29px; }
}

</style>
"""


# ============================================================
# 🔔 AUTOMATIC NOTIFICATION SCRIPT
# ============================================================

def notification_script():

    if not require_login():
        return ""

    # Only workers and inspectors receive notifications
    if session.get("role") not in ["Worker", "Inspector"]:
        return ""

    return """
    <script>

    // ========================================================
    // SMART MEETING NOTIFICATION SYSTEM
    // ========================================================

    let lastMeetingId =
        localStorage.getItem("lastMeetingId");

    // Ask permission for browser notifications
    if ("Notification" in window &&
        Notification.permission === "default") {

        Notification.requestPermission();
    }


    function checkForNewMeeting() {

        fetch("/api/latest-meeting")

        .then(function(response) {

            if (!response.ok) {
                return null;
            }

            return response.json();
        })

        .then(function(data) {

            if (!data || !data.meeting) {
                return;
            }

            const meeting = data.meeting;
            const meetingId = String(meeting.id);

            // ------------------------------------------------
            // First time opening website:
            // Save current meeting without showing old alert
            // ------------------------------------------------

            if (lastMeetingId === null) {

                localStorage.setItem(
                    "lastMeetingId",
                    meetingId
                );

                lastMeetingId = meetingId;

                return;
            }


            // ------------------------------------------------
            // NEW MEETING DETECTED
            // ------------------------------------------------

            if (meetingId !== lastMeetingId) {

                // Browser notification
                if (
                    "Notification" in window &&
                    Notification.permission === "granted"
                ) {

                    const notification =
                        new Notification(
                            "🔔 New Inspection Meeting!",
                            {
                                body:
                                    meeting.authority_name
                                    + " created: "
                                    + meeting.title
                            }
                        );

                    notification.onclick = function() {

                        window.focus();

                        window.location.href =
                            meeting.meeting_url;
                    };
                }


                // Website popup for demonstration
                alert(
                    "🔔 NEW MEETING NOTIFICATION!\\n\\n"
                    + "👤 Created by: "
                    + meeting.authority_name
                    + "\\n\\n"
                    + "🎥 Meeting: "
                    + meeting.title
                    + "\\n\\n"
                    + "Please attend the meeting!"
                );


                // Remember this meeting
                localStorage.setItem(
                    "lastMeetingId",
                    meetingId
                );

                lastMeetingId = meetingId;
            }

        })

        .catch(function(error) {
            console.log(
                "Meeting notification check failed:",
                error
            );
        });
    }


    // Check immediately
    checkForNewMeeting();

    // Check every 3 seconds
    setInterval(checkForNewMeeting, 3000);

    </script>
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

    if session["role"] in ["Worker", "Inspector"]:
        links += """
            <a href="/my-assignments">📋 My Assignments</a>
        """

    if session["role"] == "Authority":
        links += """
            <a href="/users">👥 Users</a>
            <a href="/assignments">🎲 Assign</a>
            <a href="/analytics">📈 Analytics</a>
            <a href="/cctv">📹 CCTV</a>
        """

    links += """
        <a href="/meetings">🎥 Meetings</a>
    """

    links += '<a href="/logout">🚪 Logout</a>'

    return f"""
    <div class="navbar">
        <div><b>🏛️ Smart Monitoring & Inspection</b></div>
        <div>{links}</div>
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
        <b>🏛️ Smart Monitoring & Inspection System</b>
        <a href="/login">🔐 Login</a>
    </div>

    <div class="hero">

        <h1>🏛️ Smart Real-Time Monitoring & Inspection System</h1>

        <p style="font-size:18px;">
            Secure inspection, evidence capture, smart priority
            detection and role-based monitoring.
        </p>

        <a class="btn" href="/login">
            🔐 Login to System
        </a>

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
            user["password"], password
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
                       required>

                <label>🔑 Password</label>
                <input type="password"
                       name="password"
                       required>

                <button class="btn"
                        style="width:100%;"
                        type="submit">
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
    buttons = ""

    if role in ["Worker", "Inspector"]:
        buttons = """
        <a class="btn" href="/my-assignments">
            📋 View My Assignments
        </a>

        <a class="btn btn-purple" href="/meetings">
            🎥 View Meetings
        </a>
        """

    if role == "Authority":
        buttons = """
        <a class="btn btn-purple" href="/users">
            👥 Manage Users
        </a>

        <a class="btn btn-orange" href="/assignments">
            🎲 Assign Inspection
        </a>

        <a class="btn btn-green" href="/analytics">
            📈 View Analytics
        </a>

        <a class="btn btn-purple" href="/meetings">
            🎥 Create Meeting
        </a>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card" style="text-align:center;">

            <h1>Welcome, {session["name"]}! 👋</h1>

            <p>
                Role: <span class="badge">{role}</span>
            </p>

            <div class="info">
                🔐 Your available features depend on your
                authorized role.
            </div>

            {buttons}

            <a class="btn btn-green" href="/dashboard">
                📊 Dashboard
            </a>

        </div>

        <div class="card">

            <h2>🎯 Inspection Workflow</h2>

            <p style="font-size:17px; line-height:2;">
                👨‍💼 Authority Assigns →
                📷 Identity Verification →
                🔍 Inspection →
                📸 Evidence →
                📤 Report →
                🤖 Priority Analysis →
                🔔 Automatic Notification →
                🎥 Team Coordination →
                ✅ Resolution
            </p>

        </div>

    </div>
    """


# ============================================================
# USER MANAGEMENT
# ============================================================

@app.route("/users", methods=["GET", "POST"])
def users():

    if not require_login() or session["role"] != "Authority":
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
            ✅ <b>User Created Successfully!</b><br><br>
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
                    <option value="Worker">Worker</option>
                    <option value="Inspector">Inspector</option>
                    <option value="Authority">Authority</option>
                </select>

                <button class="btn btn-purple">
                    ➕ Create User
                </button>

            </form>

        </div>

        <div class="card">

            <h2>👥 Registered Users</h2>

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
    """


# ============================================================
# ASSIGN INSPECTION
# ============================================================

@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

    conn = get_connection()

    workers = conn.execute("""
        SELECT id, name, unique_id
        FROM users
        WHERE role IN ('Worker', 'Inspector')
    """).fetchall()

    message = ""

    if request.method == "POST":

        location = request.form["location"].strip()

        if workers:

            selected = random.choice(workers)

            conn.execute("""
                INSERT INTO assignments
                (user_id, location, assigned_at, status, face_verified)
                VALUES (?, ?, ?, ?, ?)
            """, (
                selected["id"],
                location,
                current_time(),
                "Assigned",
                0
            ))

            conn.commit()

            message = f"""
            <div class="info">
                🎲 <b>Inspection Assigned Successfully!</b><br><br>
                📍 Location: <b>{location}</b><br>
                👤 Assigned To: <b>{selected["name"]}</b><br>
                🆔 ID: <b>{selected["unique_id"]}</b>
            </div>
            """

    assignment_list = conn.execute("""
        SELECT assignments.*, users.name, users.unique_id
        FROM assignments
        JOIN users ON assignments.user_id = users.id
        ORDER BY assignments.id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for item in assignment_list:
        rows += f"""
        <tr>
            <td>{item["location"]}</td>
            <td>{item["name"]}</td>
            <td>{item["unique_id"]}</td>
            <td>{item["assigned_at"]}</td>
            <td>{item["status"]}</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>🎲 Automated Inspection Assignment</h1>

            {message}

            <form method="POST">

                <label>📍 Location to Inspect</label>
                <input name="location" required>

                <button class="btn btn-purple">
                    🎲 Randomly Assign
                </button>

            </form>

        </div>

        <div class="card">

            <h2>📋 Assignment History</h2>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Assigned To</th>
                    <th>ID</th>
                    <th>Time</th>
                    <th>Status</th>
                </tr>

                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# MY ASSIGNMENTS
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

        elif assignment["face_verified"] == 1:
            action = f"""
            <a class="btn btn-green"
               href="/inspection/{assignment['id']}">
               📋 Start Inspection
            </a>
            """

        else:
            action = f"""
            <a class="btn btn-purple"
               href="/face-verification/{assignment['id']}">
               📷 Verify Face
            </a>
            """

        verification = (
            "✅ Verified"
            if assignment["face_verified"] == 1
            else "⏳ Required"
        )

        rows += f"""
        <tr>
            <td>📍 {assignment["location"]}</td>
            <td>{assignment["assigned_at"]}</td>
            <td>{verification}</td>
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

            <table>
                <tr>
                    <th>Location</th>
                    <th>Assigned Time</th>
                    <th>Verification</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>

                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# FACE VERIFICATION
# ============================================================

@app.route("/face-verification/<int:assignment_id>",
           methods=["GET", "POST"])
def face_verification(assignment_id):

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
        return "⛔ Invalid assignment.", 403

    if request.method == "POST":

        photo = request.files.get("face_photo")

        if not photo or not photo.filename:
            conn.close()
            return "❌ Please capture your face photo."

        if not allowed_file(photo.filename):
            conn.close()
            return "❌ Invalid image format."

        filename = (
            "face_"
            + str(session["user_id"])
            + "_"
            + uuid.uuid4().hex
            + ".jpg"
        )

        photo.save(
            os.path.join(
                app.config["FACE_FOLDER"],
                filename
            )
        )

        conn.execute("""
            UPDATE assignments
            SET face_verified = 1
            WHERE id = ?
            AND user_id = ?
        """, (
            assignment_id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect(
            url_for(
                "inspection",
                assignment_id=assignment_id
            )
        )

    conn.close()

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card"
             style="max-width:650px; margin:auto;">

            <h1>📷 Security Face Verification</h1>

            <div class="info">
                📍 Assigned Location:
                <b>{assignment["location"]}</b><br><br>

                Please allow camera access and capture
                your photo before starting.
            </div>

            <video id="video"
                   width="100%"
                   autoplay
                   playsinline
                   style="background:#111;
                          border-radius:12px;">
            </video>

            <canvas id="canvas"
                    style="display:none;">
            </canvas>

            <form id="faceForm"
                  method="POST"
                  enctype="multipart/form-data">

                <input type="file"
                       id="face_photo"
                       name="face_photo"
                       style="display:none;">

                <button type="button"
                        class="btn btn-purple"
                        onclick="captureFace()">
                    📸 Capture & Verify
                </button>

            </form>

            <p id="message"
               class="error">
            </p>

        </div>

    </div>

    <script>

    const video = document.getElementById("video");

    navigator.mediaDevices.getUserMedia({{
        video: true
    }})
    .then(function(stream) {{
        video.srcObject = stream;
    }})
    .catch(function() {{
        document.getElementById("message").innerHTML =
            "❌ Camera access denied.";
    }});


    function captureFace() {{

        const canvas =
            document.getElementById("canvas");

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context =
            canvas.getContext("2d");

        context.drawImage(
            video, 0, 0,
            canvas.width,
            canvas.height
        );

        canvas.toBlob(function(blob) {{

            const file = new File(
                [blob],
                "face.jpg",
                {{type: "image/jpeg"}}
            );

            const dataTransfer =
                new DataTransfer();

            dataTransfer.items.add(file);

            document.getElementById(
                "face_photo"
            ).files = dataTransfer.files;

            document.getElementById(
                "faceForm"
            ).submit();

        }}, "image/jpeg");
    }}

    </script>
    """


# ============================================================
# INSPECTION
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
        AND face_verified = 1
        AND status = 'Assigned'
    """, (
        assignment_id,
        session["user_id"]
    )).fetchone()

    if assignment is None:
        conn.close()
        return "⛔ Inspection access denied.", 403

    if request.method == "POST":

        location = assignment["location"]
        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]

        description = request.form["description"].strip()

        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")

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

        detected_issues = []

        if cleanliness == "No":
            detected_issues.append("Cleanliness")

        if safety == "No":
            detected_issues.append("Safety")

        if facilities == "No":
            detected_issues.append("Facilities")

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
                    location, issue_type, description,
                    created_at, status, priority,
                    photo, reporter_id,
                    latitude, longitude, verified
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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

        conn.execute("""
            UPDATE assignments
            SET status = 'Completed'
            WHERE id = ?
        """, (assignment_id,))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📋 Field Inspection</h1>

            <div class="info">
                📍 Location:
                <b>{assignment["location"]}</b><br>
                🔐 Face Verification:
                <b>Completed ✅</b>
            </div>

            <form method="POST"
                  enctype="multipart/form-data">

                <label>🧹 Is the area clean?</label>

                <select name="cleanliness">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">
                        No ❌ - Issue Found
                    </option>
                </select>

                <label>🛡️ Is the area safe?</label>

                <select name="safety">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">
                        No ❌ - Issue Found
                    </option>
                </select>

                <label>🏢 Are facilities working properly?</label>

                <select name="facilities">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">
                        No ❌ - Issue Found
                    </option>
                </select>

                <label>📸 Upload Photo Evidence</label>

                <input type="file"
                       name="photo"
                       accept="image/*">

                <label>📍 GPS Coordinates (Optional)</label>

                <input id="latitude"
                       name="latitude"
                       placeholder="Latitude">

                <input id="longitude"
                       name="longitude"
                       placeholder="Longitude">

                <button type="button"
                        class="btn btn-purple"
                        onclick="getLocation()">
                    📍 Get My Location
                </button>

                <label>📝 Description</label>

                <textarea name="description"
                          placeholder="Describe the issue...">
                </textarea>

                <button class="btn"
                        type="submit">
                    📤 Submit Inspection
                </button>

            </form>

        </div>

    </div>

    <script>

    function getLocation() {{

        if (navigator.geolocation) {{

            navigator.geolocation.getCurrentPosition(

                function(position) {{

                    document.getElementById(
                        "latitude"
                    ).value =
                        position.coords.latitude;

                    document.getElementById(
                        "longitude"
                    ).value =
                        position.coords.longitude;

                }},

                function() {{
                    alert(
                        "Please allow location permission."
                    );
                }}
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

    if session["role"] == "Authority":

        issues = conn.execute("""
            SELECT issues.*, users.name AS reporter_name
            FROM issues
            LEFT JOIN users
            ON issues.reporter_id = users.id
            ORDER BY issues.id DESC
        """).fetchall()

    else:

        issues = conn.execute("""
            SELECT issues.*, users.name AS reporter_name
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

    rows = ""

    for issue in issues:

        photo_html = "No Photo"

        if issue["photo"]:
            photo_html = f"""
            <img class="evidence-photo"
                 src="/uploads/{issue['photo']}"
                 alt="Evidence">
            """

        rows += f"""
        <tr>
            <td>📍 {issue["location"]}</td>
            <td>{issue["issue_type"]}</td>
            <td>{issue["description"] or "-"}</td>
            <td>{priority_badge(issue["priority"])}</td>
            <td>{photo_html}</td>
            <td>{issue["status"]}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="6"
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

        </div>

        <div class="card">

            <h2>🚨 Inspection Reports</h2>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Issue</th>
                    <th>Description</th>
                    <th>Priority</th>
                    <th>Evidence</th>
                    <th>Status</th>
                </tr>

                {rows}

            </table>

        </div>

    </div>
    """


# ============================================================
# ANALYTICS
# ============================================================

@app.route("/analytics")
def analytics():

    if not require_login() or session["role"] != "Authority":
        return "⛔ Access Denied.", 403

    conn = get_connection()

    locations = conn.execute("""
        SELECT location, COUNT(*) AS reports
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
            <td>{item["location"]}</td>
            <td>{item["reports"]}</td>
            <td>{priority_badge(priority)}</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📈 Inspection Analytics</h1>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Reports</th>
                    <th>Priority</th>
                </tr>

                {rows}

            </table>

        </div>

    </div>
    """


# ============================================================
# CCTV MODULE
# ============================================================

@app.route("/cctv", methods=["GET", "POST"])
def cctv():

    if not require_login() or session["role"] != "Authority":
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
        SELECT * FROM cctv_feeds
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
# 🔔 NOTIFICATION API
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
# MEETINGS MODULE
# ============================================================

@app.route("/meetings", methods=["GET", "POST"])
def meetings():

    if not require_login():
        return redirect(url_for("login"))

    conn = get_connection()
    message = ""

    # ========================================================
    # AUTHORITY CREATES MEETING
    # ========================================================

    if request.method == "POST":

        if session["role"] != "Authority":
            conn.close()
            return "⛔ Only Authority can create meetings.", 403

        title = request.form["title"].strip()

        # Generate unique meeting code
        meeting_code = uuid.uuid4().hex[:12].upper()

        # Generate unique meeting link
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

            🔔 The system has sent a meeting alert
            to Workers and Inspectors who are active
            on the website.

            <br><br>

            🎥 Meeting:
            <b>{title}</b>

            <br><br>

            🔑 Meeting Code:
            <b>{meeting_code}</b>

        </div>
        """

    # ========================================================
    # GET MEETING LIST
    # ========================================================

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
            if meeting["authority_name"]
            else "System Authority"
        )

        rows += f"""
        <tr>
            <td>{meeting["title"]}</td>
            <td>{authority_name}</td>
            <td>{meeting["created_at"]}</td>
            <td>

                <a class="btn btn-purple"
                   href="{meeting["meeting_url"]}">
                    🎥 Join Meeting
                </a>

            </td>
        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="4"
                style="text-align:center;">
                📭 No meetings available.
            </td>
        </tr>
        """

    # ========================================================
    # AUTHORITY CREATE FORM
    # ========================================================

    create_form = ""

    if session["role"] == "Authority":

        create_form = """
        <div class="card">

            <h1>🎥 Create Team Meeting</h1>

            <div class="info">

                🔗 A unique meeting link will
                automatically be generated.

                <br><br>

                🔔 Workers and Inspectors currently
                using the website will automatically
                receive a notification.

            </div>

            <form method="POST">

                <label>📝 Meeting Title</label>

                <input
                    name="title"
                    placeholder="Example: Emergency Inspection Review"
                    required
                >

                <button class="btn btn-purple"
                        type="submit">

                    🔔 Create Meeting & Notify Team

                </button>

            </form>

        </div>
        """

    # ========================================================
    # WORKER MEETING NOTIFICATION ON MEETINGS PAGE
    # ========================================================

    notification = ""

    if (
        session["role"] in ["Worker", "Inspector"]
        and meeting_list
    ):

        latest = meeting_list[0]

        authority_name = (
            latest["authority_name"]
            if latest["authority_name"]
            else "Authority"
        )

        notification = f"""
        <div class="notification">

            <h2>🔔 Latest Meeting</h2>

            <p style="font-size:17px;">

                📢 <b>{authority_name}</b>
                has created a meeting.

                <br><br>

                🎥 <b>{latest["title"]}</b>

                <br><br>

                👉 Please attend the meeting.

            </p>

            <a class="btn btn-purple"
               href="{latest["meeting_url"]}">

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
    """, (meeting_code,)).fetchone()

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
    """, (meeting["id"],)).fetchall()

    conn.close()

    participant_rows = ""

    for participant in participants:

        participant_rows += f"""
        <tr>
            <td>👤 {participant["name"]}</td>
            <td>{participant["role"]}</td>
            <td>🟢 Joined</td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card"
             style="text-align:center;">

            <h1>🎥 Smart Inspection Meeting Room</h1>

            <div class="info">

                🟢 <b>You have successfully joined!</b>

                <br><br>

                🎥 Meeting:
                <b>{meeting["title"]}</b>

                <br><br>

                🔑 Meeting Code:
                <b>{meeting_code}</b>

                <br><br>

                👤 Joined as:
                <b>{session["name"]}</b>
                ({session["role"]})

            </div>

            <p>
                🤝 This meeting room helps the
                inspection team coordinate and
                tracks meeting participants.
            </p>

            <a class="btn"
               href="/meetings">
                ← Back to Meetings
            </a>

        </div>

        <div class="card">

            <h2>👥 Meeting Participants</h2>

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
    print(" Smart Monitoring & Inspection System is Starting...")
    print(" Open: http://127.0.0.1:5000")
    print("=" * 60)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )