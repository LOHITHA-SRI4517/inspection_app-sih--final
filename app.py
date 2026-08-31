from flask import (
    Flask, request, redirect, url_for, session, jsonify,
    send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import sqlite3
import os
import uuid
import random
import base64
import re

# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key-in-production"
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "inspection.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def add_column_if_missing(conn, table, column, definition):
    columns = [
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    ]

    if column not in columns:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def init_db():
    conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'staff',
        face_image TEXT,
        face_registered INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT,
        incharge TEXT,
        cctv_url TEXT,
        status TEXT DEFAULT 'Active',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        inspector_id INTEGER,
        title TEXT,
        status TEXT DEFAULT 'Assigned',
        latitude TEXT,
        longitude TEXT,
        checklist TEXT,
        evidence TEXT,
        verification_photo TEXT,
        remarks TEXT,
        created_at TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(inspector_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_id INTEGER,
        project_id INTEGER,
        reported_by INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        severity TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Open',
        resolution TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        project_id INTEGER,
        latitude TEXT,
        longitude TEXT,
        photo TEXT,
        verification_status TEXT DEFAULT 'Captured',
        attendance_date TEXT,
        status TEXT DEFAULT 'Present'
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        title TEXT,
        meeting_url TEXT,
        meeting_time TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS face_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        photo TEXT,
        verification_status TEXT DEFAULT 'Captured',
        created_at TEXT
    );
    """)

    # Supports existing databases from older versions
    add_column_if_missing(conn, "users", "face_image", "TEXT")
    add_column_if_missing(
        conn, "users", "face_registered", "INTEGER DEFAULT 0"
    )
    add_column_if_missing(
        conn, "inspections", "verification_photo", "TEXT"
    )
    add_column_if_missing(
        conn, "attendance",
        "verification_status",
        "TEXT DEFAULT 'Captured'"
    )

    conn.commit()
    conn.close()


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") not in roles:
                return page(
                    "Access Denied",
                    "<div class='card danger'>"
                    "<h2>Access Denied</h2>"
                    "<p>You don't have permission to access this page.</p>"
                    "</div>"
                ), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def notify(user_id, message):
    conn = get_db()
    conn.execute("""
        INSERT INTO notifications(user_id, message, created_at)
        VALUES (?, ?, ?)
    """, (user_id, message, now()))
    conn.commit()
    conn.close()


def notify_role(role, message):
    conn = get_db()
    users = conn.execute(
        "SELECT id FROM users WHERE role=?",
        (role,)
    ).fetchall()
    conn.close()

    for user in users:
        notify(user["id"], message)


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_file(file):
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        return None

    ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


def save_camera_image(data_url):
    """Save image captured from browser camera."""

    if not data_url or "," not in data_url:
        return None

    try:
        header, encoded = data_url.split(",", 1)

        match = re.search(r"image/(png|jpeg|jpg|webp)", header.lower())
        ext = "jpg"

        if match:
            ext = match.group(1)
            if ext == "jpeg":
                ext = "jpg"

        image_data = base64.b64decode(encoded)
        filename = f"{uuid.uuid4().hex}.{ext}"

        path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        with open(path, "wb") as image_file:
            image_file.write(image_data)

        return filename

    except Exception:
        return None


# ============================================================
# BASE UI
# ============================================================

def page(title, content):
    user = session.get("name", "")
    role = session.get("role", "")

    nav = ""

    if session.get("user_id"):
        nav = f"""
        <div class="sidebar">
            <h2>🛡️ SmartInspect</h2>

            <div class="user">
                👤 {user}<br>
                <small>{role.upper()}</small>
            </div>

            <a href="/dashboard">📊 Dashboard</a>
            <a href="/projects">🏢 Projects</a>
            <a href="/inspections">📋 Inspections</a>
            <a href="/staff-report">🛠️ Staff Work</a>
            <a href="/attendance">👥 Attendance</a>
            <a href="/issues">⚠️ Issues</a>
            <a href="/meetings">🎥 Meetings</a>
            <a href="/notifications">
                🔔 Notifications
                <span id="notificationBadge"></span>
            </a>
            <a href="/analytics">📈 Analytics</a>
            <a href="/face-registration">📷 Face Security</a>
            <a href="/logout">🚪 Logout</a>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} | SmartInspect</title>
        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f4f7fb;
                color: #1e293b;
            }}

            .sidebar {{
                width: 240px;
                position: fixed;
                height: 100vh;
                overflow-y: auto;
                background: #0f172a;
                padding: 20px;
                color: white;
            }}

            .sidebar h2 {{
                color: #38bdf8;
            }}

            .sidebar a {{
                display: block;
                padding: 12px;
                margin: 5px 0;
                color: white;
                text-decoration: none;
                border-radius: 8px;
            }}

            .sidebar a:hover {{
                background: #1e293b;
            }}

            .user {{
                background: #1e293b;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 15px;
            }}

            .main {{
                margin-left: {"260px" if session.get("user_id") else "0"};
                padding: 30px;
                max-width: 1400px;
            }}

            .card {{
                background: white;
                padding: 20px;
                border-radius: 14px;
                box-shadow: 0 3px 12px rgba(0,0,0,.08);
                margin-bottom: 20px;
            }}

            .grid {{
                display: grid;
                grid-template-columns:
                    repeat(auto-fit, minmax(200px, 1fr));
                gap: 18px;
            }}

            .stat {{
                background: white;
                padding: 22px;
                border-radius: 14px;
                box-shadow: 0 3px 12px rgba(0,0,0,.08);
            }}

            input, select, textarea {{
                width: 100%;
                padding: 11px;
                margin: 7px 0 15px;
                border: 1px solid #cbd5e1;
                border-radius: 7px;
            }}

            button, .btn {{
                background: #2563eb;
                color: white;
                border: none;
                padding: 11px 18px;
                border-radius: 7px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin: 3px;
            }}

            button:hover, .btn:hover {{
                background: #1d4ed8;
            }}

            .secondary {{
                background: #475569;
            }}

            .success {{
                background: #dcfce7;
                padding: 12px;
                border-radius: 8px;
            }}

            .warning {{
                background: #fef3c7;
                padding: 12px;
                border-radius: 8px;
            }}

            .danger {{
                background: #fee2e2;
                padding: 12px;
                border-radius: 8px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}

            th, td {{
                padding: 12px;
                border-bottom: 1px solid #e2e8f0;
                text-align: left;
            }}

            th {{
                background: #eff6ff;
            }}

            .login {{
                max-width: 450px;
                margin: 70px auto;
            }}

            video, canvas, .camera-preview {{
                max-width: 100%;
                border-radius: 12px;
                margin: 10px 0;
            }}

            #notificationBadge {{
                background: #ef4444;
                border-radius: 50%;
                padding: 2px 7px;
                font-size: 12px;
            }}

            @media(max-width:700px) {{
                .sidebar {{
                    position: relative;
                    width: 100%;
                    height: auto;
                }}

                .main {{
                    margin-left: 0;
                    padding: 15px;
                }}
            }}
        </style>
    </head>

    <body>
        {nav}

        <div class="main">
            {content}
        </div>

        <script>
        async function checkNotifications() {{
            try {{
                const response =
                    await fetch('/api/notification-count');

                if (!response.ok) return;

                const data = await response.json();
                const badge =
                    document.getElementById('notificationBadge');

                if (badge && data.unread_notifications > 0) {{
                    badge.innerText = data.unread_notifications;
                }}
            }} catch (error) {{
                console.log("Notification check unavailable");
            }}
        }}

        checkNotifications();
        setInterval(checkNotifications, 30000);
        </script>
    </body>
    </html>
    """


# ============================================================
# FILE ACCESS
# ============================================================

@app.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# HOME / AUTHENTICATION
# ============================================================

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return page("Welcome", """
    <div class="login card">
        <h1>🛡️ SmartInspect</h1>
        <h3>Smart Real-Time Monitoring & Inspection System</h3>
        <p>
            Centralized monitoring, inspections, evidence,
            attendance and compliance management.
        </p>

        <a class="btn" href="/login">🔐 Login</a>
        <a class="btn secondary" href="/register">
            Register Organization
        </a>
    </div>
    """)


@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:
            message = (
                "<div class='danger'>"
                "Please enter valid details. Password must have "
                "at least 6 characters."
                "</div>"
            )
        else:
            conn = get_db()

            count = conn.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0]

            # First real account becomes Admin
            role = "admin" if count == 0 else "staff"

            try:
                conn.execute("""
                    INSERT INTO users(
                        name,email,password,role,created_at
                    )
                    VALUES(?,?,?,?,?)
                """, (
                    name,
                    email,
                    generate_password_hash(password),
                    role,
                    now()
                ))

                conn.commit()
                conn.close()

                return redirect(url_for("login"))

            except sqlite3.IntegrityError:
                conn.close()
                message = (
                    "<div class='danger'>"
                    "Email already registered."
                    "</div>"
                )

    return page("Register", f"""
    <div class="login card">
        <h2>Create Account</h2>
        {message}

        <form method="POST">
            <input name="name"
                   placeholder="Full Name"
                   required>

            <input type="email"
                   name="email"
                   placeholder="Official Email"
                   required>

            <input type="password"
                   name="password"
                   placeholder="Password (minimum 6 characters)"
                   required>

            <button>Create Account</button>
        </form>

        <p>
            Already registered?
            <a href="/login">Login</a>
        </p>
    </div>
    """)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute("""
            SELECT * FROM users WHERE email=?
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        error = (
            "<div class='danger'>"
            "Invalid email or password."
            "</div>"
        )

    return page("Login", f"""
    <div class="login card">
        <h2>🔐 Secure Login</h2>

        {error}

        <form method="POST">
            <input type="email"
                   name="email"
                   placeholder="Email"
                   required>

            <input type="password"
                   name="password"
                   placeholder="Password"
                   required>

            <button>Login</button>
        </form>

        <p>
            New organization?
            <a href="/register">Create an account</a>
        </p>
    </div>
    """)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ============================================================
