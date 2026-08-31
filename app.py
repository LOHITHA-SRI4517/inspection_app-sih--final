from flask import (
    Flask, request, redirect, url_for, session, jsonify,
    send_from_directory, render_template_string
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
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
    "change-this-secret-key-before-production"
)

# Render-compatible storage paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "inspection.db"))
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
    """Safely supports upgrading an existing SQLite database."""
    columns = [row["name"] for row in conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()]

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
        identity_photo TEXT,
        identity_verified INTEGER DEFAULT 0,
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
        remarks TEXT,
        identity_check_photo TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_id INTEGER,
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
    """)

    # Safe upgrades for older databases
    add_column_if_missing(conn, "users", "identity_photo", "TEXT")
    add_column_if_missing(conn, "users", "identity_verified",
                          "INTEGER DEFAULT 0")

    add_column_if_missing(conn, "inspections",
                          "identity_check_photo", "TEXT")

    conn.commit()
    conn.close()


# ============================================================
# SECURITY HELPERS
# ============================================================

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
                    "<div class='card'><h2>🚫 Access Denied</h2>"
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
    """, (
        user_id,
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    conn.commit()
    conn.close()


# ============================================================
# FILE / CAMERA IMAGE HELPERS
# ============================================================

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
    """
    Saves a browser camera image.
    Expected format:
    data:image/jpeg;base64,/9j/4AAQ...
    """

    if not data_url or not data_url.startswith("data:image"):
        return None

    try:
        match = re.match(
            r"data:image/(png|jpeg|jpg|webp);base64,(.*)",
            data_url,
            re.DOTALL
        )

        if not match:
            return None

        image_type = match.group(1)
        encoded_data = match.group(2)

        ext = "jpg" if image_type == "jpeg" else image_type

        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        image_data = base64.b64decode(encoded_data)

        with open(filepath, "wb") as image_file:
            image_file.write(image_data)

        return filename

    except Exception as e:
        print("Camera image error:", e)
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
        <aside class="sidebar">
            <h2>🛡️ SmartInspect</h2>

            <div class="user-box">
                👤 <b>{user}</b><br>
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
            <a href="/profile">👤 Identity Profile</a>
            <hr>
            <a href="/logout">🚪 Logout</a>
        </aside>
        """

    margin = "260px" if session.get("user_id") else "0"

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
                position: fixed;
                left: 0;
                top: 0;
                width: 235px;
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
                color: white;
                text-decoration: none;
                padding: 11px;
                margin: 5px 0;
                border-radius: 8px;
            }}

            .sidebar a:hover {{
                background: #1e293b;
            }}

            .user-box {{
                background: #1e293b;
                padding: 12px;
                border-radius: 10px;
                margin-bottom: 15px;
            }}

            .main {{
                margin-left: {margin};
                padding: 30px;
                max-width: 1450px;
            }}

            .card {{
                background: white;
                padding: 22px;
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

            textarea {{
                min-height: 100px;
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
                margin: 4px;
            }}

            button:hover, .btn:hover {{
                background: #1d4ed8;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
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
                max-width: 500px;
                margin: 60px auto;
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

            video {{
                width: 100%;
                max-width: 400px;
                border-radius: 12px;
                background: black;
            }}

            #notificationBadge {{
                background: #ef4444;
                border-radius: 20px;
                padding: 2px 7px;
                font-size: 12px;
            }}

            @media(max-width: 700px) {{
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

        <main class="main">
            {content}
        </main>

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
                console.log('Notification check unavailable');
            }}
        }}

        checkNotifications();
        setInterval(checkNotifications, 30000);
        </script>
    </body>
    </html>
    """


# ============================================================
# HOME
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
                A centralized platform for monitoring,
                inspections, attendance, evidence collection,
                issue resolution and stakeholder coordination.
            </p>

            <a class="btn" href="/login">🔐 Login</a>
            <a class="btn" href="/register">📝 Register</a>

            <p><small>
                No demo accounts are hardcoded into the system.
                Each user uses their own registered credentials.
            </small></p>
        </div>
    """)


# ============================================================
# REGISTER WITH CAMERA IDENTITY CAPTURE
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        camera_image = request.form.get("camera_image")

        if not name or not email or not password:
            message = "<div class='danger'>Please fill all required fields.</div>"
        else:
            identity_photo = save_camera_image(camera_image)

            conn = get_db()
            count = conn.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0]

            # First real registered user becomes admin.
            # No demo credentials are created.
            role = "admin" if count == 0 else "staff"

            try:
                conn.execute("""
                    INSERT INTO users(
                        name, email, password, role,
                        identity_photo, identity_verified, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    email,
                    generate_password_hash(password),
                    role,
                    identity_photo,
                    1 if identity_photo else 0,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ))

                conn.commit()
                conn.close()

                return redirect(url_for("login"))

            except sqlite3.IntegrityError:
                conn.close()
                message = "<div class='danger'>Email already registered.</div>"

    return page("Register", f"""
        <div class="login card">
            <h2>📝 Create Secure Account</h2>
            {message}

            <form method="POST" id="registerForm">

                <input name="name"
                       placeholder="Full Name"
                       required>

                <input type="email"
                       name="email"
                       placeholder="Official Email"
                       required>

                <input type="password"
                       name="password"
                       placeholder="Password"
                       required>

                <h3>📷 Identity Photo Registration</h3>

                <video id="camera"
                       autoplay
                       playsinline></video>

                <br>

                <button type="button"
                        onclick="startCamera()">
                    Start Camera
                </button>

                <button type="button"
                        onclick="capturePhoto()">
                    Capture Identity Photo
                </button>

                <canvas id="canvas"
                        style="display:none;"></canvas>

                <input type="hidden"
                       name="camera_image"
                       id="camera_image">

                <p id="cameraStatus"></p>

                <button>Create Account</button>
            </form>

            <p>
                Already registered?
                <a href="/login">Login here</a>
            </p>
        </div>

        <script>
        let stream;

        async function startCamera() {{
            try {{
                stream = await navigator.mediaDevices.getUserMedia({{
                    video: true
                }});

                document.getElementById('camera').srcObject = stream;

                document.getElementById('cameraStatus').innerHTML =
                    '✅ Camera ready';
            }} catch (error) {{
                document.getElementById('cameraStatus').innerHTML =
                    '⚠️ Camera permission is required for identity capture.';
            }}
        }}

        function capturePhoto() {{
            const video = document.getElementById('camera');
            const canvas = document.getElementById('canvas');

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            canvas.getContext('2d').drawImage(
                video, 0, 0,
                canvas.width, canvas.height
            );

            const image = canvas.toDataURL('image/jpeg');

            document.getElementById('camera_image').value = image;

            document.getElementById('cameraStatus').innerHTML =
                '✅ Identity photo captured successfully';
        }}
        </script>
    """)


