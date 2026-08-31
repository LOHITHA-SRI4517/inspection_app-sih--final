from flask import Flask, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import sqlite3
import os
import uuid
import random
import base64
import numpy as np
import face_recognition


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key-in-production"
)

DB_NAME = "inspection.db"
UPLOAD_FOLDER = "uploads"
FACE_FOLDER = os.path.join(UPLOAD_FOLDER, "faces")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FACE_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["FACE_FOLDER"] = FACE_FOLDER


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


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
        face_encoding TEXT,
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
        created_at TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(inspector_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_id INTEGER,
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

    # Support existing databases created before face columns were added
    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    ]

    if "face_image" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN face_image TEXT")

    if "face_encoding" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN face_encoding TEXT")

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
                return "Access Denied", 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def notify(user_id, message):
    conn = get_db()
    conn.execute("""
        INSERT INTO notifications (user_id, message, created_at)
        VALUES (?, ?, ?)
    """, (
        user_id,
        message,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    conn.commit()
    conn.close()


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_file(file):
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        return filename
    return None


# ============================================================
# FACE RECOGNITION FUNCTIONS
# ============================================================

def save_camera_image(data_url, folder=FACE_FOLDER):
    """
    Receives a Base64 image from browser camera
    and saves it as an image file.
    """

    if not data_url:
        return None

    try:
        header, encoded = data_url.split(",", 1)
        image_data = base64.b64decode(encoded)

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(folder, filename)

        with open(filepath, "wb") as file:
            file.write(image_data)

        return filename

    except Exception as e:
        print("Camera image error:", e)
        return None


def create_face_encoding(filename):
    """
    Creates a numerical face encoding from an image.
    Exactly one face should ideally be visible.
    """

    if not filename:
        return None

    filepath = os.path.join(FACE_FOLDER, filename)

    try:
        image = face_recognition.load_image_file(filepath)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) != 1:
            return None

        return ",".join(map(str, encodings[0]))

    except Exception as e:
        print("Face encoding error:", e)
        return None


def verify_user_face(user_id, camera_data):
    """
    Compares the current camera image with the
    registered face of the logged-in user.
    """

    conn = get_db()

    user = conn.execute("""
        SELECT face_encoding
        FROM users
        WHERE id=?
    """, (user_id,)).fetchone()

    conn.close()

    if not user or not user["face_encoding"]:
        return False, "No registered face found."

    temp_filename = save_camera_image(camera_data)

    if not temp_filename:
        return False, "Camera image could not be captured."

    filepath = os.path.join(FACE_FOLDER, temp_filename)

    try:
        known_encoding = np.array(
            [float(x) for x in user["face_encoding"].split(",")]
        )

        image = face_recognition.load_image_file(filepath)
        current_encodings = face_recognition.face_encodings(image)

        # Remove temporary verification image
        if os.path.exists(filepath):
            os.remove(filepath)

        if len(current_encodings) != 1:
            return False, "Please ensure exactly one face is visible."

        distance = face_recognition.face_distance(
            [known_encoding],
            current_encodings[0]
        )[0]

        # Lower distance = better match
        # 0.50 gives reasonably strict verification
        if distance < 0.50:
            return True, f"Face verified successfully (confidence score: {round((1-distance)*100, 1)}%)"

        return False, "Face does not match the registered identity."

    except Exception as e:
        print("Face verification error:", e)
        return False, "Face verification failed."


# ============================================================
# BASE HTML / UI
# ============================================================

def page(title, content):

    user = session.get("name", "")
    role = session.get("role", "")

    nav = ""

    if session.get("user_id"):

        staff_link = ""
        if role in ["staff", "worker"]:
            staff_link = '<a href="/staff-report">🛠️ Staff Report</a>'

        nav = f"""
        <div class="sidebar">
            <h2>🛡️ SmartInspect</h2>

            <p class="user">
                👤 {user}<br>
                <small>{role.upper()}</small>
            </p>

            <a href="/dashboard">📊 Dashboard</a>
            <a href="/projects">🏢 Projects</a>
            <a href="/inspections">📋 Inspections</a>
            {staff_link}
            <a href="/attendance">👥 Attendance</a>
            <a href="/issues">⚠️ Issues</a>
            <a href="/meetings">🎥 Meetings</a>
            <a href="/notifications">
                🔔 Notifications <span id="notificationBadge"></span>
            </a>
            <a href="/analytics">📈 Analytics</a>
            <a href="/logout">🚪 Logout</a>
        </div>
        """

    margin = "250px" if session.get("user_id") else "0"

    notification_script = ""

    if session.get("user_id"):
        notification_script = """
        <script>
        let previousNotificationCount = null;

        async function checkNotifications() {
            try {
                const response = await fetch('/api/notification-count');
                const data = await response.json();

                const badge = document.getElementById('notificationBadge');

                if (data.unread_notifications > 0) {
                    badge.innerHTML = '(' + data.unread_notifications + ')';

                    if (
                        previousNotificationCount !== null &&
                        data.unread_notifications > previousNotificationCount
                    ) {
                        alert('🔔 You have a new SmartInspect notification!');
                    }

                } else {
                    badge.innerHTML = '';
                }

                previousNotificationCount = data.unread_notifications;

            } catch (error) {
                console.log("Notification check failed");
            }
        }

        checkNotifications();
        setInterval(checkNotifications, 30000);
        </script>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} | SmartInspect</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">

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
                width: 230px;
                position: fixed;
                height: 100vh;
                background: #0f172a;
                padding: 20px;
                color: white;
                overflow-y: auto;
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
                padding: 10px;
                border-radius: 8px;
            }}

            .main {{
                margin-left: {margin};
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
                grid-template-columns: repeat(auto-fit, minmax(200px,1fr));
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

            button:hover {{
                background: #1d4ed8;
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
                max-width: 500px;
                margin: 70px auto;
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

            video, canvas {{
                width: 100%;
                max-width: 400px;
                border-radius: 10px;
                margin-bottom: 10px;
            }}

            #notificationBadge {{
                color: #fbbf24;
                font-weight: bold;
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

        {notification_script}

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

    return page("SmartInspect", """
    <div class="login card">
        <h1>🛡️ SmartInspect</h1>
        <h3>Real-Time Monitoring & Inspection System</h3>

        <p>
        Centralized platform for transparent monitoring,
        surprise inspections, attendance verification,
        CCTV integration and compliance management.
        </p>

        <a class="btn" href="/login">🔐 Login</a>
        <a class="btn" href="/register">👤 Register</a>
    </div>
    """)


# ============================================================
# REGISTER WITH FACE CAPTURE
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    message = ""

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"].lower()
        password = request.form["password"]
        face_data = request.form.get("face_data")

        if not face_data:
            message = """
            <p class='danger'>
            📷 Face registration is required for security.
            Please capture your face using the camera.
            </p>
            """
        else:

            face_image = save_camera_image(face_data)
            face_encoding = create_face_encoding(face_image)

            if not face_encoding:

                # Delete invalid image
                if face_image:
                    path = os.path.join(FACE_FOLDER, face_image)
                    if os.path.exists(path):
                        os.remove(path)

                message = """
                <p class='danger'>
                Face registration failed. Please ensure only one
                face is clearly visible and try again.
                </p>
                """

            else:

                conn = get_db()

                count = conn.execute(
                    "SELECT COUNT(*) FROM users"
                ).fetchone()[0]

                # First registered account becomes admin
                role = "admin" if count == 0 else "staff"

                try:

                    conn.execute("""
                        INSERT INTO users(
                            name, email, password, role,
                            face_image, face_encoding, created_at
                        )
                        VALUES(?,?,?,?,?,?,?)
                    """, (
                        name,
                        email,
                        generate_password_hash(password),
                        role,
                        face_image,
                        face_encoding,
                        datetime.now().strftime("%Y-%m-%d %H:%M")
                    ))

                    conn.commit()
                    conn.close()

                    return redirect(url_for("login"))

                except sqlite3.IntegrityError:

                    conn.close()

                    message = """
                    <p class='danger'>
                    Email already registered.
                    </p>
                    """

    return page("Register", f"""
    <div class="login card">

        <h2>👤 Create Secure Account</h2>

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

            <h3>📷 Face Registration</h3>

            <p>
            Your face is registered securely for identity
            verification during attendance and inspections.
            </p>

            <video id="video"
                   autoplay
                   playsinline>
            </video>

            <canvas id="canvas"
                    style="display:none">
            </canvas>

            <input type="hidden"
                   name="face_data"
                   id="face_data">

            <br>

            <button type="button"
                    onclick="startCamera()">
                📷 Start Camera
            </button>

            <button type="button"
                    onclick="captureFace()">
                📸 Capture Face
            </button>

            <p id="faceStatus"></p>

            <button type="submit">
                🔐 Create Secure Account
            </button>

        </form>

        <p>
            Already registered?
            <a href="/login">Login</a>
        </p>

    </div>

    <script>

    let stream;

    async function startCamera() {{

        try {{

            stream = await navigator.mediaDevices.getUserMedia({{
                video: {{
                    facingMode: "user"
                }}
            }});

            document.getElementById("video").srcObject = stream;

            document.getElementById("faceStatus").innerHTML =
                "📷 Camera started. Position your face clearly.";

        }} catch(error) {{

            document.getElementById("faceStatus").innerHTML =
                "⚠️ Camera permission is required.";

        }}
    }}

    function captureFace() {{

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

        document.getElementById("face_data").value =
            canvas.toDataURL("image/jpeg");

        document.getElementById("faceStatus").innerHTML =
            "✅ Face captured successfully. You can create your account.";

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

        email = request.form["email"].lower()
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        error = """
        <p class='danger'>
        Invalid email or password.
        </p>
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

    try:
        # Basic statistics
        total_projects = conn.execute(
            "SELECT COUNT(*) FROM projects"
        ).fetchone()[0]

        total_inspections = conn.execute(
            "SELECT COUNT(*) FROM inspections"
        ).fetchone()[0]

        open_issues = conn.execute(
            "SELECT COUNT(*) FROM issues WHERE status != 'Resolved'"
        ).fetchone()[0]

        today = datetime.now().strftime("%Y-%m-%d")
        today_attendance = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE attendance_date=?",
            (today,)
        ).fetchone()[0]

        # Recent inspections with project details
        recent_inspections = conn.execute("""
            SELECT inspections.*,
                   projects.name AS project_name,
                   users.name AS inspector_name
            FROM inspections
            LEFT JOIN projects
                ON inspections.project_id = projects.id
            LEFT JOIN users
                ON inspections.inspector_id = users.id
            ORDER BY inspections.id DESC
            LIMIT 5
        """).fetchall()

        conn.close()

    except sqlite3.Error as e:
        conn.close()
        return f"""
        <h2>Database Dashboard Error</h2>
        <p>{str(e)}</p>
        """, 500

    inspection_rows = ""

    for item in recent_inspections:
        inspection_rows += f"""
        <tr>
            <td>{item['title'] or 'Inspection'}</td>
            <td>{item['project_name'] or 'Not Assigned'}</td>
            <td>{item['inspector_name'] or 'Not Assigned'}</td>
            <td>{item['status']}</td>
        </tr>
        """

    if not inspection_rows:
        inspection_rows = """
        <tr>
            <td colspan="4">No inspection records available.</td>
        </tr>
        """

    return page("Dashboard", f"""
        <h1>📊 Real-Time Monitoring Dashboard</h1>

        <div class="grid">
            <div class="stat">
                <h2>{total_projects}</h2>
                🏢 Projects / Institutes
            </div>

            <div class="stat">
                <h2>{total_inspections}</h2>
                📋 Total Inspections
            </div>

            <div class="stat">
                <h2>{open_issues}</h2>
                ⚠️ Open Issues
            </div>

            <div class="stat">
                <h2>{today_attendance}</h2>
                👥 Today's Attendance
            </div>
        </div>

        <div class="card">
            <h2>📋 Recent Inspection Activity</h2>

            <table>
                <tr>
                    <th>Inspection</th>
                    <th>Project</th>
                    <th>Inspector</th>
                    <th>Status</th>
                </tr>
                {inspection_rows}
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
            return "Only authorized officials can add projects.", 403

        conn.execute("""
            INSERT INTO projects(
                name, location, incharge,
                cctv_url, status, created_at
            )
            VALUES(?,?,?,?,?,?)
        """, (
            request.form["name"],
            request.form.get("location"),
            request.form.get("incharge"),
            request.form.get("cctv_url"),
            "Active",
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        conn.commit()

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

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

    for p in projects_list:

        cctv = "Not Connected"

        if p["cctv_url"]:
            cctv = f"""
            <a class='btn'
               href='{p["cctv_url"]}'
               target='_blank'>
               📹 Open CCTV
            </a>
            """

        rows += f"""
        <tr>
            <td>{p['name']}</td>
            <td>{p['location'] or '-'}</td>
            <td>{p['incharge'] or '-'}</td>
            <td>{p['status']}</td>
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

            {rows or "<tr><td colspan='5'>No projects available.</td></tr>"}

        </table>

    </div>
    """)


# ============================================================
# RANDOM INSPECTOR ASSIGNMENT
# ============================================================

@app.route("/assign-inspector", methods=["POST"])
@role_required("admin", "official")
def assign_inspector():

    project_id = request.form["project_id"]
    title = request.form.get("title", "Surprise Inspection")

    conn = get_db()

    inspectors = conn.execute("""
        SELECT *
        FROM users
        WHERE role IN ('inspector', 'official')
    """).fetchall()

    if not inspectors:
        conn.close()
        return (
            "No inspectors available. "
            "An administrator must assign Inspector roles.",
            400
        )

    inspector = random.choice(inspectors)

    # CORRECTED: 4 values for 4 columns
    conn.execute("""
        INSERT INTO inspections(
            project_id,
            inspector_id,
            title,
            created_at
        )
        VALUES(?,?,?,?)
    """, (
        project_id,
        inspector["id"],
        title,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    conn.close()

    notify(
        inspector["id"],
        f"🎲 New inspection assigned: {title}. "
        f"Face verification is required before submission."
    )

    return redirect(url_for("inspections"))


# ============================================================
# INSPECTIONS
# ============================================================

@app.route("/inspections", methods=["GET", "POST"])
@login_required
def inspections():

    conn = get_db()

    if request.method == "POST":

        inspection_id = request.form.get("inspection_id")

        # Verify inspection ownership
        inspection = conn.execute("""
            SELECT *
            FROM inspections
            WHERE id=?
        """, (inspection_id,)).fetchone()

        if not inspection:
            conn.close()
            return "Inspection not found.", 404

        if (
            session["role"] == "inspector" and
            inspection["inspector_id"] != session["user_id"]
        ):
            conn.close()
            return "You are not authorized for this inspection.", 403

        # FACE VERIFICATION
        face_data = request.form.get("verification_face")

        verified, message = verify_user_face(
            session["user_id"],
            face_data
        )

        if not verified:
            conn.close()
            return page(
                "Face Verification Failed",
                f"""
                <div class="login card">
                    <h2>❌ Identity Verification Failed</h2>
                    <p class="danger">{message}</p>
                    <a class="btn"
                       href="/inspection-form/{inspection_id}">
                       Try Again
                    </a>
                </div>
                """
            )

        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        checklist_items = request.form.getlist("checklist")
        checklist = ", ".join(checklist_items)

        evidence = save_file(
            request.files.get("evidence")
        )

        conn.execute("""
            UPDATE inspections
            SET
                status='Completed',
                latitude=?,
                longitude=?,
                checklist=?,
                evidence=?,
                remarks=?
            WHERE id=?
        """, (
            latitude,
            longitude,
            checklist,
            evidence,
            request.form.get("remarks"),
            inspection_id
        ))

        conn.commit()
        conn.close()

        notify(
            session["user_id"],
            "✅ Inspection submitted successfully and identity verified."
        )

        return redirect(url_for("inspections"))

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

    if session["role"] == "inspector":

        inspections_list = conn.execute("""
            SELECT i.*, p.name project_name,
                   u.name inspector_name
            FROM inspections i
            LEFT JOIN projects p ON i.project_id=p.id
            LEFT JOIN users u ON i.inspector_id=u.id
            WHERE i.inspector_id=?
            ORDER BY i.id DESC
        """, (
            session["user_id"],
        )).fetchall()

    else:

        inspections_list = conn.execute("""
            SELECT i.*, p.name project_name,
                   u.name inspector_name
            FROM inspections i
            LEFT JOIN projects p ON i.project_id=p.id
            LEFT JOIN users u ON i.inspector_id=u.id
            ORDER BY i.id DESC
        """).fetchall()

    conn.close()

    assignment_form = ""

    if session["role"] in ["admin", "official"]:

        project_options = "".join(
            f"<option value='{p['id']}'>{p['name']}</option>"
            for p in projects_list
        )

        assignment_form = f"""
        <div class="card">

            <h2>🎲 Random Inspector Assignment</h2>

            <form method="POST"
                  action="/assign-inspector">

                <input name="title"
                       placeholder="Inspection Title"
                       required>

                <select name="project_id">
                    {project_options}
                </select>

                <button>
                    Randomly Assign Inspector 🎲
                </button>

            </form>

        </div>
        """

    cards = ""

    for i in inspections_list:

        if i["status"] == "Completed":

            cards += f"""
            <div class="card">

                <h3>📋 {i['title']}</h3>

                <p><b>Project:</b>
                    {i['project_name'] or '-'}
                </p>

                <p><b>Inspector:</b>
                    {i['inspector_name'] or '-'}
                </p>

                <p class="success">
                    ✅ Completed & Identity Verified
                </p>

                <p>
                    <b>GPS:</b>
                    {i['latitude'] or '-'},
                    {i['longitude'] or '-'}
                </p>

                <p>
                    <b>Checklist:</b>
                    {i['checklist'] or '-'}
                </p>

            </div>
            """

        else:

            can_start = (
                session["role"] != "inspector" or
                i["inspector_id"] == session["user_id"]
            )

            button = ""

            if can_start:
                button = f"""
                <a class="btn"
                   href="/inspection-form/{i['id']}">
                   🔐 Verify Face & Start Inspection
                </a>
                """

            cards += f"""
            <div class="card">

                <h3>📋 {i['title']}</h3>

                <p>
                    <b>Project:</b>
                    {i['project_name'] or '-'}
                </p>

                <p>
                    <b>Inspector:</b>
                    {i['inspector_name'] or 'Not assigned'}
                </p>

                <p><b>Status:</b> {i['status']}</p>

                {button}

            </div>
            """

    return page("Inspections", f"""

    <h1>📋 Digital Inspection Module</h1>

    {assignment_form}

    {cards or "<div class='card'>No inspections available.</div>"}
    """)


# ============================================================
# INSPECTION FORM + FACE + GPS + CAMERA
# ============================================================

@app.route("/inspection-form/<int:inspection_id>")
@login_required
def inspection_form(inspection_id):

    conn = get_db()

    inspection = conn.execute("""
        SELECT *
        FROM inspections
        WHERE id=?
    """, (inspection_id,)).fetchone()

    conn.close()

    if not inspection:
        return "Inspection not found.", 404

    if (
        session["role"] == "inspector" and
        inspection["inspector_id"] != session["user_id"]
    ):
        return "Access denied.", 403

    return page("Inspection Form", f"""

    <div class="card">

        <h1>📋 Smart Inspection Form</h1>

        <p class="warning">
            🔐 For security, your face will be verified before
            the inspection report can be submitted.
        </p>

        <form method="POST"
              action="/inspections"
              enctype="multipart/form-data">

            <input type="hidden"
                   name="inspection_id"
                   value="{inspection_id}">

            <input type="hidden"
                   name="latitude"
                   id="latitude">

            <input type="hidden"
                   name="longitude"
                   id="longitude">

            <input type="hidden"
                   name="verification_face"
                   id="verification_face">

            <h3>🔐 Face Verification</h3>

            <video id="video"
                   autoplay
                   playsinline>
            </video>

            <canvas id="canvas"
                    style="display:none">
            </canvas>

            <br>

            <button type="button"
                    onclick="startCamera()">
                📷 Start Camera
            </button>

            <button type="button"
                    onclick="captureVerification()">
                🔐 Capture for Verification
            </button>

            <p id="faceStatus"></p>


            <h3>📍 Geo Location</h3>

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


            <h3>📸 Photo Evidence Upload</h3>

            <input type="file"
                   name="evidence"
                   accept="image/*">


            <h3>📝 Remarks</h3>

            <textarea name="remarks"
                      placeholder="Enter inspection observations">
            </textarea>

            <button type="submit">
                Submit Verified Inspection Report
            </button>

        </form>

    </div>


    <script>

    async function startCamera() {{

        try {{

            const stream =
                await navigator.mediaDevices.getUserMedia({{
                    video: {{ facingMode: "user" }}
                }});

            document.getElementById("video").srcObject =
                stream;

        }} catch(error) {{

            document.getElementById("faceStatus").innerHTML =
                "⚠️ Camera permission is required.";

        }}
    }}


    function captureVerification() {{

        const video =
            document.getElementById("video");

        const canvas =
            document.getElementById("canvas");

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

        document.getElementById("verification_face").value =
            canvas.toDataURL("image/jpeg");

        document.getElementById("faceStatus").innerHTML =
            "✅ Face captured. It will be verified when you submit.";

    }}


    function getLocation() {{

        if (navigator.geolocation) {{

            navigator.geolocation.getCurrentPosition(

                function(position) {{

                    document.getElementById("latitude").value =
                        position.coords.latitude;

                    document.getElementById("longitude").value =
                        position.coords.longitude;

                    document.getElementById("locationStatus").innerHTML =
                        "✅ GPS Location Captured Successfully";

                }},

                function() {{

                    document.getElementById("locationStatus").innerHTML =
                        "⚠️ Unable to capture location";

                }}
            );
        }}
    }}

    </script>
    """)


# ============================================================
# STAFF / WORKER ISSUE REPORT
# ============================================================

@app.route("/staff-report", methods=["GET", "POST"])
@login_required
def staff_report():

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        severity = request.form["severity"]

        conn = get_db()

        conn.execute("""
            INSERT INTO issues(
                title, description, severity,
                status, created_at
            )
            VALUES(?,?,?,?,?)
        """, (
            title,
            description,
            severity,
            "Open",
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        conn.commit()

        admins = conn.execute("""
            SELECT id FROM users
            WHERE role IN ('admin', 'official')
        """).fetchall()

        conn.close()

        for admin in admins:
            notify(
                admin["id"],
                f"⚠️ New staff issue reported: {title}"
            )

        return redirect(url_for("issues"))

    return page("Staff Report", """
    <div class="card">

        <h1>🛠️ Project Staff Work & Issue Report</h1>

        <p>
            Workers and project staff can report
            problems directly from the field.
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
                      placeholder="Describe the issue or field observation"
                      required>
            </textarea>

            <button>Submit Report</button>

        </form>

    </div>
    """)


# ============================================================
# ISSUE VERIFICATION & RESOLUTION
# ============================================================

@app.route("/issues", methods=["GET", "POST"])
@login_required
def issues():

    conn = get_db()

    if (
        request.method == "POST" and
        session["role"] in ["admin", "official", "inspector"]
    ):

        issue_id = request.form["issue_id"]
        resolution = request.form["resolution"]

        conn.execute("""
            UPDATE issues
            SET status='Resolved',
                resolution=?
            WHERE id=?
        """, (
            resolution,
            issue_id
        ))

        conn.commit()

    issues_list = conn.execute("""
        SELECT *
        FROM issues
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    html = "<h1>⚠️ Issue Verification & Resolution</h1>"

    for issue in issues_list:

        action = ""

        if (
            issue["status"] != "Resolved" and
            session["role"] in ["admin", "official", "inspector"]
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
                {issue['title']} —
                {issue['severity']}
            </h3>

            <p>{issue['description']}</p>

            <p>
                <b>Status:</b>
                {issue['status']}
            </p>

            {action}

        </div>
        """

    return page("Issues", html)


# ============================================================
# ATTENDANCE + GPS + FACE VERIFICATION
# ============================================================

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():

    conn = get_db()

    if request.method == "POST":

        face_data = request.form.get("attendance_face")

        verified, message = verify_user_face(
            session["user_id"],
            face_data
        )

        if not verified:

            conn.close()

            return page(
                "Verification Failed",
                f"""
                <div class="login card">
                    <h2>❌ Attendance Not Marked</h2>
                    <p class="danger">{message}</p>
                    <a class="btn" href="/attendance">
                        Try Again
                    </a>
                </div>
                """
            )

        # Prevent duplicate attendance on same day
        existing = conn.execute("""
            SELECT id
            FROM attendance
            WHERE user_id=?
            AND attendance_date=?
        """, (
            session["user_id"],
            datetime.now().strftime("%Y-%m-%d")
        )).fetchone()

        if existing:
            conn.close()

            return page(
                "Attendance",
                """
                <div class="login card">
                    <h2>ℹ️ Attendance Already Marked</h2>
                    <p>You have already marked attendance today.</p>
                    <a class="btn" href="/dashboard">
                        Dashboard
                    </a>
                </div>
                """
            )

        photo = save_file(
            request.files.get("photo")
        )

        conn.execute("""
            INSERT INTO attendance(
                user_id, project_id,
                latitude, longitude,
                photo, attendance_date,
                status
            )
            VALUES(?,?,?,?,?,?,?)
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

        notify(
            session["user_id"],
            "✅ Attendance marked successfully with face verification."
        )

    projects_list = conn.execute(
        "SELECT * FROM projects"
    ).fetchall()

    records = conn.execute("""
        SELECT a.*, u.name user_name,
               p.name project_name
        FROM attendance a
        LEFT JOIN users u ON a.user_id=u.id
        LEFT JOIN projects p ON a.project_id=p.id
        ORDER BY a.id DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    options = "".join(
        f"<option value='{p['id']}'>{p['name']}</option>"
        for p in projects_list
    )

    rows = "".join(f"""
        <tr>
            <td>{r['user_name']}</td>
            <td>{r['project_name'] or '-'}</td>
            <td>{r['attendance_date']}</td>
            <td>{r['status']}</td>
        </tr>
    """ for r in records)

    return page("Attendance", f"""

    <h1>👥 Smart Attendance Management</h1>

    <div class="card">

        <p class="warning">
            🔐 Face verification is required to prevent proxy attendance.
        </p>

        <form method="POST"
              enctype="multipart/form-data">

            <select name="project_id">
                {options}
            </select>

            <input type="hidden"
                   id="alatitude"
                   name="latitude">

            <input type="hidden"
                   id="alongitude"
                   name="longitude">

            <input type="hidden"
                   id="attendance_face"
                   name="attendance_face">


            <h3>🔐 Verify Your Identity</h3>

            <video id="video"
                   autoplay
                   playsinline>
            </video>

            <canvas id="canvas"
                    style="display:none">
            </canvas>

            <br>

            <button type="button"
                    onclick="startCamera()">
                📷 Start Camera
            </button>

            <button type="button"
                    onclick="captureFace()">
                🔐 Capture Face
            </button>

            <p id="faceStatus"></p>


            <h3>📍 GPS Location</h3>

            <button type="button"
                    onclick="attendanceLocation()">
                📍 Capture GPS
            </button>

            <p id="attendanceStatus"></p>


            <label>
                📸 Additional Attendance Photo
            </label>

            <input type="file"
                   name="photo"
                   accept="image/*">

            <button>
                ✅ Verify Face & Mark Attendance
            </button>

        </form>

    </div>


    <div class="card">

        <h2>Recent Attendance Records</h2>

        <table>

            <tr>
                <th>User</th>
                <th>Project</th>
                <th>Date</th>
                <th>Status</th>
            </tr>

            {rows or "<tr><td colspan='4'>No records available.</td></tr>"}

        </table>

    </div>


    <script>

    async function startCamera() {{

        try {{

            const stream =
                await navigator.mediaDevices.getUserMedia({{
                    video: {{ facingMode: "user" }}
                }});

            document.getElementById("video").srcObject =
                stream;

        }} catch(error) {{

            document.getElementById("faceStatus").innerHTML =
                "⚠️ Camera permission is required.";

        }}
    }}


    function captureFace() {{

        const video =
            document.getElementById("video");

        const canvas =
            document.getElementById("canvas");

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context =
            canvas.getContext("2d");

        context.drawImage(
            video,
            0,
            0,
            canvas.width,
            canvas.height
        );

        document.getElementById("attendance_face").value =
            canvas.toDataURL("image/jpeg");

        document.getElementById("faceStatus").innerHTML =
            "✅ Face captured for verification.";

    }}


    function attendanceLocation() {{

        navigator.geolocation.getCurrentPosition(

            function(position) {{

                document.getElementById("alatitude").value =
                    position.coords.latitude;

                document.getElementById("alongitude").value =
                    position.coords.longitude;

                document.getElementById("attendanceStatus").innerHTML =
                    "✅ Location Captured Successfully";

            }},

            function() {{

                document.getElementById("attendanceStatus").innerHTML =
                    "⚠️ Location permission is required.";

            }}
        );
    }}

    </script>
    """)


# ============================================================
# MEETING / VIDEO CONFERENCE
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
                project_id, title,
                meeting_url, meeting_time,
                created_at
            )
            VALUES(?,?,?,?,?)
        """, (
            request.form["project_id"],
            request.form["title"],
            request.form.get("meeting_url"),
            request.form["meeting_time"],
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        conn.commit()

    meetings_list = conn.execute("""
        SELECT m.*, p.name project_name
        FROM meetings m
        LEFT JOIN projects p ON m.project_id=p.id
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

    for m in meetings_list:

        join = ""

        if m["meeting_url"]:
            join = f"""
            <a class='btn'
               target='_blank'
               href='{m["meeting_url"]}'>
               🎥 Join Meeting
            </a>
            """

        cards += f"""
        <div class="card">

            <h3>🎥 {m['title']}</h3>

            <p>🏢 {m['project_name'] or '-'}</p>

            <p>🕒 {m['meeting_time']}</p>

            {join}

        </div>
        """

    return page("Meetings", f"""

    <h1>🎥 Meeting & VC Coordination</h1>

    {form}

    {cards or "<div class='card'>No meetings scheduled.</div>"}
    """)


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
@login_required
def notifications():

    conn = get_db()

    notes = conn.execute("""
        SELECT *
        FROM notifications
        WHERE user_id=?
        ORDER BY id DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.execute("""
        UPDATE notifications
        SET is_read=1
        WHERE user_id=?
    """, (
        session["user_id"],
    ))

    conn.commit()
    conn.close()

    cards = "".join(
        f"""
        <div class='card'>
            <b>🔔 {n['message']}</b><br>
            <small>{n['created_at']}</small>
        </div>
        """
        for n in notes
    )

    return page("Notifications", f"""

    <h1>🔔 Notifications & Alerts</h1>

    {cards or "<div class='card'>No notifications yet.</div>"}
    """)


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
        SELECT COUNT(*)
        FROM issues
        WHERE severity='Critical'
    """).fetchone()[0]

    open_issues = conn.execute("""
        SELECT COUNT(*)
        FROM issues
        WHERE status='Open'
    """).fetchone()[0]

    completed = conn.execute("""
        SELECT COUNT(*)
        FROM inspections
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
        f"<div class='warning'>{a}</div><br>"
        for a in alerts
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
# API - NOTIFICATION COUNT
# ============================================================

@app.route("/api/notification-count")
@login_required
def notification_count():

    conn = get_db()

    count = conn.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE user_id=?
        AND is_read=0
    """, (
        session["user_id"],
    )).fetchone()[0]

    conn.close()

    return jsonify({
        "unread_notifications": count
    })


# ============================================================
# INITIALIZE APPLICATION
# ============================================================

init_db()


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