# FACE REGISTRATION
# ============================================================

@app.route("/face-registration", methods=["GET", "POST"])
@login_required
def face_registration():

    if request.method == "POST":
        image_data = request.form.get("camera_image")
        filename = save_camera_image(image_data)

        if not filename:
            return page(
                "Face Registration",
                """
                <div class="card danger">
                    <h2>Camera capture failed</h2>
                    <a class="btn" href="/face-registration">
                        Try Again
                    </a>
                </div>
                """
            )

        conn = get_db()

        conn.execute("""
            UPDATE users
            SET face_image=?, face_registered=1
            WHERE id=?
        """, (filename, session["user_id"]))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return page("Face Registration", """
    <div class="card">
        <h1>📷 Face Registration</h1>

        <p>
            Register your identity photograph using your device camera.
            This image is used as a security identity record.
        </p>

        <div class="warning">
            ⚠️ Allow camera permission when your browser asks.
        </div><br>

        <video id="video" autoplay playsinline></video>
        <canvas id="canvas" style="display:none;"></canvas>

        <form method="POST" id="faceForm">
            <input type="hidden"
                   name="camera_image"
                   id="camera_image">

            <button type="button" onclick="startCamera()">
                📷 Start Camera
            </button>

            <button type="button" onclick="captureFace()">
                📸 Capture & Register Face
            </button>

            <button type="submit">
                ✅ Save Registration
            </button>
        </form>

        <p id="status"></p>
    </div>

    <script>
    let stream;

    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user" },
                audio: false
            });

            document.getElementById("video").srcObject = stream;
            document.getElementById("status").innerText =
                "✅ Camera is ready";

        } catch (error) {
            document.getElementById("status").innerText =
                "❌ Camera permission is required.";
        }
    }

    function captureFace() {
        const video = document.getElementById("video");
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

        document.getElementById("camera_image").value =
            canvas.toDataURL("image/jpeg", 0.9);

        document.getElementById("status").innerText =
            "✅ Face captured. Click Save Registration.";

        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    }
    </script>
    """)


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()

    projects = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE status='Active'"
    ).fetchone()[0]

    inspections = conn.execute(
        "SELECT COUNT(*) FROM inspections"
    ).fetchone()[0]

    open_issues = conn.execute("""
        SELECT COUNT(*) FROM issues
        WHERE status != 'Resolved'
    """).fetchone()[0]

    attendance_count = conn.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE attendance_date=?
    """, (today(),)).fetchone()[0]

    recent = conn.execute("""
        SELECT
            i.*,
            p.name AS project_name,
            u.name AS inspector_name
        FROM inspections i
        LEFT JOIN projects p ON p.id = i.project_id
        LEFT JOIN users u ON u.id = i.inspector_id
        ORDER BY i.id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    rows = ""

    for item in recent:
        rows += f"""
        <tr>
            <td>{item["title"] or "Inspection"}</td>
            <td>{item["project_name"] or "Not assigned"}</td>
            <td>{item["inspector_name"] or "Not assigned"}</td>
            <td>{item["status"]}</td>
        </tr>
        """

    return page("Dashboard", f"""
    <h1>📊 Real-Time Monitoring Dashboard</h1>

    <div class="grid">
        <div class="stat">
            <h2>{projects}</h2>
            🏢 Active Projects
        </div>

        <div class="stat">
            <h2>{inspections}</h2>
            📋 Total Inspections
        </div>

        <div class="stat">
            <h2>{open_issues}</h2>
            ⚠️ Open Issues
        </div>

        <div class="stat">
            <h2>{attendance_count}</h2>
            👥 Today's Attendance
        </div>
    </div>

    <div class="card">
        <h2>Recent Inspection Activity</h2>

        <table>
            <tr>
                <th>Inspection</th>
                <th>Project</th>
                <th>Inspector</th>
                <th>Status</th>
            </tr>

            {rows or
             "<tr><td colspan='4'>No inspections yet.</td></tr>"}
        </table>
    </div>
    """)


