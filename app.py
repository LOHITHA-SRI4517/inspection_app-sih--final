from flask import Flask, request, redirect, url_for, session, send_from_directory, jsonify
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

DATABASE = "inspection.db"
UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def require_login():
    return "user_id" in session


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# PRIORITY SYSTEM
# Low     = 1 report
# Medium  = 2-3 reports
# High    = More than 3 reports
# ============================================================

def calculate_priority(report_count):

    if report_count > 3:
        return "High"

    elif report_count >= 2:
        return "Medium"

    return "Low"


def priority_badge(priority):

    if priority == "High":
        return '<span class="badge priority-high">🔴 High</span>'

    if priority == "Medium":
        return '<span class="badge priority-medium">🟡 Medium</span>'

    return '<span class="badge priority-low">🟢 Low</span>'


# ============================================================
# DATABASE SETUP
# ============================================================

def create_database():

    conn = get_connection()

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            status TEXT DEFAULT 'Assigned'
        )
    """)

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            meeting_code TEXT UNIQUE NOT NULL,
            meeting_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meeting_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            UNIQUE(meeting_id, user_id)
        )
    """)

    # Default Authority
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

    # Default Inspector
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

    # Default Worker
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
            "Field Worker",
            generate_password_hash("worker123"),
            "Worker",
            current_time()
        ))

    conn.commit()
    conn.close()


create_database()


# ============================================================
# DESIGN
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
    gap: 15px;
}

.navbar a {
    color: white;
    text-decoration: none;
    margin-left: 12px;
    font-weight: bold;
}

.container {
    max-width: 1200px;
    margin: auto;
    padding: 30px 20px;
}

.card {
    background: white;
    padding: 25px;
    border-radius: 18px;
    margin-bottom: 22px;
    box-shadow: 0 7px 22px rgba(0,0,0,0.08);
}

.hero {
    text-align: center;
    padding: 80px 20px;
}

.hero h1 {
    color: #1e3a8a;
    font-size: 40px;
}

.btn {
    display: inline-block;
    background: #2563eb;
    color: white;
    padding: 11px 18px;
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

.btn-red {
    background: #dc2626;
}

input, select, textarea {
    width: 100%;
    padding: 12px;
    margin-top: 7px;
    margin-bottom: 16px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
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
    border-radius: 8px;
    margin: 15px 0;
}

.notification {
    background: #fff7ed;
    padding: 18px;
    border-left: 5px solid #f97316;
    border-radius: 10px;
    margin-bottom: 20px;
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
    margin-bottom: 25px;
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
        padding: 16px;
    }

    .hero h1 {
        font-size: 28px;
    }

    table {
        font-size: 12px;
    }
}