# ============================================================
# LOGIN
# ============================================================

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

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        error = """
            <div class='danger'>
                Invalid email or password.
            </div>
        """

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

                <button>Login Securely</button>
            </form>

            <p>
                New user?
                <a href="/register">Create an account</a>
            </p>
        </div>
    """)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()

    project_count = conn.execute(
        "SELECT COUNT(*) FROM projects"
    ).fetchone()[0]

    inspection_count = conn.execute(
        "SELECT COUNT(*) FROM inspections"
    ).fetchone()[0]

    open_issue_count = conn.execute("""
        SELECT COUNT(*) FROM issues
        WHERE status != 'Resolved'
    """).fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")

    attendance_count = conn.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE attendance_date=?
    """, (today,)).fetchone()[0]

    recent = conn.execute("""
        SELECT
            inspections.title,
            inspections.status,
            projects.name AS project_name
        FROM inspections
        LEFT JOIN projects
            ON inspections.project_id = projects.id
        ORDER BY inspections.id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    rows = ""

    for item in recent:
        rows += f"""
        <tr>
            <td>{item['title'] or 'Inspection'}</td>
            <td>{item['project_name'] or 'Not assigned'}</td>
            <td>{item['status']}</td>
        </tr>
        """

    return page("Dashboard", f"""
        <h1>📊 Real-Time Monitoring Dashboard</h1>

        <div class="grid">
            <div class="stat">
                <h2>{project_count}</h2>
                🏢 Projects / Institutes
            </div>

            <div class="stat">
                <h2>{inspection_count}</h2>
                📋 Inspections
            </div>

            <div class="stat">
                <h2>{open_issue_count}</h2>
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
                    <th>Status</th>
                </tr>

                {rows or "<tr><td colspan='3'>No activity yet.</td></tr>"}
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

        if session.get("role") not in ["admin", "official"]:
            conn.close()
            return "Access denied", 403

        conn.execute("""
            INSERT INTO projects(
                name, location, incharge,
                cctv_url, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.form.get("name"),
            request.form.get("location"),
            request.form.get("incharge"),
            request.form.get("cctv_url"),
            "Active",
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        conn.commit()

    project_list = conn.execute(
        "SELECT * FROM projects ORDER BY id DESC"
    ).fetchall()

    conn.close()

    add_form = ""

    if session.get("role") in ["admin", "official"]:
        add_form = """
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
                       placeholder="Authorized CCTV / Monitoring URL">

                <button>Add Project</button>
            </form>
        </div>
        """

    rows = ""

    for project in project_list:

        cctv = "Not Connected"

        if project["cctv_url"]:
            cctv = f"""
            <a class="btn"
               href="{project['cctv_url']}"
               target="_blank">
               📹 Open CCTV
            </a>
            """

        rows += f"""
        <tr>
            <td>{project['name']}</td>
            <td>{project['location'] or '-'}</td>
            <td>{project['incharge'] or '-'}</td>
            <td>{project['status']}</td>
            <td>{cctv}</td>
        </tr>
        """

    return page("Projects", f"""
        <h1>🏢 Project & Institute Management</h1>

        {add_form}

        <div class="card">
            <table>
                <tr>
                    <th>Name</th>
                    <th>Location</th>
                    <th>Incharge</th>
                    <th>Status</th>
                    <th>Monitoring</th>
                </tr>

                {rows or "<tr><td colspan='5'>No projects yet.</td></tr>"}
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
    title = request.form.get("title", "Surprise Inspection")

    conn = get_db()

    inspectors = conn.execute("""
        SELECT * FROM users
        WHERE role IN ('inspector', 'official')
    """).fetchall()

    if not inspectors:
        conn.close()
        return page(
            "Inspector Required",
            """
            <div class="card">
                <h2>⚠️ No Inspector Available</h2>
                <p>
                    An administrator should assign an appropriate
                    user role before creating an inspection.
                </p>
            </div>
            """
        )

    inspector = random.choice(inspectors)

    conn.execute("""
        INSERT INTO inspections(
            project_id, inspector_id, title,
            status, created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        project_id,
        inspector["id"],
        title,
        "Assigned",
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    conn.close()

    notify(
        inspector["id"],
        f"🎲 You have been assigned an inspection: {title}"
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

    if session.get("role") == "inspector":

        inspection_list = conn.execute("""
            SELECT inspections.*,
                   projects.name AS project_name,
                   users.name AS inspector_name
            FROM inspections
            LEFT JOIN projects
                ON inspections.project_id = projects.id
            LEFT JOIN users
                ON inspections.inspector_id = users.id
            WHERE inspections.inspector_id=?
            ORDER BY inspections.id DESC
        """, (session["user_id"],)).fetchall()

    else:

        inspection_list = conn.execute("""
            SELECT inspections.*,
                   projects.name AS project_name,
                   users.name AS inspector_name
            FROM inspections
            LEFT JOIN projects
                ON inspections.project_id = projects.id
            LEFT JOIN users
                ON inspections.inspector_id = users.id
            ORDER BY inspections.id DESC
        """).fetchall()

    conn.close()

    assignment_form = ""

    if session.get("role") in ["admin", "official"]:

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

                <button>🎲 Assign Random Inspector</button>
            </form>
        </div>
        """

    cards = ""

    for inspection in inspection_list:

        button = ""

        if inspection["status"] != "Completed":

            if (
                session.get("role") == "inspector" and
                inspection["inspector_id"] == session["user_id"]
            ):
                button = f"""
                <a class="btn"
                   href="/inspection-form/{inspection['id']}">
                    🔐 Verify Identity & Start
                </a>
                """

        cards += f"""
        <div class="card">
            <h3>📋 {inspection['title']}</h3>

            <p><b>Project:</b>
                {inspection['project_name'] or '-'}
            </p>

            <p><b>Inspector:</b>
                {inspection['inspector_name'] or '-'}
            </p>

            <p><b>Status:</b>
                {inspection['status']}
            </p>

            {button}
        </div>
        """

    return page("Inspections", f"""
        <h1>📋 Digital Inspection Module</h1>

        {assignment_form}

        {cards or "<div class='card'>No inspections available.</div>"}
    """)


# ============================================================
# INSPECTION FORM + IDENTITY PHOTO + GPS
# ============================================================

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
        session.get("role") == "inspector" and
        inspection["inspector_id"] != session["user_id"]
    ):
        conn.close()
        return "Access denied", 403

    if request.method == "POST":

        identity_photo = save_camera_image(
            request.form.get("verification_photo")
        )

        evidence = save_file(
            request.files.get("evidence")
        )

        checklist = ", ".join(
            request.form.getlist("checklist")
        )

        conn.execute("""
            UPDATE inspections
            SET status=?,
                latitude=?,
                longitude=?,
                checklist=?,
                evidence=?,
                remarks=?,
                identity_check_photo=?
            WHERE id=?
        """, (
            "Completed",
            request.form.get("latitude"),
            request.form.get("longitude"),
            checklist,
            evidence,
            request.form.get("remarks"),
            identity_photo,
            inspection_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("inspections"))

    conn.close()

    return page("Inspection Form", f"""
        <div class="card">

            <h1>📋 Secure Inspection Form</h1>

            <p class="warning">
                🔐 Capture a current identity photo before
                submitting the inspection report.
            </p>

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

                <h3>📷 Identity Verification Capture</h3>

                <video id="camera"
                       autoplay
                       playsinline></video>

                <br>

                <button type="button"
                        onclick="startCamera()">
                    Start Camera
                </button>

                <button type="button"
                        onclick="captureVerification()">
                    Capture Verification Photo
                </button>

                <canvas id="canvas"
                        style="display:none;"></canvas>

                <p id="identityStatus"></p>

                <h3>📍 GPS Location</h3>

                <button type="button"
                        onclick="getLocation()">
                    Capture Current Location
                </button>

                <p id="locationStatus"></p>

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

                <h3>📸 Evidence Upload</h3>

                <input type="file"
                       name="evidence"
                       accept="image/*">

                <h3>📝 Remarks</h3>

                <textarea name="remarks"
                          placeholder="Enter observations">
                </textarea>

                <button>Submit Secure Inspection Report</button>

            </form>
        </div>

        <script>
        async function startCamera() {{
            try {{
                const stream =
                    await navigator.mediaDevices.getUserMedia({{
                        video: true
                    }});

                document.getElementById('camera').srcObject = stream;

            }} catch(error) {{
                document.getElementById('identityStatus').innerHTML =
                    '⚠️ Camera permission is required.';
            }}
        }}

        function captureVerification() {{
            const video =
                document.getElementById('camera');

            const canvas =
                document.getElementById('canvas');

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            canvas.getContext('2d').drawImage(
                video, 0, 0,
                canvas.width, canvas.height
            );

            document.getElementById('verification_photo').value =
                canvas.toDataURL('image/jpeg');

            document.getElementById('identityStatus').innerHTML =
                '✅ Current identity photo captured';
        }}

        function getLocation() {{
            if (!navigator.geolocation) {{
                document.getElementById('locationStatus').innerHTML =
                    '⚠️ GPS is not supported.';
                return;
            }}

            navigator.geolocation.getCurrentPosition(
                function(position) {{
                    document.getElementById('latitude').value =
                        position.coords.latitude;

                    document.getElementById('longitude').value =
                        position.coords.longitude;

                    document.getElementById('locationStatus').innerHTML =
                        '✅ GPS location captured';
                }},
                function() {{
                    document.getElementById('locationStatus').innerHTML =
                        '⚠️ Unable to capture location.';
                }}
            );
        }}
        </script>
    """)


# ============================================================
# STAFF WORK / ISSUE REPORT
# ============================================================

@app.route("/staff-report", methods=["GET", "POST"])
@login_required
def staff_report():

    if request.method == "POST":

        title = request.form.get("title")
        description = request.form.get("description")
        severity = request.form.get("severity")

        conn = get_db()

        conn.execute("""
            INSERT INTO issues(
                reported_by, title, description,
                severity, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            title,
            description,
            severity,
            "Open",
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        admins = conn.execute("""
            SELECT id FROM users
            WHERE role IN ('admin', 'official')
        """).fetchall()

        conn.commit()
        conn.close()

        for admin in admins:
            notify(
                admin["id"],
                f"⚠️ New issue reported: {title}"
            )

        return redirect(url_for("issues"))

    return page("Staff Work", """
        <div class="card">
            <h1>🛠️ Project Staff Work & Issue Report</h1>

            <p>
                Project staff can report field issues and
                operational problems directly to authorities.
            </p>

            <form method="POST">

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
# ISSUES
# ============================================================

@app.route("/issues", methods=["GET", "POST"])
@login_required
def issues():

    conn = get_db()

    if (
        request.method == "POST" and
        session.get("role") in ["admin", "official", "inspector"]
    ):

        issue_id = request.form.get("issue_id")
        resolution = request.form.get("resolution")

        conn.execute("""
            UPDATE issues
            SET status='Resolved',
                resolution=?
            WHERE id=?
        """, (resolution, issue_id))

        conn.commit()

    issue_list = conn.execute("""
        SELECT issues.*, users.name AS reporter_name
        FROM issues
        LEFT JOIN users
            ON issues.reported_by = users.id
        ORDER BY issues.id DESC
    """).fetchall()

    conn.close()

    content = "<h1>⚠️ Issue Verification & Resolution</h1>"

    for issue in issue_list:

        action = ""

        if (
            issue["status"] != "Resolved" and
            session.get("role") in
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

        content += f"""
        <div class="card">
            <h3>{issue['title']} — {issue['severity']}</h3>

            <p>{issue['description']}</p>

            <p>
                <b>Reported by:</b>
                {issue['reporter_name'] or 'Unknown'}
            </p>

            <p>
                <b>Status:</b>
                {issue['status']}
            </p>

            {action}
        </div>
        """

    if not issue_list:
        content += "<div class='card'>No issues reported.</div>"

    return page("Issues", content)


# ============================================================
# ATTENDANCE
# ============================================================

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():

    conn = get_db()

    if request.method == "POST":

        photo = save_camera_image(
            request.form.get("attendance_photo")
        )

        conn.execute("""
            INSERT INTO attendance(
                user_id, project_id, latitude,
                longitude, photo, attendance_date, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            request.form.get("project_id"),
            request.form.get("latitude"),
            request.form.get("longitude"),
            photo,
            datetime.now().strftime("%Y-%m-%d"),
            "Present"
        ))

        conn.commit()

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

    records = conn.execute("""
        SELECT attendance.*,
               users.name AS user_name,
               projects.name AS project_name
        FROM attendance
        LEFT JOIN users
            ON attendance.user_id = users.id
        LEFT JOIN projects
            ON attendance.project_id = projects.id
        ORDER BY attendance.id DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    options = "".join(
        f"<option value='{p['id']}'>{p['name']}</option>"
        for p in projects_list
    )

    rows = "".join(f"""
        <tr>
            <td>{record['user_name']}</td>
            <td>{record['project_name'] or '-'}</td>
            <td>{record['attendance_date']}</td>
            <td>{record['status']}</td>
        </tr>
    """ for record in records)

    return page("Attendance", f"""
        <h1>👥 Smart Attendance Management</h1>

        <div class="card">

            <form method="POST">

                <select name="project_id">
                    {options}
                </select>

                <input type="hidden"
                       name="latitude"
                       id="alatitude">

                <input type="hidden"
                       name="longitude"
                       id="alongitude">

                <input type="hidden"
                       name="attendance_photo"
                       id="attendance_photo">

                <h3>📷 Live Attendance Photo</h3>

                <video id="attendanceCamera"
                       autoplay
                       playsinline></video>

                <br>

                <button type="button"
                        onclick="startAttendanceCamera()">
                    Start Camera
                </button>

                <button type="button"
                        onclick="captureAttendance()">
                    Capture Photo
                </button>

                <canvas id="attendanceCanvas"
                        style="display:none;"></canvas>

                <p id="attendancePhotoStatus"></p>

                <button type="button"
                        onclick="attendanceLocation()">
                    📍 Capture GPS
                </button>

                <p id="attendanceStatus"></p>

                <button>Mark Attendance</button>

            </form>
        </div>

        <div class="card">

            <h2>Recent Attendance</h2>

            <table>
                <tr>
                    <th>User</th>
                    <th>Project</th>
                    <th>Date</th>
                    <th>Status</th>
                </tr>

                {rows}
            </table>
        </div>

        <script>
        async function startAttendanceCamera() {{
            try {{
                const stream =
                    await navigator.mediaDevices.getUserMedia({{
                        video: true
                    }});

                document.getElementById('attendanceCamera').srcObject =
                    stream;
            }} catch(error) {{
                document.getElementById(
                    'attendancePhotoStatus'
                ).innerHTML = '⚠️ Camera permission denied.';
            }}
        }}

        function captureAttendance() {{
            const video =
                document.getElementById('attendanceCamera');

            const canvas =
                document.getElementById('attendanceCanvas');

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            canvas.getContext('2d').drawImage(
                video, 0, 0,
                canvas.width, canvas.height
            );

            document.getElementById('attendance_photo').value =
                canvas.toDataURL('image/jpeg');

            document.getElementById(
                'attendancePhotoStatus'
            ).innerHTML = '✅ Attendance photo captured';
        }}

        function attendanceLocation() {{
            navigator.geolocation.getCurrentPosition(
                function(position) {{
                    document.getElementById('alatitude').value =
                        position.coords.latitude;

                    document.getElementById('alongitude').value =
                        position.coords.longitude;

                    document.getElementById('attendanceStatus').innerHTML =
                        '✅ GPS captured';
                }},
                function() {{
                    document.getElementById('attendanceStatus').innerHTML =
                        '⚠️ GPS permission required.';
                }}
            );
        }}
        </script>
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

    cards = "".join(f"""
        <div class="card">
            <b>🔔 {note['message']}</b><br>
            <small>{note['created_at']}</small>
        </div>
    """ for note in notes)

    return page("Notifications", f"""
        <h1>🔔 Notifications & Alerts</h1>
        {cards or "<div class='card'>No notifications yet.</div>"}
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

    return jsonify({
        "unread_notifications": count
    })


# ============================================================
# ANALYTICS
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
    """).fetchone()[0]

    open_issues = conn.execute("""
        SELECT COUNT(*) FROM issues
        WHERE status != 'Resolved'
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
# IDENTITY PROFILE
# ============================================================

@app.route("/profile")
@login_required
def profile():

    conn = get_db()

    user = conn.execute("""
        SELECT * FROM users WHERE id=?
    """, (session["user_id"],)).fetchone()

    conn.close()

    photo_html = """
        <p class="warning">
            No identity photo registered.
        </p>
    """

    if user["identity_photo"]:
        photo_html = f"""
            <img src="/uploads/{user['identity_photo']}"
                 style="max-width:250px;border-radius:12px;">
        """

    verification = (
        "✅ Identity photo registered"
        if user["identity_verified"]
        else "⚠️ Identity photo not registered"
    )

    return page("Profile", f"""
        <div class="card">
            <h1>👤 Identity Profile</h1>

            <p><b>Name:</b> {user['name']}</p>
            <p><b>Email:</b> {user['email']}</p>
            <p><b>Role:</b> {user['role'].upper()}</p>
            <p><b>Status:</b> {verification}</p>

            <h3>Registered Identity Photo</h3>
            {photo_html}

            <p class="warning">
                🔐 Identity photos are captured as part of
                the security and verification workflow.
                This prototype does not perform automated
                AI biometric matching.
            </p>
        </div>
    """)


# ============================================================
# UPLOAD FILES
# ============================================================

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# MEETINGS / VC
# ============================================================

@app.route("/meetings", methods=["GET", "POST"])
@login_required
def meetings():

    conn = get_db()

    if (
        request.method == "POST" and
        session.get("role") in ["admin", "official"]
    ):

        conn.execute("""
            INSERT INTO meetings(
                project_id, title, meeting_url,
                meeting_time, created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            request.form.get("project_id"),
            request.form.get("title"),
            request.form.get("meeting_url"),
            request.form.get("meeting_time"),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        conn.commit()

    meetings_list = conn.execute("""
        SELECT meetings.*, projects.name AS project_name
        FROM meetings
        LEFT JOIN projects
            ON meetings.project_id = projects.id
        ORDER BY meetings.id DESC
    """).fetchall()

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

    conn.close()

    form = ""

    if session.get("role") in ["admin", "official"]:

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
                       placeholder="Meeting URL">

                <input type="datetime-local"
                       name="meeting_time"
                       required>

                <button>Schedule Meeting</button>

            </form>
        </div>
        """

    cards = ""

    for meeting in meetings_list:

        join = ""

        if meeting["meeting_url"]:
            join = f"""
                <a class="btn"
                   href="{meeting['meeting_url']}"
                   target="_blank">
                   Join Meeting
                </a>
            """

        cards += f"""
        <div class="card">
            <h3>🎥 {meeting['title']}</h3>
            <p>🏢 {meeting['project_name'] or '-'}</p>
            <p>🕒 {meeting['meeting_time']}</p>
            {join}
        </div>
        """

    return page("Meetings", f"""
        <h1>🎥 Meeting & VC Coordination</h1>

        {form}

        {cards or "<div class='card'>No meetings scheduled.</div>"}
    """)


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def file_too_large(error):
    return page(
        "File Too Large",
        """
        <div class="card">
            <h2>⚠️ File Too Large</h2>
            <p>Please upload a file smaller than 10 MB.</p>
        </div>
        """
    ), 413


@app.errorhandler(404)
def not_found(error):
    return page(
        "Page Not Found",
        """
        <div class="card">
            <h2>404 - Page Not Found</h2>
            <a class="btn" href="/">Go Home</a>
        </div>
        """
    ), 404


# ============================================================
# INITIALIZATION
# ============================================================

init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