# ============================================================
# PROJECT MANAGEMENT
# ============================================================

@app.route("/projects", methods=["GET", "POST"])
@login_required
def projects():
    conn = get_db()

    if request.method == "POST":

        if session["role"] not in ["admin", "official"]:
            conn.close()
            return "Access Denied", 403

        conn.execute("""
            INSERT INTO projects(
                name,location,incharge,cctv_url,status,created_at
            )
            VALUES(?,?,?,?,?,?)
        """, (
            request.form.get("name"),
            request.form.get("location"),
            request.form.get("incharge"),
            request.form.get("cctv_url"),
            "Active",
            now()
        ))

        conn.commit()

    project_list = conn.execute("""
        SELECT * FROM projects ORDER BY id DESC
    """).fetchall()

    conn.close()

    form = ""

    if session["role"] in ["admin", "official"]:
        form = """
        <div class="card">
            <h2>➕ Add Project / Institute</h2>

            <form method="POST">
                <input name="name"
                       placeholder="Project / Institute Name"
                       required>

                <input name="location"
                       placeholder="Location">

                <input name="incharge"
                       placeholder="Project Incharge">

                <input name="cctv_url"
                       placeholder="CCTV / Monitoring URL">

                <button>Add Project</button>
            </form>
        </div>
        """

    rows = ""

    for project in project_list:

        cctv = "Not Connected"

        if project["cctv_url"]:
            cctv = (
                f"<a class='btn' target='_blank' "
                f"href='{project['cctv_url']}'>📹 View CCTV</a>"
            )

        rows += f"""
        <tr>
            <td>{project["name"]}</td>
            <td>{project["location"] or "-"}</td>
            <td>{project["incharge"] or "-"}</td>
            <td>{project["status"]}</td>
            <td>{cctv}</td>
        </tr>
        """

    return page("Projects", f"""
    <h1>🏢 Project & Institute Management</h1>

    {form}

    <div class="card">
        <table>
            <tr>
                <th>Name</th>
                <th>Location</th>
                <th>Incharge</th>
                <th>Status</th>
                <th>CCTV</th>
            </tr>

            {rows or
             "<tr><td colspan='5'>No projects available.</td></tr>"}
        </table>
    </div>
    """)