</style>
"""


# ============================================================
# NAVBAR + MEETING NOTIFICATIONS
# ============================================================

def notification_script():

    if not require_login():
        return ""

    if session.get("role") not in ["Worker", "Inspector"]:
        return ""

    # This is NOT an f-string, so normal JavaScript braces work
    return """
    <script>

    let lastMeetingId =
        localStorage.getItem("smartInspectionLastMeeting");

    function checkMeeting() {

        fetch("/api/latest-meeting")
        .then(response => response.json())
        .then(data => {

            if (!data.meeting) return;

            const meeting = data.meeting;
            const id = String(meeting.id);

            if (lastMeetingId === null) {

                localStorage.setItem(
                    "smartInspectionLastMeeting",
                    id
                );

                lastMeetingId = id;
                return;
            }

            if (id !== lastMeetingId) {

                alert(
                    "🔔 NEW MEETING!\\n\\n"
                    + meeting.title
                    + "\\n\\nCreated by: "
                    + meeting.authority_name
                    + "\\n\\nPlease join the meeting."
                );

                localStorage.setItem(
                    "smartInspectionLastMeeting",
                    id
                );

                lastMeetingId = id;
            }

        })
        .catch(error => console.log(error));
    }

    checkMeeting();
    setInterval(checkMeeting, 5000);

    </script>
    """


def navbar():

    if not require_login():
        return ""

    links = """
        <a href="/home">🏠 Home</a>
        <a href="/dashboard">📊 Dashboard</a>
    """

    if session["role"] in ["Worker", "Inspector"]:
        links += """
            <a href="/my-assignments">📋 My Work</a>
        """

    if session["role"] == "Authority":
        links += """
            <a href="/users">👥 Users</a>
            <a href="/assignments">🎲 Assign</a>
            <a href="/analytics">📈 Analytics</a>
        """

    links += """
        <a href="/meetings">🎥 Meetings</a>
        <a href="/logout">🚪 Logout</a>
    """

    return """
    <div class="navbar">
        <div><b>🏛️ Smart Monitoring & Inspection</b></div>
        <div>""" + links + """</div>
    </div>
    """ + notification_script()


# ============================================================
# LANDING
# ============================================================

@app.route("/")
def landing():

    return STYLE + """
    <div class="navbar">
        <b>🏛️ Smart Monitoring & Inspection System</b>
        <div>
            <a href="/login">🔐 Login</a>
        </div>
    </div>

    <div class="hero">
        <h1>🏛️ Smart Real-Time Monitoring & Inspection System</h1>

        <p>
            Smart inspection assignments, evidence reporting,
            priority monitoring and team coordination.
        </p>

        <br>

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
             style="max-width:500px;margin:60px auto;">

            <h1 style="text-align:center;">
                🔐 System Login
            </h1>

            <form method="POST">

                <label>🆔 Unique ID</label>
                <input type="text" name="unique_id" required>

                <label>🔑 Password</label>
                <input type="password" name="password" required>

                <button class="btn"
                        style="width:100%;"
                        type="submit">
                    Login
                </button>

            </form>

            <p style="color:red;">{error}</p>

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

    if role == "Authority":

        work_info = """
        👑 <b>Authority Responsibilities:</b><br><br>
        • Manage Workers and Inspectors<br>
        • Randomly assign inspections<br>
        • Monitor all inspection reports<br>
        • Track High, Medium and Low priority locations<br>
        • Create team meetings
        """

        buttons = """
        <a class="btn" href="/dashboard">📊 Monitor Dashboard</a>
        <a class="btn btn-purple" href="/assignments">🎲 Assign Inspection</a>
        <a class="btn btn-green" href="/meetings">🎥 Create Meeting</a>
        """

    else:

        work_info = """
        👷 <b>Your Responsibilities:</b><br><br>
        • View only your assigned inspections<br>
        • Conduct field inspection<br>
        • Submit evidence and issue reports<br>
        • Attend team meetings
        """

        buttons = """
        <a class="btn btn-purple"
           href="/my-assignments">
           📋 View My Assignments
        </a>

        <a class="btn btn-green"
           href="/meetings">
           🎥 View Meetings
        </a>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card" style="text-align:center;">

            <h1>Welcome, {session["name"]}! 👋</h1>

            <p>
                Role:
                <span class="badge">{role}</span>
            </p>

            <div class="info">
                {work_info}
            </div>

            {buttons}

        </div>

    </div>
    """


