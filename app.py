from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    send_from_directory,
    jsonify
)
import sqlite3
from datetime import datetime
import uuid
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = "smart_inspection_secret_2026_change_in_production"

DATABASE = "inspection.db"
UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

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
# DATABASE SETUP
# ============================================================

def create_database():
    conn = get_connection()

    # ---------------- USERS ----------------
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

    # ---------------- INSPECTION TASKS ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inspection_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            instructions TEXT,
            assigned_to INTEGER NOT NULL,
            assigned_by INTEGER NOT NULL,
            status TEXT DEFAULT 'Assigned',
            created_at TEXT NOT NULL,
            FOREIGN KEY (assigned_to) REFERENCES users(id),
            FOREIGN KEY (assigned_by) REFERENCES users(id)
        )
    """)

    # ---------------- INSPECTION REPORTS ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inspection_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            worker_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            cleanliness TEXT,
            safety TEXT,
            facilities TEXT,
            description TEXT,
            image_filename TEXT,
            status TEXT DEFAULT 'Submitted',
            inspector_status TEXT DEFAULT 'Pending Review',
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES inspection_tasks(id),
            FOREIGN KEY (worker_id) REFERENCES users(id)
        )
    """)

    # ---------------- ISSUES ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            location TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            description TEXT,
            image_filename TEXT,
            status TEXT DEFAULT 'Reported',
            created_at TEXT NOT NULL
        )
    """)

    # ---------------- MEETINGS ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            meeting_link TEXT UNIQUE NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)

    # ---------------- NOTIFICATIONS ----------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ========================================================
    # DEFAULT AUTHORITY
    # ========================================================

    admin = conn.execute(
        "SELECT id FROM users WHERE unique_id = ?",
        ("ADMIN001",)
    ).fetchone()

    if admin is None:
        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "ADMIN001",
            "System Administrator",
            generate_password_hash("admin123"),
            "Authority",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    # ========================================================
    # DEFAULT INSPECTOR
    # ========================================================

    inspector = conn.execute(
        "SELECT id FROM users WHERE unique_id = ?",
        ("INS001",)
    ).fetchone()

    if inspector is None:
        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "INS001",
            "Demo Inspector",
            generate_password_hash("inspector123"),
            "Inspector",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    # ========================================================
    # DEFAULT WORKER
    # ========================================================

    worker = conn.execute(
        "SELECT id FROM users WHERE unique_id = ?",
        ("WORK001",)
    ).fetchone()

    if worker is None:
        conn.execute("""
            INSERT INTO users
            (unique_id, name, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "WORK001",
            "Demo Worker",
            generate_password_hash("worker123"),
            "Worker",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    conn.commit()
    conn.close()


create_database()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def logged_in():
    return "user_id" in session


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def generate_unique_id(role):
    prefixes = {
        "Authority": "AUTH",
        "Officer": "OFF",
        "Inspector": "INS",
        "Worker": "WORK"
    }

    return prefixes[role] + uuid.uuid4().hex[:6].upper()


def create_notification(user_id, message, link=""):
    conn = get_connection()

    conn.execute("""
        INSERT INTO notifications
        (user_id, message, link, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        message,
        link,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


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
    background: linear-gradient(135deg, #eff6ff, #eef2ff, #f0fdfa);
    color: #1e293b;
}

.navbar {
    background: linear-gradient(90deg, #172554, #2563eb);
    color: white;
    padding: 16px 5%;
    box-shadow: 0 4px 15px rgba(0,0,0,0.15);
}

.navbar a {
    color: white;
    text-decoration: none;
    margin-left: 16px;
    font-weight: bold;
}

.container {
    max-width: 1200px;
    margin: 30px auto;
    padding: 20px;
}

.card {
    background: white;
    padding: 25px;
    border-radius: 18px;
    margin-bottom: 22px;
    box-shadow: 0 8px 25px rgba(30,58,138,0.10);
}

.hero {
    text-align: center;
}

h1, h2 {
    color: #1e3a8a;
}

.btn {
    display: inline-block;
    background: #2563eb;
    color: white;
    padding: 11px 17px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    text-decoration: none;
    margin: 4px;
    font-size: 14px;
}

.btn:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

.btn-green {
    background: #059669;
}

.btn-orange {
    background: #ea580c;
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
    margin-top: 6px;
    margin-bottom: 15px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
}

textarea {
    min-height: 100px;
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

.badge {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 20px;
    background: #e0e7ff;
    font-size: 13px;
    font-weight: bold;
}

.info {
    background: #eff6ff;
    border-left: 5px solid #2563eb;
    padding: 15px;
    margin: 15px 0;
    border-radius: 8px;
}

.success {
    background: #ecfdf5;
    border-left: 5px solid #059669;
    padding: 15px;
    margin: 15px 0;
    border-radius: 8px;
}

.warning {
    background: #fff7ed;
    border-left: 5px solid #ea580c;
    padding: 15px;
    margin: 15px 0;
    border-radius: 8px;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 15px;
    margin-bottom: 25px;
}

.stat-card {
    background: white;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 5px 20px rgba(0,0,0,0.08);
}

.stat-number {
    font-size: 32px;
    font-weight: bold;
    color: #2563eb;
}

.popup {
    display: none;
    position: fixed;
    right: 25px;
    bottom: 25px;
    width: 340px;
    background: white;
    border-radius: 15px;
    padding: 20px;
    z-index: 9999;
    box-shadow: 0 10px 40px rgba(0,0,0,0.25);
    border-left: 6px solid #2563eb;
}

.popup h3 {
    margin-top: 0;
    color: #1e3a8a;
}

.image-preview {
    max-width: 150px;
    max-height: 100px;
    border-radius: 8px;
}

@media (max-width: 800px) {

    .navbar a {
        display: inline-block;
        margin: 8px 5px;
    }

    .container {
        padding: 10px;
    }

    table {
        font-size: 12px;
    }
}

</style>
"""


# ============================================================
# NAVIGATION BAR
# ============================================================

def navbar():

    if not logged_in():
        return ""

    role = session["role"]

    links = """
        <a href="/home">🏠 Home</a>
        <a href="/dashboard">📊 Dashboard</a>
    """

    if role == "Authority":
        links += """
            <a href="/users">👥 Users</a>
            <a href="/assign">📋 Assign</a>
            <a href="/analytics">📈 Analytics</a>
            <a href="/cctv">📹 CCTV</a>
            <a href="/meetings">📹 Meetings</a>
        """

    elif role == "Inspector":
        links += """
            <a href="/review-reports">🔍 Review Reports</a>
            <a href="/meetings">📹 Meetings</a>
        """

    elif role == "Worker":
        links += """
            <a href="/my-tasks">📋 My Work</a>
            <a href="/meetings">📹 Meetings</a>
        """

    else:
        links += """
            <a href="/analytics">📈 Analytics</a>
            <a href="/meetings">📹 Meetings</a>
        """

    links += """
        <a href="/logout">🚪 Logout</a>
    """

    return f"""
    <div class="navbar">
        <b>🏛️ Smart Inspection System</b>
        <span style="float:right;">
            {links}
        </span>
    </div>
    """


# ============================================================
# NOTIFICATION POPUP SCRIPT
# ============================================================

NOTIFICATION_SCRIPT = """
<div class="popup" id="notificationPopup">
    <h3>🔔 New Notification</h3>
    <p id="notificationMessage"></p>
    <a id="notificationLink" class="btn btn-green">
        View / Join
    </a>
    <button class="btn" onclick="closeNotification()">
        Close
    </button>
</div>

<script>

let lastNotificationId = 0;

function checkNotifications() {

    fetch("/notifications-api")
        .then(response => response.json())
        .then(data => {

            if (data.notification) {

                const notification = data.notification;

                if (notification.id > lastNotificationId) {

                    lastNotificationId = notification.id;

                    document.getElementById(
                        "notificationMessage"
                    ).innerText = notification.message;

                    document.getElementById(
                        "notificationLink"
                    ).href = notification.link || "/meetings";

                    document.getElementById(
                        "notificationPopup"
                    ).style.display = "block";
                }
            }
        })
        .catch(error => console.log(error));
}

function closeNotification() {
    document.getElementById(
        "notificationPopup"
    ).style.display = "none";
}

setInterval(checkNotifications, 5000);

</script>
"""


# ============================================================
# LOGIN
# ============================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if logged_in():
        return redirect(url_for("home"))

    error = ""

    if request.method == "POST":

        unique_id = request.form["unique_id"].strip()
        password = request.form["password"]

        conn = get_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE unique_id = ?",
            (unique_id,)
        ).fetchone()

        conn.close()

        if (
            user is not None
            and check_password_hash(
                user["password"],
                password
            )
        ):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        error = "❌ Invalid Unique ID or Password!"

    return f"""
    {STYLE}

    <div class="container">

        <div class="card hero"
             style="max-width:500px; margin:70px auto;">

            <h1>🏛️ Smart Inspection & Monitoring</h1>

            <p>
                Digital Inspection • Monitoring • Issue Management
            </p>

            <div class="info">
                🔐 Secure Role-Based Access System
            </div>

            <form method="POST" style="text-align:left;">

                <label>🆔 Unique ID</label>
                <input type="text"
                       name="unique_id"
                       required>

                <label>🔑 Password</label>
                <input type="password"
                       name="password"
                       required>

                <button class="btn" type="submit">
                    🔐 Login
                </button>

            </form>

            <p style="color:red;">{error}</p>

            <div class="info">
                <b>Authority:</b> ADMIN001 / admin123<br>
                <b>Inspector:</b> INS001 / inspector123<br>
                <b>Worker:</b> WORK001 / worker123
            </div>

        </div>

    </div>
    """


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ============================================================
# HOME
# ============================================================

@app.route("/home")
def home():

    if not logged_in():
        return redirect(url_for("login"))

    role = session["role"]
    name = session["name"]

    role_description = {
        "Authority":
            "Manage the complete system, assign inspections, "
            "verify activities and conduct meetings.",

        "Officer":
            "Monitor inspection activities and view system progress.",

        "Inspector":
            "Review submitted field reports and professionally "
            "verify inspection findings.",

        "Worker":
            "Complete assigned field inspections and upload "
            "evidence images."
    }

    return f"""
    {STYLE}
    {navbar()}
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <div class="card hero">

            <h1>
                Welcome, {name}! 👋
            </h1>

            <p>
                Role:
                <span class="badge">{role}</span>
            </p>

            <div class="info">
                <b>Your Responsibility:</b><br><br>
                {role_description.get(role, "")}
            </div>

        </div>

        <div class="card">

            <h2>🎯 Smart System Workflow</h2>

            <p style="font-size:17px;">
                👨‍💼 Authority assigns inspection
                →
                👷 Worker conducts field inspection
                →
                📷 Uploads evidence
                →
                🔍 Inspector verifies report
                →
                📊 Officer & Authority monitor progress
                →
                ✅ Issue resolved
            </p>

        </div>

    </div>
    """


# ============================================================
# USER MANAGEMENT - AUTHORITY ONLY
# ============================================================

@app.route("/users", methods=["GET", "POST"])
def users():

    if (
        not logged_in()
        or session["role"] != "Authority"
    ):
        return "⛔ Access Denied."

    message = ""

    if request.method == "POST":

        name = request.form["name"].strip()
        password = request.form["password"]
        role = request.form["role"]

        unique_id = generate_unique_id(role)

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
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

        message = f"""
        <div class="success">
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
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <div class="card">

            <h1>👥 User Management</h1>

            {message}

            <form method="POST">

                <label>Full Name</label>
                <input type="text" name="name" required>

                <label>Password</label>
                <input type="password" name="password" required>

                <label>Role</label>

                <select name="role">
                    <option value="Authority">Authority</option>
                    <option value="Officer">Officer</option>
                    <option value="Inspector">Inspector</option>
                    <option value="Worker">Worker</option>
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
                    <th>Unique ID</th>
                    <th>Name</th>
                    <th>Role</th>
                </tr>
                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# ASSIGN INSPECTION - AUTHORITY ONLY
# ============================================================

@app.route("/assign", methods=["GET", "POST"])
def assign():

    if (
        not logged_in()
        or session["role"] != "Authority"
    ):
        return "⛔ Access Denied."

    conn = get_connection()

    workers = conn.execute("""
        SELECT id, name, unique_id
        FROM users
        WHERE role = 'Worker'
    """).fetchall()

    message = ""

    if request.method == "POST":

        location = request.form["location"].strip()
        instructions = request.form["instructions"].strip()
        worker_id = request.form["worker_id"]

        conn.execute("""
            INSERT INTO inspection_tasks
            (location, instructions, assigned_to,
             assigned_by, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            location,
            instructions,
            worker_id,
            session["user_id"],
            "Assigned",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

        create_notification(
            worker_id,
            f"📋 New inspection work assigned at {location}",
            "/my-tasks"
        )

        message = """
        <div class="success">
            ✅ Inspection work assigned successfully!
        </div>
        """

    conn.close()

    options = ""

    for worker in workers:
        options += f"""
        <option value="{worker["id"]}">
            {worker["name"]} ({worker["unique_id"]})
        </option>
        """

    return f"""
    {STYLE}
    {navbar()}
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <div class="card">

            <h1>📋 Assign Inspection Work</h1>

            <p>
                Assign field inspection tasks to Workers.
            </p>

            {message}

            <form method="POST">

                <label>📍 Inspection Location</label>
                <input type="text"
                       name="location"
                       required>

                <label>👷 Assign to Worker</label>

                <select name="worker_id" required>
                    {options}
                </select>

                <label>📝 Instructions</label>

                <textarea
                    name="instructions"
                    placeholder="Explain what the worker should inspect..."
                ></textarea>

                <button class="btn btn-orange">
                    📤 Assign Inspection
                </button>

            </form>

        </div>

    </div>
    """


# ============================================================
# WORKER TASKS AND INSPECTION FORM
# ============================================================

@app.route("/my-tasks")
def my_tasks():

    if (
        not logged_in()
        or session["role"] != "Worker"
    ):
        return "⛔ Only Workers can access assigned work."

    conn = get_connection()

    tasks = conn.execute("""
        SELECT *
        FROM inspection_tasks
        WHERE assigned_to = ?
        ORDER BY id DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    rows = ""

    for task in tasks:

        if task["status"] == "Assigned":

            action = f"""
            <a class="btn"
               href="/conduct-inspection/{task["id"]}">
                📋 Conduct Inspection
            </a>
            """

        else:
            action = "✅ Submitted"

        rows += f"""
        <tr>
            <td>{task["location"]}</td>
            <td>{task["instructions"] or "-"}</td>
            <td>{task["status"]}</td>
            <td>{action}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="4">
                No inspection work assigned yet.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <div class="card">

            <h1>👷 My Assigned Inspection Work</h1>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Instructions</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
                {rows}
            </table>

        </div>

    </div>
    """


# ============================================================
# WORKER CONDUCT INSPECTION WITH IMAGE
# ============================================================

@app.route(
    "/conduct-inspection/<int:task_id>",
    methods=["GET", "POST"]
)
def conduct_inspection(task_id):

    if (
        not logged_in()
        or session["role"] != "Worker"
    ):
        return "⛔ Only Workers can conduct this inspection."

    conn = get_connection()

    task = conn.execute("""
        SELECT *
        FROM inspection_tasks
        WHERE id = ?
        AND assigned_to = ?
    """, (
        task_id,
        session["user_id"]
    )).fetchone()

    if task is None:
        conn.close()
        return "❌ Inspection task not found."

    if request.method == "POST":

        cleanliness = request.form["cleanliness"]
        safety = request.form["safety"]
        facilities = request.form["facilities"]
        description = request.form["description"].strip()

        image_filename = ""

        image = request.files.get("image")

        if image and image.filename != "":

            if allowed_file(image.filename):

                filename = secure_filename(image.filename)

                image_filename = (
                    f"{uuid.uuid4().hex}_{filename}"
                )

                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        image_filename
                    )
                )

        cursor = conn.execute("""
            INSERT INTO inspection_reports
            (
                task_id,
                worker_id,
                location,
                cleanliness,
                safety,
                facilities,
                description,
                image_filename,
                status,
                inspector_status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            session["user_id"],
            task["location"],
            cleanliness,
            safety,
            facilities,
            description,
            image_filename,
            "Submitted",
            "Pending Review",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        report_id = cursor.lastrowid

        # Automatically create issues
        checks = {
            "Cleanliness": cleanliness,
            "Safety": safety,
            "Facilities": facilities
        }

        for issue_type, value in checks.items():

            if value == "No":

                conn.execute("""
                    INSERT INTO issues
                    (
                        report_id,
                        location,
                        issue_type,
                        description,
                        image_filename,
                        status,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id,
                    task["location"],
                    issue_type,
                    description,
                    image_filename,
                    "Reported",
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ))

        conn.execute("""
            UPDATE inspection_tasks
            SET status = 'Submitted'
            WHERE id = ?
        """, (task_id,))

        conn.commit()
        conn.close()

        return redirect(url_for("my_tasks"))

    conn.close()

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card">

            <h1>📋 Conduct Field Inspection</h1>

            <div class="info">
                📍 <b>Location:</b> {task["location"]}<br>
                📝 <b>Instructions:</b>
                {task["instructions"] or "General inspection"}
            </div>

            <form method="POST"
                  enctype="multipart/form-data">

                <label>🧹 Cleanliness</label>
                <select name="cleanliness">
                    <option value="Yes">Good ✅</option>
                    <option value="No">Issue Found ❌</option>
                </select>

                <label>🛡️ Safety</label>
                <select name="safety">
                    <option value="Yes">Good ✅</option>
                    <option value="No">Issue Found ❌</option>
                </select>

                <label>🏢 Facilities</label>
                <select name="facilities">
                    <option value="Yes">Good ✅</option>
                    <option value="No">Issue Found ❌</option>
                </select>

                <label>📷 Upload Evidence Image</label>
                <input type="file"
                       name="image"
                       accept="image/*">

                <label>📝 Inspection Description</label>
                <textarea
                    name="description"
                    placeholder="Describe your findings..."
                ></textarea>

                <button class="btn btn-green">
                    📤 Submit Inspection Report
                </button>

            </form>

        </div>

    </div>
    """


# ============================================================
# INSPECTOR REVIEWS WORKER REPORTS
# ============================================================

@app.route("/review-reports")
def review_reports():

    if (
        not logged_in()
        or session["role"] != "Inspector"
    ):
        return "⛔ Only Inspectors can review reports."

    conn = get_connection()

    reports = conn.execute("""
        SELECT
            inspection_reports.*,
            users.name AS worker_name
        FROM inspection_reports
        JOIN users
        ON inspection_reports.worker_id = users.id
        ORDER BY inspection_reports.id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for report in reports:

        image = "-"

        if report["image_filename"]:
            image = f"""
            <a href="/uploads/{report["image_filename"]}"
               target="_blank">
                📷 View Image
            </a>
            """

        rows += f"""
        <tr>
            <td>{report["location"]}</td>
            <td>{report["worker_name"]}</td>
            <td>{report["created_at"]}</td>
            <td>{report["inspector_status"]}</td>
            <td>{image}</td>
            <td>
                <a class="btn btn-green"
                   href="/verify-report/{report["id"]}/Verified">
                    ✅ Verify
                </a>
                <a class="btn btn-red"
                   href="/verify-report/{report["id"]}/Needs%20Review">
                    ⚠️ Review
                </a>
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <div class="card">

            <h1>🔍 Inspector Report Verification</h1>

            <p>
                Inspectors verify reports submitted by Workers.
            </p>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Worker</th>
                    <th>Submitted</th>
                    <th>Status</th>
                    <th>Evidence</th>
                    <th>Action</th>
                </tr>
                {rows}
            </table>

        </div>

    </div>
    """


@app.route(
    "/verify-report/<int:report_id>/<status>"
)
def verify_report(report_id, status):

    if (
        not logged_in()
        or session["role"] != "Inspector"
    ):
        return "⛔ Access Denied."

    if status not in ["Verified", "Needs Review"]:
        return "❌ Invalid status."

    conn = get_connection()

    conn.execute("""
        UPDATE inspection_reports
        SET inspector_status = ?
        WHERE id = ?
    """, (
        status,
        report_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("review_reports"))


# ============================================================
# DASHBOARD - AUTHORITY AND OFFICER
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not logged_in():
        return redirect(url_for("login"))

    conn = get_connection()

    issues = conn.execute("""
        SELECT *
        FROM issues
        ORDER BY id DESC
    """).fetchall()

    total = conn.execute(
        "SELECT COUNT(*) AS count FROM issues"
    ).fetchone()["count"]

    reported = conn.execute("""
        SELECT COUNT(*) AS count
        FROM issues
        WHERE status = 'Reported'
    """).fetchone()["count"]

    progress = conn.execute("""
        SELECT COUNT(*) AS count
        FROM issues
        WHERE status = 'In Progress'
    """).fetchone()["count"]

    resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM issues
        WHERE status = 'Resolved'
    """).fetchone()["count"]

    conn.close()

    rows = ""

    for issue in issues:

        action = "🔒 Monitoring Only"

        if session["role"] == "Authority":

            if issue["status"] == "Reported":

                action = f"""
                <a class="btn btn-orange"
                   href="/update-issue/{issue["id"]}/In%20Progress">
                    🟡 Start Action
                </a>
                """

            elif issue["status"] == "In Progress":

                action = f"""
                <a class="btn btn-green"
                   href="/update-issue/{issue["id"]}/Resolved">
                    🟢 Resolve
                </a>
                """

            else:
                action = "✅ Completed"

        image = "-"

        if issue["image_filename"]:
            image = f"""
            <a href="/uploads/{issue["image_filename"]}"
               target="_blank">
                📷 Evidence
            </a>
            """

        rows += f"""
        <tr>
            <td>{issue["location"]}</td>
            <td>{issue["issue_type"]}</td>
            <td>{image}</td>
            <td>{issue["created_at"]}</td>
            <td>
                <span class="badge">
                    {issue["status"]}
                </span>
            </td>
            <td>{action}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="6">
                🎉 No issues reported yet.
            </td>
        </tr>
        """

    return f"""
    {STYLE}
    {navbar()}
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <h1>📊 Smart Monitoring Dashboard</h1>

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

            <h2>🚨 Reported Issues</h2>

            <div style="overflow-x:auto;">

                <table>
                    <tr>
                        <th>Location</th>
                        <th>Issue</th>
                        <th>Evidence</th>
                        <th>Time</th>
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
# UPDATE ISSUE - AUTHORITY ONLY
# ============================================================

@app.route(
    "/update-issue/<int:issue_id>/<status>"
)
def update_issue(issue_id, status):

    if (
        not logged_in()
        or session["role"] != "Authority"
    ):
        return "⛔ Access Denied."

    if status not in [
        "Reported",
        "In Progress",
        "Resolved"
    ]:
        return "❌ Invalid status."

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
# ANALYTICS
# ============================================================

@app.route("/analytics")
def analytics():

    if not logged_in():
        return redirect(url_for("login"))

    conn = get_connection()

    reports = conn.execute(
        "SELECT COUNT(*) AS count FROM inspection_reports"
    ).fetchone()["count"]

    verified = conn.execute("""
        SELECT COUNT(*) AS count
        FROM inspection_reports
        WHERE inspector_status = 'Verified'
    """).fetchone()["count"]

    tasks = conn.execute(
        "SELECT COUNT(*) AS count FROM inspection_tasks"
    ).fetchone()["count"]

    completed = conn.execute("""
        SELECT COUNT(*) AS count
        FROM inspection_tasks
        WHERE status = 'Submitted'
    """).fetchone()["count"]

    conn.close()

    return f"""
    {STYLE}
    {navbar()}
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <h1>📈 System Analytics</h1>

        <div class="dashboard-grid">

            <div class="stat-card">
                <div class="stat-number">{tasks}</div>
                <p>📋 Total Assigned Tasks</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{completed}</div>
                <p>✅ Completed Tasks</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{reports}</div>
                <p>📄 Inspection Reports</p>
            </div>

            <div class="stat-card">
                <div class="stat-number">{verified}</div>
                <p>🔍 Verified Reports</p>
            </div>

        </div>

        <div class="card">

            <h2>🎯 Performance Summary</h2>

            <p>
                This analytics section helps the organization
                monitor inspection activities, completed work,
                submitted reports and verified inspections.
            </p>

        </div>

    </div>
    """


# ============================================================
# CCTV INTERFACE
# ============================================================

@app.route("/cctv")
def cctv():

    if (
        not logged_in()
        or session["role"] != "Authority"
    ):
        return "⛔ CCTV access is restricted."

    return f"""
    {STYLE}
    {navbar()}
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <h1>📹 Smart CCTV Monitoring</h1>

        <div class="info">
            ℹ️ CCTV interface demonstration for the project.
            Real camera integration can be added in future.
        </div>

        <div class="dashboard-grid">

            <div class="card hero">
                <h2>📹 Camera 1</h2>
                <div style="
                    background:#1e293b;
                    color:white;
                    padding:60px 20px;
                    border-radius:10px;
                ">
                    🔴 LIVE CAMERA FEED<br><br>
                    Main Entrance
                </div>
            </div>

            <div class="card hero">
                <h2>📹 Camera 2</h2>
                <div style="
                    background:#1e293b;
                    color:white;
                    padding:60px 20px;
                    border-radius:10px;
                ">
                    🔴 LIVE CAMERA FEED<br><br>
                    Block A
                </div>
            </div>

            <div class="card hero">
                <h2>📹 Camera 3</h2>
                <div style="
                    background:#1e293b;
                    color:white;
                    padding:60px 20px;
                    border-radius:10px;
                ">
                    🔴 LIVE CAMERA FEED<br><br>
                    Parking Area
                </div>
            </div>

        </div>

    </div>
    """


# ============================================================
# MEETINGS
# ============================================================

@app.route("/meetings", methods=["GET", "POST"])
def meetings():

    if not logged_in():
        return redirect(url_for("login"))

    message = ""

    # Only Authority can create a meeting
    if (
        request.method == "POST"
        and session["role"] == "Authority"
    ):

        title = request.form["title"].strip()
        description = request.form["description"].strip()

        meeting_link = (
            "/meeting-room/"
            + uuid.uuid4().hex[:12]
        )

        conn = get_connection()

        conn.execute("""
            INSERT INTO meetings
            (
                title,
                description,
                meeting_link,
                created_by,
                created_at,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title,
            description,
            meeting_link,
            session["user_id"],
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            1
        ))

        users = conn.execute("""
            SELECT id
            FROM users
            WHERE id != ?
        """, (
            session["user_id"],
        )).fetchall()

        conn.commit()
        conn.close()

        # Send notification to every user
        for user in users:

            create_notification(
                user["id"],
                f"📹 Meeting Started: {title}. "
                "Click to join now!",
                meeting_link
            )

        message = f"""
        <div class="success">
            🎉 Meeting created successfully!<br><br>
            Share this meeting link:<br>
            <b>{meeting_link}</b>
        </div>
        """

    conn = get_connection()

    meeting_list = conn.execute("""
        SELECT *
        FROM meetings
        WHERE active = 1
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    rows = ""

    for meeting in meeting_list:

        rows += f"""
        <div class="card">

            <h2>📹 {meeting["title"]}</h2>

            <p>
                {meeting["description"] or "Official meeting"}
            </p>

            <p>
                Created: {meeting["created_at"]}
            </p>

            <a class="btn btn-green"
               href="{meeting["meeting_link"]}">
                🔗 Join Meeting
            </a>

        </div>
        """

    create_form = ""

    if session["role"] == "Authority":

        create_form = """
        <div class="card">

            <h2>➕ Start a New Meeting</h2>

            <form method="POST">

                <label>Meeting Title</label>
                <input type="text"
                       name="title"
                       placeholder="Example: Weekly Inspection Review"
                       required>

                <label>Description</label>
                <textarea
                    name="description"
                    placeholder="Meeting agenda..."
                ></textarea>

                <button class="btn btn-purple">
                    📹 Start Meeting & Notify Team
                </button>

            </form>

        </div>
        """

    return f"""
    {STYLE}
    {navbar()}
    {NOTIFICATION_SCRIPT}

    <div class="container">

        <h1>📹 Team Meetings</h1>

        {message}

        {create_form}

        <h2>🔴 Active Meetings</h2>

        {rows or "<div class='info'>No active meetings.</div>"}

    </div>
    """


# ============================================================
# MEETING ROOM
# ============================================================

@app.route("/meeting-room/<meeting_code>")
def meeting_room(meeting_code):

    if not logged_in():
        return redirect(url_for("login"))

    return f"""
    {STYLE}
    {navbar()}

    <div class="container">

        <div class="card hero">

            <h1>📹 Smart Inspection Meeting Room</h1>

            <div style="
                background:#172554;
                color:white;
                padding:100px 20px;
                border-radius:15px;
                margin:20px 0;
            ">

                <h2 style="color:white;">
                    🎥 Meeting Room
                </h2>

                <p>
                    Welcome, {session["name"]}!
                </p>

                <p>
                    Meeting Code: {meeting_code}
                </p>

                <p>
                    🔊 Camera and video integration can be
                    connected using WebRTC or a meeting API.
                </p>

            </div>

            <a href="/meetings"
               class="btn btn-red">
                🚪 Leave Meeting
            </a>

        </div>

    </div>
    """


# ============================================================
# NOTIFICATION API
# ============================================================

@app.route("/notifications-api")
def notifications_api():

    if not logged_in():
        return jsonify({"notification": None})

    conn = get_connection()

    notification = conn.execute("""
        SELECT *
        FROM notifications
        WHERE user_id = ?
        AND is_read = 0
        ORDER BY id ASC
        LIMIT 1
    """, (
        session["user_id"],
    )).fetchone()

    if notification:

        data = {
            "id": notification["id"],
            "message": notification["message"],
            "link": notification["link"]
        }

        conn.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE id = ?
        """, (
            notification["id"],
        ))

        conn.commit()
        conn.close()

        return jsonify({"notification": data})

    conn.close()

    return jsonify({"notification": None})


# ============================================================
# SERVE UPLOADED IMAGES
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