# ============================================================
# RANDOM INSPECTOR ASSIGNMENT
# ============================================================

@app.route("/assign-inspector", methods=["POST"])
@role_required("admin", "official")
def assign_inspector():

    project_id = request.form.get("project_id")
    title = request.form.get("title") or "Surprise Inspection"

    conn = get_db()

    inspectors = conn.execute("""
        SELECT * FROM users
        WHERE role IN ('inspector', 'official')
    """).fetchall()

    if not inspectors:
        conn.close()

        return page(
            "Inspector Assignment",
            """
            <div class="card warning">
                <h2>No Inspector Available</h2>
                <p>
                    An administrator must create or assign
                    an Inspector/Official account first.
                </p>
            </div>
            """
        )

    inspector = random.choice(inspectors)

    conn.execute("""
        INSERT INTO inspections(
            project_id,inspector_id,title,status,created_at
        )
        VALUES(?,?,?,?,?)
    """, (
        project_id,
        inspector["id"],
        title,
        "Assigned",
        now()
    ))

    conn.commit()
    conn.close()

    notify(
        inspector["id"],
        f"🎲 Security assignment: You have been assigned "
        f"to '{title}'. Please complete identity verification "
        f"before starting."
    )

    return redirect(url_for("inspections"))


# ============================================================
# INSPECTIONS
# ============================================================

@app.route("/inspections")
@login_required
def inspections():

    conn = get_db()

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

    if session["role"] in ["inspector", "staff"]:
        inspections_list = conn.execute("""
            SELECT
                i.*,
                p.name AS project_name,
                u.name AS inspector_name
            FROM inspections i
            LEFT JOIN projects p ON p.id=i.project_id
            LEFT JOIN users u ON u.id=i.inspector_id
            WHERE i.inspector_id=?
            ORDER BY i.id DESC
        """, (session["user_id"],)).fetchall()

    else:
        inspections_list = conn.execute("""
            SELECT
                i.*,
                p.name AS project_name,
                u.name AS inspector_name
            FROM inspections i
            LEFT JOIN projects p ON p.id=i.project_id
            LEFT JOIN users u ON u.id=i.inspector_id
            ORDER BY i.id DESC
        """).fetchall()

    conn.close()

    assignment_form = ""

    if session["role"] in ["admin", "official"]:

        options = "".join(
            f"<option value='{p['id']}'>{p['name']}</option>"
            for p in projects_list
        )

        assignment_form = f"""
        <div class="card">
            <h2>🎲 Random Inspector Assignment</h2>

            <form method="POST" action="/assign-inspector">
                <input name="title"
                       placeholder="Inspection Title"
                       required>

                <select name="project_id" required>
                    {options}
                </select>

                <button>
                    🎲 Randomly Assign Inspector
                </button>
            </form>
        </div>
        """

    cards = ""

    for inspection in inspections_list:

        if inspection["status"] == "Completed":
            cards += f"""
            <div class="card">
                <h3>📋 {inspection["title"]}</h3>
                <p>
                    <b>Project:</b>
                    {inspection["project_name"] or "-"}
                </p>
                <p>
                    <b>Inspector:</b>
                    {inspection["inspector_name"] or "-"}
                </p>
                <p class="success">✅ Completed</p>
            </div>
            """

        else:
            cards += f"""
            <div class="card">
                <h3>📋 {inspection["title"]}</h3>
                <p>
                    <b>Project:</b>
                    {inspection["project_name"] or "-"}
                </p>
                <p><b>Status:</b> {inspection["status"]}</p>

                <a class="btn"
                   href="/inspection-form/{inspection['id']}">
                    📋 Start Inspection
                </a>
            </div>
            """

    return page("Inspections", f"""
    <h1>📋 Digital Inspection Module</h1>

    {assignment_form}

    {cards or
     "<div class='card'>No inspections assigned yet.</div>"}
    """)