# ============================================================
# USER MANAGEMENT - AUTHORITY ONLY
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

        prefix = {
            "Worker": "WORK",
            "Inspector": "INS",
            "Authority": "AUTH"
        }

        unique_id = (
            prefix[role]
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
            🆔 <b>ID: {unique_id}</b><br>
            👤 <b>Name: {name}</b><br>
            🏷️ <b>Role: {role}</b>
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
                </select>

                <button class="btn btn-purple">
                    ➕ Create User
                </button>

            </form>

        </div>

        <div class="card">

            <h2>Registered Users</h2>

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
# RANDOM INSPECTION ASSIGNMENT
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
                🎲 <b>Random Inspection Assigned!</b><br><br>
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

            {message}

            <form method="POST">

                <label>📍 Location to Inspect</label>

                <input name="location"
                       placeholder="Enter inspection location"
                       required>

                <button class="btn btn-purple">
                    🎲 Randomly Assign Worker/Inspector
                </button>

            </form>

        </div>

        <div class="card">

            <h2>📋 Assignment History</h2>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Assigned To</th>
                    <th>Time</th>
                    <th>Status</th>
                </tr>
                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# MY ASSIGNMENTS - OWN WORK ONLY
# ============================================================

@app.route("/my-assignments")
def my_assignments():

    if not require_login():
        return redirect(url_for("login"))

    if session["role"] not in ["Worker", "Inspector"]:
        return "⛔ Access Denied.", 403

    conn = get_connection()

    assignments_list = conn.execute("""
        SELECT *
        FROM assignments
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    rows = ""

    for assignment in assignments_list:

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
            <td>{assignment["assigned_at"]}</td>
            <td>{assignment["status"]}</td>
            <td>{action}</td>
        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="4" style="text-align:center;">
                📭 No assignments available.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📋 My Assigned Inspections</h1>

            <div class="info">
                🔒 You can only access inspections assigned to you.
            </div>

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
    """


# ============================================================
# CONDUCT INSPECTION
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
        return "⛔ You cannot access this inspection.", 403

    if request.method == "POST":

        location = assignment["location"]

        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]

        description = request.form.get(
            "description",
            ""
        ).strip()

        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")

        # Save photo
        photo_name = None
        photo = request.files.get("photo")

        if photo and photo.filename and allowed_file(photo.filename):

            filename = secure_filename(photo.filename)
            extension = filename.rsplit(".", 1)[1].lower()

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

        # Find issues
        detected_issues = []

        if cleanliness == "No":
            detected_issues.append("Cleanliness Issue")

        if safety == "No":
            detected_issues.append("Safety Issue")

        if facilities == "No":
            detected_issues.append("Facility Issue")

        # Save each detected issue
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

        conn.execute("""
            UPDATE assignments
            SET status = 'Completed'
            WHERE id = ?
            AND user_id = ?
        """, (
            assignment_id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()

    # IMPORTANT:
    # JavaScript is added using string concatenation below,
    # avoiding f-string brace errors.

    page = f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>🔍 Field Inspection</h1>

            <div class="info">
                📍 Assigned Location:
                <b>{assignment["location"]}</b><br><br>

                👷 Inspector:
                <b>{session["name"]}</b>
            </div>

            <form method="POST"
                  enctype="multipart/form-data">

                <label>🧹 Is the area clean?</label>

                <select name="cleanliness">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">No ❌ - Issue Found</option>
                </select>

                <label>🛡️ Is the area safe?</label>

                <select name="safety">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">No ❌ - Issue Found</option>
                </select>

                <label>🏢 Are facilities working properly?</label>

                <select name="facilities">
                    <option value="Yes">Yes ✅</option>
                    <option value="No">No ❌ - Issue Found</option>
                </select>

                <label>📸 Upload Photo Evidence</label>

                <input type="file"
                       name="photo"
                       accept="image/*">

                <label>📍 GPS Location (Optional)</label>

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

                <label>📝 Inspection Description</label>

                <textarea name="description"
                          placeholder="Describe issues or observations..."></textarea>

                <br>

                <button class="btn"
                        type="submit">
                    📤 Submit Inspection
                </button>

            </form>

        </div>

    </div>
    """

    # NOT an f-string → JavaScript braces are safe
    gps_script = """
    <script>

    function getLocation() {

        if (navigator.geolocation) {

            navigator.geolocation.getCurrentPosition(

                function(position) {

                    document.getElementById("latitude").value =
                        position.coords.latitude;

                    document.getElementById("longitude").value =
                        position.coords.longitude;

                    alert("✅ Location captured successfully!");

                },

                function() {

                    alert(
                        "❌ Please allow location permission."
                    );

                }
            );

        } else {

            alert(
                "❌ Geolocation is not supported by your browser."
            );
        }
    }

    </script>
    """

    return page + gps_script


# ============================================================
# UPLOADS
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

        # Worker / Inspector sees ONLY their reports
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

            photo_html = f"""
            <img class="evidence-photo"
                 src="/uploads/{issue["photo"]}"
                 alt="Evidence">
            """

        rows += f"""
        <tr>
            <td>{issue["location"]}</td>
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
            <td colspan="6" style="text-align:center;">
                🎉 No issues reported yet.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <h1>📊 Monitoring Dashboard</h1>

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
                <div class="stat-number">{high}</div>
                <p>🚨 High Priority</p>
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
# ANALYTICS - AUTHORITY ONLY
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

            <h1>📈 Authority Analytics</h1>

            <div class="info">
                Priority Rules:<br>
                🟢 Low = 1 Report<br>
                🟡 Medium = 2–3 Reports<br>
                🔴 High = More than 3 Reports
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
# LATEST MEETING API
# ============================================================

@app.route("/api/latest-meeting")
def latest_meeting():

    if not require_login():

        return jsonify({
            "meeting": None
        })

    conn = get_connection()

    meeting = conn.execute("""
        SELECT
            meetings.*,
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

    # Only Authority creates meetings
    if request.method == "POST":

        if session["role"] != "Authority":

            conn.close()
            return "⛔ Only Authority can create meetings.", 403

        title = request.form["title"].strip()

        # Random unique meeting code
        meeting_code = uuid.uuid4().hex[:12].upper()

        # Random internal meeting link
        meeting_url = url_for(
            "meeting_room",
            meeting_code=meeting_code
        )

        conn.execute("""
            INSERT INTO meetings
            (
                title,
                meeting_code,
                meeting_url,
                created_at,
                created_by
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            meeting_code,
            meeting_url,
            current_time(),
            session["user_id"]
        ))

        conn.commit()

        message = """
        <div class="info">
            🔔 <b>Meeting Created Successfully!</b><br><br>
            Workers and Inspectors will receive a popup
            notification when they are active on the website.
        </div>
        """

    meetings_list = conn.execute("""
        SELECT meetings.*, users.name AS authority_name
        FROM meetings
        LEFT JOIN users
        ON meetings.created_by = users.id
        ORDER BY meetings.id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for meeting in meetings_list:

        creator = (
            meeting["authority_name"]
            or "Authority"
        )

        rows += f"""
        <tr>
            <td>{meeting["title"]}</td>
            <td>{creator}</td>
            <td>{meeting["created_at"]}</td>
            <td>
                <a class="btn btn-purple"
                   href="{meeting["meeting_url"]}">
                   🎥 Join Meeting
                </a>
            </td>
        </tr>
        """

    create_form = ""

    if session["role"] == "Authority":

        create_form = """
        <div class="card">

            <h1>🎥 Create Team Meeting</h1>

            <div class="info">
                🔗 A random unique meeting link will be generated
                automatically.
                <br><br>
                🔔 Active Workers and Inspectors will receive
                a popup notification.
            </div>

            <form method="POST">

                <label>Meeting Title</label>

                <input name="title"
                       placeholder="Example: Inspection Review"
                       required>

                <button class="btn btn-purple">
                    🔔 Create Meeting & Notify Team
                </button>

            </form>

        </div>
        """

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        {message}

        {create_form}

        <div class="card">

            <h2>🎥 Available Meetings</h2>

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
        SELECT *
        FROM meetings
        WHERE meeting_code = ?
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
        SELECT users.name, users.role
        FROM meeting_participants
        JOIN users
        ON meeting_participants.user_id = users.id
        WHERE meeting_participants.meeting_id = ?
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

        <div class="card" style="text-align:center;">

            <h1>🎥 Smart Inspection Meeting Room</h1>

            <div class="info">

                🟢 <b>You successfully joined the meeting!</b>

                <br><br>

                🎥 Meeting:
                <b>{meeting["title"]}</b>

                <br><br>

                👤 Joined as:
                <b>{session["name"]}</b>
                ({session["role"]})

            </div>

            <a class="btn"
               href="/meetings">
               ← Back to Meetings
            </a>

        </div>

        <div class="card">

            <h2>👥 Participants</h2>

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
    print("Smart Monitoring & Inspection System Starting...")
    print("Open: http://127.0.0.1:5000")
    print("=" * 60)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