@app.route("/inspection-form/<int:inspection_id>",
           methods=["GET", "POST"])
@login_required
def inspection_form(inspection_id):

    conn = get_db()

    inspection = conn.execute("""
        SELECT * FROM inspections WHERE id=?
    """, (inspection_id,)).fetchone()

    if not inspection:
        conn.close()
        return "Inspection not found", 404

    if (
        session["role"] in ["inspector", "staff"] and
        inspection["inspector_id"] != session["user_id"]
    ):
        conn.close()
        return "Access Denied", 403

    if request.method == "POST":

        checklist = ", ".join(
            request.form.getlist("checklist")
        )

        evidence = save_file(
            request.files.get("evidence")
        )

        verification_photo = save_camera_image(
            request.form.get("verification_photo")
        )

        if not verification_photo:
            conn.close()

            return page(
                "Verification Required",
                """
                <div class="card danger">
                    <h2>📷 Identity Verification Required</h2>
                    <p>
                        Please capture your live camera photo
                        before submitting the inspection.
                    </p>
                </div>
                """
            )

        conn.execute("""
            UPDATE inspections
            SET
                status='Completed',
                latitude=?,
                longitude=?,
                checklist=?,
                evidence=?,
                verification_photo=?,
                remarks=?
            WHERE id=?
        """, (
            request.form.get("latitude"),
            request.form.get("longitude"),
            checklist,
            evidence,
            verification_photo,
            request.form.get("remarks"),
            inspection_id
        ))

        conn.execute("""
            INSERT INTO face_verifications(
                user_id,action,photo,verification_status,created_at
            )
            VALUES(?,?,?,?,?)
        """, (
            session["user_id"],
            "Inspection Submission",
            verification_photo,
            "Captured",
            now()
        ))

        conn.commit()
        conn.close()

        notify_role(
            "admin",
            "📋 An inspection report has been completed."
        )

        return redirect(url_for("inspections"))

    conn.close()

    return page("Inspection Form", f"""
    <div class="card">
        <h1>📋 Smart Inspection Form</h1>

        <form method="POST"
              enctype="multipart/form-data">

            <input type="hidden"
                   name="latitude"
                   id="latitude">

            <input type="hidden"
                   name="longitude"
                   id="longitude">

            <input type="hidden"
                   name="verification_photo"
                   id="verification_photo">

            <h3>📍 GPS Location</h3>

            <button type="button"
                    onclick="getLocation()">
                Capture Current Location
            </button>

            <p id="locationStatus"></p>

            <h3>📷 Identity Verification Capture</h3>

            <p>
                Capture a live photo before submitting
                this official inspection.
            </p>

            <video id="video"
                   autoplay
                   playsinline></video>

            <canvas id="canvas"
                    style="display:none;"></canvas>

            <br>

            <button type="button"
                    onclick="startCamera()">
                Start Camera
            </button>

            <button type="button"
                    onclick="captureVerification()">
                Capture Verification
            </button>

            <p id="faceStatus"></p>

            <h3>📋 Inspection Checklist</h3>

            <label>
                <input type="checkbox"
                       name="checklist"
                       value="Infrastructure Verified">
                Infrastructure Verified
            </label><br>

            <label>
                <input type="checkbox"
                       name="checklist"
                       value="Staff Available">
                Staff Available
            </label><br>

            <label>
                <input type="checkbox"
                       name="checklist"
                       value="Beneficiary Services Verified">
                Beneficiary Services Verified
            </label><br>

            <label>
                <input type="checkbox"
                       name="checklist"
                       value="Records Verified">
                Records Verified
            </label><br>

            <label>
                <input type="checkbox"
                       name="checklist"
                       value="Attendance Verified">
                Attendance Verified
            </label>

            <h3>📸 Photo Evidence</h3>
            <input type="file"
                   name="evidence"
                   accept="image/*">

            <h3>📝 Remarks</h3>
            <textarea name="remarks"
                      placeholder="Enter inspection observations"></textarea>

            <button type="submit">
                ✅ Submit Inspection Report
            </button>

        </form>
    </div>

    <script>
    let stream;

    async function startCamera() {{
        try {{
            stream = await navigator.mediaDevices.getUserMedia({{
                video: {{ facingMode: "user" }},
                audio: false
            }});

            document.getElementById("video").srcObject = stream;

        }} catch(error) {{
            document.getElementById("faceStatus").innerText =
                "❌ Camera permission is required.";
        }}
    }}

    function captureVerification() {{
        const video = document.getElementById("video");
        const canvas = document.getElementById("canvas");

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        canvas.getContext("2d").drawImage(
            video, 0, 0,
            canvas.width, canvas.height
        );

        document.getElementById("verification_photo").value =
            canvas.toDataURL("image/jpeg", 0.9);

        document.getElementById("faceStatus").innerText =
            "✅ Live verification photo captured.";

        if(stream) {{
            stream.getTracks().forEach(track => track.stop());
        }}
    }}

    function getLocation() {{
        if (!navigator.geolocation) {{
            document.getElementById("locationStatus").innerText =
                "❌ GPS is not supported by this browser.";
            return;
        }}

        navigator.geolocation.getCurrentPosition(
            function(position) {{
                document.getElementById("latitude").value =
                    position.coords.latitude;

                document.getElementById("longitude").value =
                    position.coords.longitude;

                document.getElementById("locationStatus").innerText =
                    "✅ GPS location captured successfully.";
            }},
            function() {{
                document.getElementById("locationStatus").innerText =
                    "⚠️ Unable to capture location.";
            }}
        );
    }}
    </script>
    """)


# ============================================================
# STAFF WORK / ISSUE REPORTING
# ============================================================

@app.route("/staff-report", methods=["GET", "POST"])
@login_required
def staff_report():

    if request.method == "POST":

        conn = get_db()

        conn.execute("""
            INSERT INTO issues(
                project_id,reported_by,title,description,
                severity,status,created_at
            )
            VALUES(?,?,?,?,?,?,?)
        """, (
            request.form.get("project_id") or None,
            session["user_id"],
            request.form.get("title"),
            request.form.get("description"),
            request.form.get("severity"),
            "Open",
            now()
        ))

        conn.commit()
        conn.close()

        notify_role(
            "admin",
            f"⚠️ New issue reported: "
            f"{request.form.get('title')}"
        )

        return redirect(url_for("issues"))

    conn = get_db()

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

    conn.close()

    options = "".join(
        f"<option value='{p['id']}'>{p['name']}</option>"
        for p in projects_list
    )

    return page("Staff Report", f"""
    <div class="card">
        <h1>🛠️ Project Staff Work & Issue Report</h1>

        <form method="POST">

            <select name="project_id">
                <option value="">Select Project (Optional)</option>
                {options}
            </select>

            <input name="title"
                   placeholder="Issue Title"
                   required>

            <select name="severity">
                <option>Low</option>
                <option selected>Medium</option>
                <option>High</option>
                <option>Critical</option>
            </select>

            <textarea name="description"
                      placeholder="Describe the issue"
                      required></textarea>

            <button>Submit Report</button>
        </form>
    </div>
    """)


# ============================================================
# ISSUE RESOLUTION
# ============================================================

@app.route("/issues", methods=["GET", "POST"])
@login_required
def issues():

    conn = get_db()

    if (
        request.method == "POST" and
        session["role"] in ["admin", "official", "inspector"]
    ):
        conn.execute("""
            UPDATE issues
            SET status='Resolved', resolution=?
            WHERE id=?
        """, (
            request.form.get("resolution"),
            request.form.get("issue_id")
        ))

        conn.commit()

    issue_list = conn.execute("""
        SELECT
            issues.*,
            users.name AS reporter_name
        FROM issues
        LEFT JOIN users
            ON users.id=issues.reported_by
        ORDER BY issues.id DESC
    """).fetchall()

    conn.close()

    html = "<h1>⚠️ Issue Verification & Resolution</h1>"

    for issue in issue_list:

        action = ""

        if (
            issue["status"] != "Resolved" and
            session["role"] in
            ["admin", "official", "inspector"]
        ):
            action = f"""
            <form method="POST">
                <input type="hidden"
                       name="issue_id"
                       value="{issue['id']}">

                <input name="resolution"
                       placeholder="Resolution details"
                       required>

                <button>Verify & Resolve</button>
            </form>
            """

        html += f"""
        <div class="card">
            <h3>
                {issue["title"]} — {issue["severity"]}
            </h3>

            <p>{issue["description"]}</p>
            <p>
                <b>Reported by:</b>
                {issue["reporter_name"] or "Unknown"}
            </p>
            <p><b>Status:</b> {issue["status"]}</p>

            {action}
        </div>
        """

    return page("Issues", html)


# ============================================================
# ATTENDANCE + GPS + CAMERA
# ============================================================

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():

    conn = get_db()

    if request.method == "POST":

        verification_photo = save_camera_image(
            request.form.get("camera_photo")
        )

        if not verification_photo:
            conn.close()
            return page(
                "Attendance",
                """
                <div class="card danger">
                    <h2>📷 Camera Verification Required</h2>
                    <p>
                        Capture a live identity photo before
                        marking attendance.
                    </p>
                </div>
                """
            )

        existing = conn.execute("""
            SELECT id FROM attendance
            WHERE user_id=? AND attendance_date=?
        """, (
            session["user_id"],
            today()
        )).fetchone()

        if existing:
            conn.close()
            return page(
                "Attendance",
                """
                <div class="card warning">
                    <h2>Attendance Already Marked</h2>
                    <p>You have already marked attendance today.</p>
                    <a class="btn" href="/attendance">Back</a>
                </div>
                """
            )

        conn.execute("""
            INSERT INTO attendance(
                user_id,project_id,latitude,longitude,
                photo,verification_status,
                attendance_date,status
            )
            VALUES(?,?,?,?,?,?,?,?)
        """, (
            session["user_id"],
            request.form.get("project_id") or None,
            request.form.get("latitude"),
            request.form.get("longitude"),
            verification_photo,
            "Live Photo Captured",
            today(),
            "Present"
        ))

        conn.execute("""
            INSERT INTO face_verifications(
                user_id,action,photo,verification_status,created_at
            )
            VALUES(?,?,?,?,?)
        """, (
            session["user_id"],
            "Attendance",
            verification_photo,
            "Captured",
            now()
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("attendance"))

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

    records = conn.execute("""
        SELECT
            a.*,
            u.name AS user_name,
            p.name AS project_name
        FROM attendance a
        LEFT JOIN users u ON u.id=a.user_id
        LEFT JOIN projects p ON p.id=a.project_id
        ORDER BY a.id DESC
        LIMIT 30
    """).fetchall()

    conn.close()

    options = "".join(
        f"<option value='{p['id']}'>{p['name']}</option>"
        for p in projects_list
    )

    rows = "".join(f"""
    <tr>
        <td>{r["user_name"]}</td>
        <td>{r["project_name"] or "-"}</td>
        <td>{r["attendance_date"]}</td>
        <td>{r["status"]}</td>
        <td>{r["verification_status"]}</td>
    </tr>
    """ for r in records)

    return page("Attendance", f"""
    <h1>👥 Smart Attendance Management</h1>

    <div class="card">
        <form method="POST">

            <select name="project_id">
                <option value="">Select Project</option>
                {options}
            </select>

            <input type="hidden"
                   id="alatitude"
                   name="latitude">

            <input type="hidden"
                   id="alongitude"
                   name="longitude">

            <input type="hidden"
                   id="camera_photo"
                   name="camera_photo">

            <button type="button"
                    onclick="attendanceLocation()">
                📍 Capture GPS
            </button>

            <p id="attendanceStatus"></p>

            <h3>📷 Live Identity Capture</h3>

            <video id="video"
                   autoplay
                   playsinline></video>

            <canvas id="canvas"
                    style="display:none;"></canvas>

            <br>

            <button type="button"
                    onclick="startAttendanceCamera()">
                Start Camera
            </button>

            <button type="button"
                    onclick="captureAttendance()">
                Capture Identity
            </button>

            <p id="cameraStatus"></p>

            <button type="submit">
                ✅ Mark Attendance
            </button>

        </form>
    </div>

    <div class="card">
        <table>
            <tr>
                <th>User</th>
                <th>Project</th>
                <th>Date</th>
                <th>Status</th>
                <th>Verification</th>
            </tr>
            {rows or
             "<tr><td colspan='5'>No attendance records.</td></tr>"}
        </table>
    </div>

    <script>
    let attendanceStream;

    async function startAttendanceCamera() {{
        try {{
            attendanceStream =
                await navigator.mediaDevices.getUserMedia({{
                    video: {{ facingMode: "user" }},
                    audio: false
                }});

            document.getElementById("video").srcObject =
                attendanceStream;

        }} catch(error) {{
            document.getElementById("cameraStatus").innerText =
                "❌ Camera permission required.";
        }}
    }}

    function captureAttendance() {{
        const video = document.getElementById("video");
        const canvas = document.getElementById("canvas");

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        canvas.getContext("2d").drawImage(
            video, 0, 0,
            canvas.width, canvas.height
        );

        document.getElementById("camera_photo").value =
            canvas.toDataURL("image/jpeg", 0.9);

        document.getElementById("cameraStatus").innerText =
            "✅ Identity photo captured.";

        if(attendanceStream) {{
            attendanceStream.getTracks().forEach(
                track => track.stop()
            );
        }}
    }}

    function attendanceLocation() {{
        navigator.geolocation.getCurrentPosition(
            function(position) {{
                document.getElementById("alatitude").value =
                    position.coords.latitude;

                document.getElementById("alongitude").value =
                    position.coords.longitude;

                document.getElementById("attendanceStatus").innerText =
                    "✅ GPS location captured.";
            }},
            function() {{
                document.getElementById("attendanceStatus").innerText =
                    "⚠️ Unable to capture GPS.";
            }}
        );
    }}
    </script>
    """)


# ============================================================
# MEETINGS / VIDEO CONFERENCING
# ============================================================

@app.route("/meetings", methods=["GET", "POST"])
@login_required
def meetings():

    conn = get_db()

    if (
        request.method == "POST" and
        session["role"] in ["admin", "official"]
    ):

        conn.execute("""
            INSERT INTO meetings(
                project_id,title,meeting_url,
                meeting_time,created_at
            )
            VALUES(?,?,?,?,?)
        """, (
            request.form.get("project_id"),
            request.form.get("title"),
            request.form.get("meeting_url"),
            request.form.get("meeting_time"),
            now()
        ))

        conn.commit()

        notify_role(
            "staff",
            f"🎥 A new meeting has been scheduled: "
            f"{request.form.get('title')}"
        )

    meeting_list = conn.execute("""
        SELECT
            m.*,
            p.name AS project_name
        FROM meetings m
        LEFT JOIN projects p ON p.id=m.project_id
        ORDER BY m.meeting_time DESC
    """).fetchall()

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

    conn.close()

    form = ""

    if session["role"] in ["admin", "official"]:

        options = "".join(
            f"<option value='{p['id']}'>{p['name']}</option>"
            for p in projects_list
        )

        form = f"""
        <div class="card">
            <h2>➕ Schedule Monitoring / VC Meeting</h2>

            <form method="POST">
                <select name="project_id">
                    {options}
                </select>

                <input name="title"
                       placeholder="Meeting Title"
                       required>

                <input name="meeting_url"
                       placeholder="VC Meeting Link">

                <input type="datetime-local"
                       name="meeting_time"
                       required>

                <button>Schedule Meeting</button>
            </form>
        </div>
        """

    cards = ""

    for meeting in meeting_list:

        join_button = ""

        if meeting["meeting_url"]:
            join_button = f"""
            <a class="btn"
               target="_blank"
               href="{meeting["meeting_url"]}">
                🎥 Join Meeting
            </a>
            """

        cards += f"""
        <div class="card">
            <h3>🎥 {meeting["title"]}</h3>
            <p>🏢 {meeting["project_name"] or "-"}</p>
            <p>🕒 {meeting["meeting_time"]}</p>
            {join_button}
        </div>
        """

    return page("Meetings", f"""
    <h1>🎥 Meeting & VC Coordination</h1>

    {form}

    {cards or
     "<div class='card'>No meetings scheduled.</div>"}
    """)


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
@login_required
def notifications():

    conn = get_db()

    notes = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id=?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.execute("""
        UPDATE notifications
        SET is_read=1
        WHERE user_id=?
    """, (session["user_id"],))

    conn.commit()
    conn.close()

    cards = ""

    for note in notes:
        cards += f"""
        <div class="card">
            <b>🔔 {note["message"]}</b>
            <br>
            <small>{note["created_at"]}</small>
        </div>
        """

    return page("Notifications", f"""
    <h1>🔔 Notifications & Alerts</h1>

    {cards or
     "<div class='card'>No notifications yet.</div>"}
    """)


@app.route("/api/notification-count")
@login_required
def notification_count():

    conn = get_db()

    count = conn.execute("""
        SELECT COUNT(*) FROM notifications
        WHERE user_id=? AND is_read=0
    """, (session["user_id"],)).fetchone()[0]

    conn.close()

    return jsonify({"unread_notifications": count})


# ============================================================
# RULE-BASED ANALYTICS
# ============================================================

@app.route("/analytics")
@login_required
def analytics():

    conn = get_db()

    total_issues = conn.execute(
        "SELECT COUNT(*) FROM issues"
    ).fetchone()[0]

    critical = conn.execute("""
        SELECT COUNT(*) FROM issues
        WHERE severity='Critical'
        AND status!='Resolved'
    """).fetchone()[0]

    open_issues = conn.execute("""
        SELECT COUNT(*) FROM issues
        WHERE status!='Resolved'
    """).fetchone()[0]

    completed = conn.execute("""
        SELECT COUNT(*) FROM inspections
        WHERE status='Completed'
    """).fetchone()[0]

    conn.close()

    alerts = []

    if critical > 0:
        alerts.append(
            "🚨 Critical issues require immediate attention."
        )

    if open_issues > 5:
        alerts.append(
            "⚠️ High number of unresolved issues detected."
        )

    if completed == 0:
        alerts.append(
            "📋 No completed inspections recorded yet."
        )

    if not alerts:
        alerts.append(
            "✅ System status is currently stable."
        )

    alert_html = "".join(
        f"<div class='warning'>{alert}</div><br>"
        for alert in alerts
    )

    return page("Analytics", f"""
    <h1>📈 Rule-Based Analytics</h1>

    <div class="grid">
        <div class="stat">
            <h2>{total_issues}</h2>
            Total Issues
        </div>

        <div class="stat">
            <h2>{critical}</h2>
            Critical Issues
        </div>

        <div class="stat">
            <h2>{open_issues}</h2>
            Open Issues
        </div>

        <div class="stat">
            <h2>{completed}</h2>
            Completed Inspections
        </div>
    </div>

    <div class="card">
        <h2>🤖 Smart System Alerts</h2>
        {alert_html}
    </div>
    """)


# ============================================================
# INITIALIZATION
# ============================================================

init_db()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
