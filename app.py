from flask import Flask, request, redirect, url_for, session, send_from_directory, jsonify, render_template_string, abort
import sqlite3
import os
import uuid
import random
from datetime import datetime
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-in-render")

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

STYLE = r"""
<style>
*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#f5f7fb;color:#172033}a{text-decoration:none;color:inherit}.navbar{position:sticky;top:0;z-index:50;background:#fff;border-bottom:1px solid #e7ebf3;padding:14px 5%;display:flex;justify-content:space-between;align-items:center;gap:15px}.brand{display:flex;align-items:center;gap:10px;font-weight:800;color:#172554}.brand-icon{width:38px;height:38px;border-radius:11px;background:#2563eb;color:#fff;display:grid;place-items:center}.navlinks{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.navlinks a{padding:9px 11px;border-radius:9px;color:#475569;font-size:14px}.navlinks a:hover{background:#eef4ff;color:#1d4ed8}.container{max-width:1280px;margin:auto;padding:28px 20px}.hero{background:linear-gradient(135deg,#eff6ff,#fff);border:1px solid #dbeafe;border-radius:26px;padding:58px 28px;text-align:center}.hero h1{font-size:43px;line-height:1.1;color:#17327c;margin:0 auto 16px;max-width:950px}.hero p{font-size:18px;color:#64748b;max-width:820px;margin:0 auto 26px;line-height:1.7}.card{background:#fff;border:1px solid #e7ebf3;border-radius:18px;padding:23px;margin-bottom:20px;box-shadow:0 8px 28px rgba(15,23,42,.05)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:17px}.feature{background:#fff;border:1px solid #e7ebf3;border-radius:18px;padding:21px}.feature-icon{font-size:29px}.feature h3{margin:9px 0 7px;color:#1e3a8a}.feature p{color:#64748b;line-height:1.55}.btn{display:inline-block;border:0;background:#2563eb;color:#fff;padding:10px 16px;border-radius:9px;cursor:pointer;font-weight:700;font-size:14px;margin:3px}.btn:hover{filter:brightness(.95)}.btn-green{background:#059669}.btn-purple{background:#7c3aed}.btn-orange{background:#ea580c}.btn-red{background:#dc2626}.btn-dark{background:#334155}.btn-light{background:#eef4ff;color:#1d4ed8}.section-title{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.section-title h1,.section-title h2{margin:0;color:#172554}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:20px 0}.stat{background:#fff;border:1px solid #e7ebf3;border-radius:16px;padding:18px}.stat .num{font-size:30px;font-weight:800;color:#2563eb}.stat small{color:#64748b}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.field label{display:block;font-weight:700;font-size:14px;margin-bottom:6px;color:#334155}input,select,textarea{width:100%;padding:11px 12px;border:1px solid #cbd5e1;border-radius:9px;font-size:15px;background:#fff}textarea{min-height:110px;resize:vertical}.full{grid-column:1/-1}.info{background:#eff6ff;border:1px solid #bfdbfe;border-left:5px solid #2563eb;padding:13px 15px;border-radius:10px;margin:14px 0;line-height:1.6}.success{background:#ecfdf5;border-color:#a7f3d0;border-left-color:#059669}.warning{background:#fff7ed;border-color:#fed7aa;border-left-color:#ea580c}.danger{background:#fef2f2;border-color:#fecaca;border-left-color:#dc2626}.error{color:#b91c1c;font-weight:700}.badge{display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:800;white-space:nowrap}.low{background:#dcfce7;color:#166534}.medium{background:#fef3c7;color:#92400e}.high{background:#fee2e2;color:#991b1b}.blue{background:#dbeafe;color:#1e40af}.purple{background:#ede9fe;color:#6d28d9}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:850px}th{background:#172554;color:#fff}th,td{padding:11px;border-bottom:1px solid #e5e7eb;text-align:left;vertical-align:middle}tr:hover td{background:#f8fafc}.evidence{width:95px;height:70px;object-fit:cover;border-radius:8px}.workflow{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;align-items:center;font-weight:700;color:#334155}.step{background:#eff6ff;border:1px solid #bfdbfe;padding:10px 13px;border-radius:10px}.footer{text-align:center;color:#64748b;padding:30px}.camera{width:100%;background:#0f172a;border-radius:14px;min-height:280px;object-fit:cover}.login-box{max-width:480px;margin:42px auto}.role{font-size:12px;background:#eef2ff;color:#3730a3;padding:5px 9px;border-radius:999px;font-weight:800}.empty{text-align:center;padding:35px;color:#64748b}.pill-row{display:flex;gap:8px;flex-wrap:wrap}.meeting-code{font-family:monospace;font-size:20px;font-weight:800;letter-spacing:2px}.notice{position:fixed;right:18px;bottom:18px;z-index:100;background:#172554;color:#fff;padding:14px 17px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.2);display:none}.progress{height:10px;background:#e5e7eb;border-radius:99px;overflow:hidden}.progress>span{display:block;height:100%;background:#2563eb}.two-col{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}.checklist{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.mini{font-size:13px;color:#64748b}.metric{font-size:25px;font-weight:800;color:#172554}@media(max-width:850px){.two-col{grid-template-columns:1fr}.checklist{grid-template-columns:1fr 1fr}}@media(max-width:700px){.navbar{align-items:flex-start;flex-direction:column}.hero{padding:40px 17px}.hero h1{font-size:30px}.container{padding:18px 12px}.form-grid{grid-template-columns:1fr}.full{grid-column:auto}.card{padding:17px}.checklist{grid-template-columns:1fr}}
</style>
"""

LAYOUT = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ title or 'SIMMS' }}</title></head><body>
{{ navbar|safe }}
<main class="container">{{ body|safe }}</main>
<div class="footer">SIMMS • Smart Real-Time Monitoring & Inspection System • SIH 26095</div>
</body></html>
"""


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def logged_in():
    return "user_id" in session


def role_required(*roles):
    return logged_in() and session.get("role") in roles


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def esc(value):
    if value is None:
        return ""
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def badge(value, kind="priority"):
    if kind == "priority":
        cls = {"Low": "low", "Medium": "medium", "High": "high"}.get(value, "blue")
    elif kind == "status":
        cls = {"Reported": "high", "In Progress": "medium", "Resolved": "low", "Assigned": "blue", "Accepted": "purple", "Completed": "low"}.get(value, "blue")
    else:
        cls = "blue"
    return f'<span class="badge {cls}">{esc(value)}</span>'


def safe_external_url(value):
    """Allow only normal http/https URLs for stored CCTV links."""
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def page(body, title="SIMMS"):
    return render_template_string(STYLE + LAYOUT, body=body, navbar=nav(), title=title)


def nav():
    if not logged_in():
        return '<div class="navbar"><a class="brand" href="/"><span class="brand-icon">🏛️</span> SIMMS</a><div class="navlinks"><a href="/login">🔐 Login</a></div></div>'

    role = session.get("role")
    links = ['<a href="/home">🏠 Home</a>']
    if role == "Authority":
        links += [
            '<a href="/dashboard">📊 Dashboard</a>',
            '<a href="/assignments">🎲 Assign</a>',
            '<a href="/users">👥 Users</a>',
            '<a href="/analytics">📈 Analytics</a>',
            '<a href="/cctv">📹 CCTV</a>',
            '<a href="/meetings">🎥 Meetings</a>',
        ]
    elif role == "Inspector":
        links += [
            '<a href="/my-inspections">📋 My Inspections</a>',
            '<a href="/meetings">🎥 Meetings</a>',
        ]
    elif role == "Project Staff":
        links += [
            '<a href="/my-work">🛠️ My Work</a>',
            '<a href="/meetings">🎥 Meetings</a>',
        ]
    elif role == "Beneficiary":
        links += [
            '<a href="/beneficiary">🙋 My Services</a>',
            '<a href="/meetings">🎥 Meetings</a>',
        ]
    links.append('<a href="/logout">🚪 Logout</a>')
    return f'<div class="navbar"><a class="brand" href="/home"><span class="brand-icon">🏛️</span> SIMMS</a><div class="navlinks">{"".join(links)}</div></div>'


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Authority','Inspector','Project Staff','Beneficiary')),
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS projects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        project_type TEXT NOT NULL,
        location TEXT NOT NULL,
        contact_name TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS assignments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspector_id INTEGER NOT NULL,
        project_id INTEGER,
        location TEXT NOT NULL,
        instructions TEXT,
        assigned_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Assigned',
        face_verified INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(inspector_id) REFERENCES users(id),
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS work_assignments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        staff_id INTEGER NOT NULL,
        project_id INTEGER,
        title TEXT NOT NULL,
        location TEXT NOT NULL,
        instructions TEXT,
        assigned_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Assigned',
        evidence_photo TEXT,
        latitude TEXT,
        longitude TEXT,
        completed_at TEXT,
        FOREIGN KEY(staff_id) REFERENCES users(id),
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS issues(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER,
        project_id INTEGER,
        location TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Reported',
        priority TEXT NOT NULL DEFAULT 'Low',
        photo TEXT,
        reporter_id INTEGER,
        latitude TEXT,
        longitude TEXT,
        verified INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(assignment_id) REFERENCES assignments(id),
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(reporter_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS cctv_feeds(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        location TEXT NOT NULL,
        feed_url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS meetings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        meeting_url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        created_by INTEGER,
        meeting_code TEXT UNIQUE NOT NULL,
        FOREIGN KEY(created_by) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS meeting_participants(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        joined_at TEXT NOT NULL,
        UNIQUE(meeting_id,user_id),
        FOREIGN KEY(meeting_id) REFERENCES meetings(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        project_id INTEGER,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Present',
        captured_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(project_id) REFERENCES projects(id)
    );
    """)

    defaults = [
        ("ADMIN001", "System Authority", "admin123", "Authority"),
        ("PMU001", "PMU Inspection Officer", "pmu123", "Inspector"),
        ("STAFF001", "Project Staff Demo", "staff123", "Project Staff"),
        ("BEN001", "Beneficiary Demo", "beneficiary123", "Beneficiary"),
    ]
    for uid, name, pwd, role in defaults:
        if conn.execute("SELECT 1 FROM users WHERE unique_id=?", (uid,)).fetchone() is None:
            conn.execute(
                "INSERT INTO users(unique_id,name,password,role,created_at) VALUES(?,?,?,?,?)",
                (uid, name, generate_password_hash(pwd), role, now()),
            )

    if conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO projects(name,project_type,location,contact_name,created_at) VALUES(?,?,?,?,?)",
            ("Demo Social Welfare Institute", "DoSJE Scheme", "Raipur District", "Project Incharge", now()),
        )
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def landing():
    body = '''
    <section class="hero">
      <div class="pill-row" style="justify-content:center"><span class="role">SMART INDIA HACKATHON • SIH 26095</span></div>
      <h1>Smart Real-Time Monitoring & Inspection Mobile App</h1>
      <p>Centralized monitoring for DoSJE schemes with surprise inspections, random PMU inspection assignment, CCTV integration, random VC coordination, geo-tagged evidence and analytics.</p>
      <a class="btn" href="/login">🔐 Login</a>
      <a class="btn btn-light" href="#features">Explore Features</a>
    </section>
    <section id="features" class="grid" style="margin-top:22px">
      <div class="feature"><div class="feature-icon">🎲</div><h3>Random Inspection Assignment</h3><p>Authority can randomly assign inspection duties to eligible PMU/Inspection Team members.</p></div>
      <div class="feature"><div class="feature-icon">📍</div><h3>Geo-Tagged Reports</h3><p>Inspectors can capture latitude, longitude, time and photo evidence with an inspection report.</p></div>
      <div class="feature"><div class="feature-icon">📹</div><h3>CCTV Integration</h3><p>Authorized monitoring URLs can be registered and opened from the central dashboard.</p></div>
      <div class="feature"><div class="feature-icon">🎥</div><h3>Random VC Coordination</h3><p>Authority can create meeting rooms for interaction with project staff and beneficiaries.</p></div>
      <div class="feature"><div class="feature-icon">📊</div><h3>Anomaly Analytics</h3><p>Repeated findings, attendance gaps and inspection activity are summarized for prototype monitoring.</p></div>
      <div class="feature"><div class="feature-icon">👥</div><h3>Role Separation</h3><p>Authority, PMU Inspector, Project Staff and Beneficiary have separate workspaces and permissions.</p></div>
    </section>
    <div class="card" style="margin-top:22px"><h2>SIH 26095 Workflow</h2><div class="workflow"><span class="step">Authority</span>→<span class="step">Random PMU Assignment</span>→<span class="step">Inspect</span>→<span class="step">GPS + Evidence</span>→<span class="step">Analytics</span>→<span class="step">Verify & Resolve</span></div></div>
    <div class="card"><h2>Prototype Roles</h2><div class="grid"><div class="feature"><b>Authority</b><p>DoSJE / State / District monitoring role.</p></div><div class="feature"><b>Inspector</b><p>PMU / Inspection Team member who performs inspections.</p></div><div class="feature"><b>Project Staff</b><p>Project/Institute/NGO-side staff who can participate in coordination and provide updates.</p></div><div class="feature"><b>Beneficiary</b><p>Service beneficiary who can participate in VC/feedback workflows.</p></div></div></div>
    '''
    return page(body, "SIMMS • SIH 26095")


@app.route("/login", methods=["GET", "POST"])
def login():
    if logged_in():
        return redirect(url_for("home"))
    error = ""
    if request.method == "POST":
        uid = request.form.get("unique_id", "").strip().upper()
        password = request.form.get("password", "")
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE unique_id=?", (uid,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        error = "Invalid Unique ID or Password."
    body = f'''
    <div class="card login-box"><div style="text-align:center"><div class="brand-icon" style="margin:auto">🔐</div><h1 style="color:#172554">System Login</h1><p style="color:#64748b">Sign in to your SIH 26095 workspace.</p></div>
    {f'<div class="info danger">❌ {esc(error)}</div>' if error else ''}
    <form method="POST"><div class="field"><label>Unique ID</label><input name="unique_id" placeholder="ADMIN001 / PMU001 / STAFF001 / BEN001" required></div><div class="field" style="margin-top:12px"><label>Password</label><input type="password" name="password" placeholder="Enter password" required></div><button class="btn" style="width:100%;margin-top:12px">Login</button></form>
    <div class="info" style="margin-top:18px"><b>Demo accounts</b><br>Authority: ADMIN001 / admin123<br>PMU Inspector: PMU001 / pmu123<br>Project Staff: STAFF001 / staff123<br>Beneficiary: BEN001 / beneficiary123</div><a href="/">← Back to home</a></div>'''
    return page(body, "Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/home")
def home():
    if not logged_in():
        return redirect(url_for("login"))
    role = session["role"]
    if role == "Authority":
        buttons = '<a class="btn" href="/dashboard">📊 Dashboard</a><a class="btn btn-orange" href="/assignments">🎲 Assign Inspection</a><a class="btn btn-green" href="/assignments-staff-form">🛠️ Assign Staff Work</a><a class="btn btn-purple" href="/users">👥 Users</a><a class="btn btn-dark" href="/attendance">👥 Attendance</a><a class="btn btn-green" href="/projects">🏢 Projects</a>'
        description = "Monitor DoSJE scheme projects, assign PMU inspections and review evidence."
    elif role == "Inspector":
        buttons = '<a class="btn btn-purple" href="/my-inspections">📋 My Inspections</a><a class="btn" href="/meetings">🎥 Meetings</a>'
        description = "Complete assigned PMU/Inspection Team duties with GPS and evidence."
    elif role == "Project Staff":
        buttons = '<a class="btn btn-green" href="/my-work">🛠️ My Work</a><a class="btn" href="/meetings">🎥 Meetings</a>'
        description = "Handle project-side work, submit evidence and participate in coordination."
    else:
        buttons = '<a class="btn btn-purple" href="/beneficiary">🙋 My Services</a><a class="btn" href="/meetings">🎥 Meetings</a>'
        description = "Access beneficiary-side information and coordination."
    body = f'''<div class="card"><div class="section-title"><div><h1>Welcome, {esc(session["name"])} 👋</h1><p style="color:#64748b">{esc(description)}</p></div><span class="role">{esc(role)}</span></div><div class="info">🔐 Role-based access is enabled. Your modules are separated according to the SIH 26095 workflow.</div><div class="pill-row">{buttons}</div></div>'''
    return page(body, "Home")


@app.route("/users", methods=["GET", "POST"])
def users():
    if not role_required("Authority"):
        return "Access denied", 403
    message = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        if not name or len(password) < 4 or role not in ("Authority", "Inspector", "Project Staff", "Beneficiary"):
            message = '<div class="info warning">Enter a valid name, password of at least 4 characters and supported role.</div>'
        else:
            prefix = {"Authority": "AUTH", "Inspector": "PMU", "Project Staff": "STAFF", "Beneficiary": "BEN"}[role]
            uid = prefix + uuid.uuid4().hex[:6].upper()
            conn = db()
            conn.execute("INSERT INTO users(unique_id,name,password,role,created_at) VALUES(?,?,?,?,?)", (uid, name, generate_password_hash(password), role, now()))
            conn.commit()
            conn.close()
            message = f'<div class="info success">✅ User created. ID: <b>{esc(uid)}</b> • Role: <b>{esc(role)}</b></div>'
    conn = db()
    rows = conn.execute("SELECT unique_id,name,role,created_at FROM users ORDER BY id DESC").fetchall()
    conn.close()
    trs = "".join(f'<tr><td>{esc(r["unique_id"])}</td><td>{esc(r["name"])}</td><td>{esc(r["role"])}</td><td>{esc(r["created_at"])}</td></tr>' for r in rows)
    body = f'''<div class="card"><h1>👥 User Management</h1>{message}<form method="POST" class="form-grid"><div class="field"><label>Full Name</label><input name="name" required></div><div class="field"><label>Password</label><input type="password" name="password" required></div><div class="field"><label>Role</label><select name="role"><option>Inspector</option><option>Project Staff</option><option>Beneficiary</option><option>Authority</option></select></div><div class="field" style="display:flex;align-items:end"><button class="btn btn-purple">➕ Create User</button></div></form></div><div class="card"><h2>Registered Users</h2><div class="table-wrap"><table><tr><th>Unique ID</th><th>Name</th><th>Role</th><th>Created</th></tr>{trs}</table></div></div>'''
    return page(body, "Users")


@app.route("/projects", methods=["GET", "POST"])
def projects():
    if not role_required("Authority"):
        return "Access denied", 403
    message = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        project_type = request.form.get("project_type", "").strip()
        location = request.form.get("location", "").strip()
        contact = request.form.get("contact_name", "").strip()
        if not name or not project_type or not location:
            message = '<div class="info warning">Project name, type and location are required.</div>'
        else:
            conn = db()
            conn.execute("INSERT INTO projects(name,project_type,location,contact_name,created_at) VALUES(?,?,?,?,?)", (name, project_type, location, contact, now()))
            conn.commit()
            conn.close()
            message = '<div class="info success">✅ Project/institute registered successfully.</div>'
    conn = db()
    rows = conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
    conn.close()
    trs = "".join(f'<tr><td>{esc(r["name"])}</td><td>{esc(r["project_type"])}</td><td>{esc(r["location"])}</td><td>{esc(r["contact_name"] or "-")}</td></tr>' for r in rows)
    body = f'''<div class="card"><h1>🏢 Projects / Institutes / NGOs</h1>{message}<form method="POST" class="form-grid"><div class="field"><label>Project / Institute / NGO Name</label><input name="name" required></div><div class="field"><label>Scheme / Project Type</label><input name="project_type" placeholder="DoSJE Scheme" required></div><div class="field"><label>Location</label><input name="location" required></div><div class="field"><label>Project Incharge / Contact</label><input name="contact_name"></div><div class="full"><button class="btn btn-green">➕ Register Project</button></div></form></div><div class="card"><h2>Registered Projects</h2><div class="table-wrap"><table><tr><th>Name</th><th>Type</th><th>Location</th><th>Contact</th></tr>{trs or '<tr><td colspan="4" class="empty">No projects registered.</td></tr>'}</table></div></div>'''
    return page(body, "Projects")


@app.route("/assignments", methods=["GET", "POST"])
def assignments():
    if not role_required("Authority"):
        return "Access denied", 403
    message = ""
    conn = db()
    inspectors = conn.execute("SELECT id,name,unique_id FROM users WHERE role='Inspector' ORDER BY name").fetchall()
    projects_rows = conn.execute("SELECT id,name,location FROM projects ORDER BY name").fetchall()

    if request.method == "POST":
        project_id = request.form.get("project_id", "").strip()
        location = request.form.get("location", "").strip()
        instructions = request.form.get("instructions", "").strip()
        selected_id = request.form.get("inspector_id", "random").strip()
        if project_id and project_id.isdigit():
            project = conn.execute("SELECT * FROM projects WHERE id=?", (int(project_id),)).fetchone()
            if project:
                location = project["location"]
        else:
            project = None
        if not location:
            message = '<div class="info warning">Select a project or enter a location.</div>'
        elif not inspectors:
            message = '<div class="info warning">No Inspector / PMU Team accounts are available.</div>'
        else:
            if selected_id == "random":
                selected = random.choice(inspectors)
            else:
                selected = conn.execute("SELECT id,name,unique_id FROM users WHERE id=? AND role='Inspector'", (selected_id,)).fetchone()
                if not selected:
                    message = '<div class="info danger">Invalid Inspector selection.</div>'
            if selected and not message:
                conn.execute("INSERT INTO assignments(inspector_id,project_id,location,instructions,assigned_at,status,face_verified) VALUES(?,?,?,?,?,?,0)", (selected["id"], int(project_id) if project_id.isdigit() else None, location, instructions, now(), "Assigned"))
                conn.commit()
                message = f'<div class="info success">🎲 Inspection assigned to <b>{esc(selected["name"])}</b> ({esc(selected["unique_id"])}). Worker/Project Staff accounts are not included in PMU inspection assignment.</div>'

    rows = conn.execute("""
        SELECT a.*,u.name inspector_name,u.unique_id, p.name project_name
        FROM assignments a JOIN users u ON a.inspector_id=u.id
        LEFT JOIN projects p ON a.project_id=p.id
        ORDER BY a.id DESC
    """).fetchall()
    conn.close()
    inspector_options = '<option value="random">🎲 Randomly select Inspector</option>' + "".join(f'<option value="{r["id"]}">{esc(r["name"])} ({esc(r["unique_id"])})</option>' for r in inspectors)
    trs = "".join(f'<tr><td>🔍 Inspection</td><td>{esc(r["project_name"] or "-")}</td><td>{esc(r["location"])}</td><td>{esc(r["inspector_name"])}</td><td>{esc(r["unique_id"])}</td><td>{badge(r["status"],"status")}</td><td>{esc(r["assigned_at"])}</td></tr>' for r in rows)
    body = f'''<div class="card"><h1>🎲 Random PMU Inspection Assignment</h1><p style="color:#64748b">This module assigns <b>inspection duties only to PMU/Inspection Team (Inspector) accounts</b>. Project Staff are handled separately under Work Assignments.</p>{message}<form method="POST" class="form-grid"><div class="field"><label>Project / Institute / NGO</label><select name="project_id"><option value="">-- Select project --</option>{''.join(f'<option value="{p["id"]}">{esc(p["name"])} — {esc(p["location"])}</option>' for p in projects_rows)}</select></div><div class="field"><label>Inspector</label><select name="inspector_id" required>{inspector_options}</select></div><div class="field"><label>Location (used if no project selected)</label><input name="location" placeholder="District / Institute location"></div><div class="field"><label>Inspection Instructions</label><input name="instructions" placeholder="Check facilities, attendance, records..."></div><div class="full"><button class="btn btn-purple">🎲 Assign Inspection</button></div></form></div><div class="card"><h2>📋 Inspection Assignment History</h2><div class="table-wrap"><table><tr><th>Type</th><th>Project</th><th>Location</th><th>Assigned Inspector</th><th>ID</th><th>Status</th><th>Assigned</th></tr>{trs or '<tr><td colspan="7" class="empty">No inspection assignments yet.</td></tr>'}</table></div></div>'''
    return page(body, "Inspection Assignments")


@app.route("/my-inspections")
def my_inspections():
    if not role_required("Inspector"):
        return "Access denied", 403
    conn = db()
    rows = conn.execute("SELECT a.*,p.name project_name FROM assignments a LEFT JOIN projects p ON a.project_id=p.id WHERE a.inspector_id=? ORDER BY a.id DESC", (session["user_id"],)).fetchall()
    conn.close()
    trs = ""
    for r in rows:
        if r["status"] == "Completed":
            action = '<span class="badge low">✅ Completed</span>'
        elif r["face_verified"]:
            action = f'<a class="btn btn-green" href="/inspection/{r["id"]}">📋 Start Inspection</a>'
        else:
            action = f'<a class="btn btn-purple" href="/face-verification/{r["id"]}">📷 Verify Identity</a>'
        verification = '<span class="badge low">✅ Verified</span>' if r["face_verified"] else '<span class="badge medium">⏳ Required</span>'
        trs += f'<tr><td>🔍 Inspection</td><td>{esc(r["project_name"] or "-")}</td><td>📍 {esc(r["location"])}</td><td>{verification}</td><td>{badge(r["status"],"status")}</td><td>{esc(r["assigned_at"])}</td><td>{action}</td></tr>'
    body = f'''<div class="card"><div class="section-title"><h1>📋 My Inspection Assignments</h1><span class="role">PMU / Inspection Team</span></div><div class="info">Only inspection assignments belonging to your Inspector account are shown here. Project Staff assignments never appear on this page.</div><div class="table-wrap"><table><tr><th>Type</th><th>Project</th><th>Location</th><th>Identity</th><th>Status</th><th>Assigned</th><th>Action</th></tr>{trs or '<tr><td colspan="7" class="empty">📭 No inspection assignments available.</td></tr>'}</table></div></div>'''
    return page(body, "My Inspections")


@app.route("/face-verification/<int:assignment_id>", methods=["GET", "POST"])
def face_verification(assignment_id):
    if not role_required("Inspector"):
        return "Access denied", 403
    conn = db()
    assignment = conn.execute("SELECT * FROM assignments WHERE id=? AND inspector_id=? AND status='Assigned'", (assignment_id, session["user_id"])).fetchone()
    if not assignment:
        conn.close()
        return "Invalid assignment", 403
    if request.method == "POST":
        photo = request.files.get("face_photo")
        if not photo or not photo.filename:
            conn.close()
            return "Please capture your face photo.", 400
        if not allowed_file(photo.filename):
            conn.close()
            return "Invalid image format.", 400
        filename = "face_" + str(session["user_id"]) + "_" + uuid.uuid4().hex + ".jpg"
        photo.save(os.path.join(FACE_FOLDER, filename))
        conn.execute("UPDATE assignments SET face_verified=1 WHERE id=? AND inspector_id=?", (assignment_id, session["user_id"]))
        conn.commit()
        conn.close()
        return redirect(url_for("inspection", assignment_id=assignment_id))
    conn.close()
    body = f'''<div class="card" style="max-width:700px;margin:auto"><h1>📷 Inspector Identity Verification</h1><div class="info">Assigned location: <b>{esc(assignment["location"])}</b><br>This prototype records a camera capture as an identity-verification step. It does not perform biometric face matching.</div><div class="video-box"><video id="video" class="camera" autoplay playsinline></video></div><canvas id="canvas" hidden></canvas><form id="faceForm" method="POST" enctype="multipart/form-data"><input id="face_photo" name="face_photo" type="file" accept="image/*" hidden><button type="button" class="btn btn-purple" onclick="captureFace()">📸 Capture & Verify</button></form><p id="message" class="error"></p></div><script>
const video=document.getElementById('video');
if(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia){{navigator.mediaDevices.getUserMedia({{video:true}}).then(stream=>{{video.srcObject=stream;}}).catch(()=>{{document.getElementById('message').textContent='❌ Camera access denied. Please allow camera permission.';}});}}else{{document.getElementById('message').textContent='❌ Camera is not supported by this browser.';}}
function captureFace(){{if(!video.videoWidth){{alert('Please wait for the camera to start.');return;}}const canvas=document.getElementById('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);canvas.toBlob(blob=>{{if(!blob){{alert('Could not capture image.');return;}}const file=new File([blob],'face.jpg',{{type:'image/jpeg'}});const dt=new DataTransfer();dt.items.add(file);document.getElementById('face_photo').files=dt.files;const stream=video.srcObject;if(stream)stream.getTracks().forEach(t=>t.stop());document.getElementById('faceForm').submit();}},'image/jpeg');}}
</script>'''
    return page(body, "Identity Verification")


@app.route("/inspection/<int:assignment_id>", methods=["GET", "POST"])
def inspection(assignment_id):
    if not role_required("Inspector"):
        return "Access denied", 403
    conn = db()
    assignment = conn.execute("SELECT * FROM assignments WHERE id=? AND inspector_id=? AND face_verified=1 AND status='Assigned'", (assignment_id, session["user_id"])).fetchone()
    if not assignment:
        conn.close()
        return "Inspection access denied", 403

    if request.method == "POST":
        cleanliness = request.form.get("cleanliness", "Yes")
        safety = request.form.get("safety", "Yes")
        facilities = request.form.get("facilities", "Yes")
        attendance_ok = request.form.get("attendance_ok", "Yes")
        records_ok = request.form.get("records_ok", "Yes")
        description = request.form.get("description", "").strip()
        lat = request.form.get("latitude", "").strip()
        lon = request.form.get("longitude", "").strip()
        photo_name = None
        photo = request.files.get("photo")

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                conn.close()
                return "Invalid photo format.", 400
            safe_name = secure_filename(photo.filename)
            ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else "jpg"
            photo_name = uuid.uuid4().hex + "." + ext
            photo.save(os.path.join(UPLOAD_FOLDER, photo_name))

        checks = [
            ("Cleanliness", cleanliness),
            ("Safety", safety),
            ("Facilities", facilities),
            ("Attendance", attendance_ok),
            ("Records", records_ok),
        ]
        detected = [label for label, answer in checks if answer == "No"]
        if detected and not description:
            description = "Issues detected during inspection: " + ", ".join(detected)

        project_id = assignment["project_id"]
        for issue_type in detected:
            count_query = "SELECT COUNT(*) FROM issues WHERE LOWER(location)=LOWER(?)"
            count = conn.execute(count_query, (assignment["location"],)).fetchone()[0] + 1
            priority = "High" if count > 3 else "Medium" if count >= 2 else "Low"
            conn.execute("""INSERT INTO issues(assignment_id,project_id,location,issue_type,description,created_at,status,priority,photo,reporter_id,latitude,longitude,verified)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,0)""", (assignment_id, project_id, assignment["location"], issue_type, description, now(), "Reported", priority, photo_name, session["user_id"], lat, lon))

        conn.execute("UPDATE assignments SET status='Completed' WHERE id=? AND inspector_id=?", (assignment_id, session["user_id"]))
        conn.commit()
        conn.close()
        result = "⚠️ Issues reported: " + ", ".join(detected) if detected else "✅ Inspection completed. No issues found."
        body = f'<div class="card" style="text-align:center"><h1>✅ Inspection Submitted</h1><div class="info success">📍 {esc(assignment["location"])}<br><br>{esc(result)}</div><a class="btn" href="/my-inspections">📋 My Inspections</a><a class="btn btn-green" href="/dashboard">📊 Dashboard</a></div>'
        return page(body, "Inspection Submitted")

    conn.close()
    body = f'''<div class="card"><h1>📋 PMU Field Inspection</h1><div class="info">📍 Location: <b>{esc(assignment["location"])}</b><br>🔐 Identity Verification: <b>Completed ✅</b><br>📝 Instructions: <b>{esc(assignment["instructions"] or "Follow the standard inspection checklist.")}</b></div><form method="POST" enctype="multipart/form-data" class="form-grid"><div class="field"><label>🧹 Is the area clean?</label><select name="cleanliness"><option>Yes</option><option>No</option></select></div><div class="field"><label>🛡️ Is the area safe?</label><select name="safety"><option>Yes</option><option>No</option></select></div><div class="field"><label>🏢 Are facilities working?</label><select name="facilities"><option>Yes</option><option>No</option></select></div><div class="field"><label>👥 Is attendance satisfactory?</label><select name="attendance_ok"><option>Yes</option><option>No</option></select></div><div class="field"><label>📄 Are records available/correct?</label><select name="records_ok"><option>Yes</option><option>No</option></select></div><div class="field"><label>📸 Photo Evidence</label><input type="file" name="photo" accept="image/*"></div><div class="field"><label>Latitude</label><input id="latitude" name="latitude" placeholder="Latitude"></div><div class="field"><label>Longitude</label><input id="longitude" name="longitude" placeholder="Longitude"></div><div class="full"><button type="button" class="btn btn-purple" onclick="getLocation()">📍 Get Current Location</button></div><div class="field full"><label>📝 Inspection Remarks</label><textarea name="description" placeholder="Describe observations, deficiencies and evidence..."></textarea></div><div class="full"><button class="btn" type="submit">📤 Submit Inspection Report</button></div></form></div><script>
function getLocation(){{if(!navigator.geolocation){{alert('Geolocation is not supported by this browser.');return;}}navigator.geolocation.getCurrentPosition(position=>{{document.getElementById('latitude').value=position.coords.latitude;document.getElementById('longitude').value=position.coords.longitude;}},()=>alert('Please allow location permission.'));}}
</script>'''
    return page(body, "Field Inspection")


@app.route("/my-work", methods=["GET", "POST"])
def my_work():
    if not role_required("Project Staff"):
        return "Access denied", 403
    conn = db()
    message = ""
    if request.method == "POST":
        work_id = request.form.get("work_id", "").strip()
        action = request.form.get("action", "")
        work = conn.execute("SELECT * FROM work_assignments WHERE id=? AND staff_id=?", (work_id, session["user_id"])).fetchone()
        if not work:
            message = '<div class="info danger">Invalid work assignment.</div>'
        elif action == "accept" and work["status"] == "Assigned":
            conn.execute("UPDATE work_assignments SET status='Accepted' WHERE id=?", (work_id,))
            conn.commit()
            message = '<div class="info success">✅ Work accepted.</div>'
        elif action == "complete" and work["status"] in ("Assigned", "Accepted"):
            photo = request.files.get("evidence_photo")
            photo_name = None
            if photo and photo.filename:
                if not allowed_file(photo.filename):
                    conn.close()
                    return "Invalid image format.", 400
                safe_name = secure_filename(photo.filename)
                ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else "jpg"
                photo_name = uuid.uuid4().hex + "." + ext
                photo.save(os.path.join(UPLOAD_FOLDER, photo_name))
            lat = request.form.get("latitude", "").strip()
            lon = request.form.get("longitude", "").strip()
            conn.execute("UPDATE work_assignments SET status='Completed',evidence_photo=?,latitude=?,longitude=?,completed_at=? WHERE id=?", (photo_name, lat, lon, now(), work_id))
            conn.commit()
            message = '<div class="info success">✅ Work completed and evidence submitted.</div>'
    rows = conn.execute("SELECT w.*,p.name project_name FROM work_assignments w LEFT JOIN projects p ON w.project_id=p.id WHERE w.staff_id=? ORDER BY w.id DESC", (session["user_id"],)).fetchall()
    conn.close()
    cards = ""
    for r in rows:
        if r["status"] == "Completed":
            action = '<span class="badge low">✅ Completed</span>'
        else:
            action = f'''<form method="POST" enctype="multipart/form-data" style="margin-top:10px"><input type="hidden" name="work_id" value="{r["id"]}"><div class="field"><label>Evidence photo (optional)</label><input type="file" name="evidence_photo" accept="image/*"></div><div class="form-grid"><div class="field"><label>Latitude</label><input name="latitude"></div><div class="field"><label>Longitude</label><input name="longitude"></div></div>{('<button class="btn btn-light" name="action" value="accept">Accept Work</button>' if r["status"] == "Assigned" else '')}<button class="btn btn-green" name="action" value="complete">Complete Work</button></form>'''
        photo = f'<img class="evidence" src="/uploads/{esc(r["evidence_photo"])}">' if r["evidence_photo"] else ''
        cards += f'''<div class="feature"><span class="badge purple">🛠️ Project Staff Work</span><h3>{esc(r["title"])}</h3><p><b>Project:</b> {esc(r["project_name"] or "-")}<br><b>Location:</b> {esc(r["location"])}<br><b>Instructions:</b> {esc(r["instructions"] or "-")}<br><b>Status:</b> {badge(r["status"],"status")}</p>{photo}{action}</div>'''
    body = f'''<div class="card"><div class="section-title"><h1>🛠️ My Work Assignments</h1><span class="role">Project / Institute Staff</span></div><div class="info">This is a separate work area for Project Staff. These assignments are <b>not</b> PMU inspection assignments and never appear in the Inspector's inspection list.</div>{message}<div class="grid">{cards or '<div class="empty">📭 No work assignments available.</div>'}</div></div>'''
    return page(body, "My Work")


@app.route("/staff-assignments", methods=["POST"])
def staff_assignments():
    if not role_required("Authority"):
        return "Access denied", 403
    staff_id = request.form.get("staff_id", "").strip()
    project_id = request.form.get("project_id", "").strip()
    title = request.form.get("title", "").strip()
    location = request.form.get("location", "").strip()
    instructions = request.form.get("instructions", "").strip()
    if not staff_id or not title or not location:
        return redirect(url_for("assignments") + "#staff-work")
    conn = db()
    staff = conn.execute("SELECT id FROM users WHERE id=? AND role='Project Staff'", (staff_id,)).fetchone()
    if not staff:
        conn.close()
        return "Invalid Project Staff account", 400
    conn.execute("INSERT INTO work_assignments(staff_id,project_id,title,location,instructions,assigned_at,status) VALUES(?,?,?,?,?,?,?)", (staff_id, int(project_id) if project_id.isdigit() else None, title, location, instructions, now(), "Assigned"))
    conn.commit()
    conn.close()
    return redirect(url_for("assignments") + "#staff-work")


@app.route("/beneficiary")
def beneficiary():
    if not role_required("Beneficiary"):
        return "Access denied", 403
    conn = db()
    projects_rows = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
    conn.close()
    rows = "".join(f'<tr><td>{esc(p["name"])}</td><td>{esc(p["project_type"])}</td><td>{esc(p["location"])}</td><td>{esc(p["contact_name"] or "Project Incharge")}</td></tr>' for p in projects_rows)
    body = f'''<div class="card"><h1>🙋 Beneficiary Workspace</h1><div class="info">This prototype provides a simple beneficiary-side view for project/service information and random VC coordination.</div><h2>Available Projects / Institutes</h2><div class="table-wrap"><table><tr><th>Project</th><th>Scheme</th><th>Location</th><th>Contact</th></tr>{rows or '<tr><td colspan="4" class="empty">No project information available.</td></tr>'}</table></div><a class="btn btn-purple" href="/meetings">🎥 View Available VC Meetings</a></div>'''
    return page(body, "Beneficiary")


@app.route("/assignments-staff-form")
def assignments_staff_form():
    if not role_required("Authority"):
        return "Access denied", 403
    conn = db()
    staff = conn.execute("SELECT id,name,unique_id FROM users WHERE role='Project Staff' ORDER BY name").fetchall()
    projects_rows = conn.execute("SELECT id,name,location FROM projects ORDER BY name").fetchall()
    conn.close()
    staff_options = "".join(f'<option value="{s["id"]}">{esc(s["name"])} ({esc(s["unique_id"])})</option>' for s in staff)
    project_options = '<option value="">-- Optional --</option>' + "".join(f'<option value="{p["id"]}">{esc(p["name"])} — {esc(p["location"])}</option>' for p in projects_rows)
    body = f'''<div class="card"><h1>🛠️ Assign Project Staff Work</h1><div class="info">This is intentionally separate from PMU Inspection Assignment. Authority can assign project-side operational/support work to Project Staff.</div><form method="POST" action="/staff-assignments" class="form-grid"><div class="field"><label>Project Staff</label><select name="staff_id" required>{staff_options or '<option value="">No Project Staff accounts</option>'}</select></div><div class="field"><label>Project</label><select name="project_id">{project_options}</select></div><div class="field"><label>Work Title</label><input name="title" placeholder="Update beneficiary attendance records" required></div><div class="field"><label>Location</label><input name="location" required></div><div class="field full"><label>Instructions</label><textarea name="instructions"></textarea></div><div class="full"><button class="btn btn-green">🛠️ Assign Staff Work</button></div></form></div>'''
    return page(body, "Assign Staff Work")


@app.route("/dashboard")
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))
    conn = db()
    query = "SELECT i.*,u.name reporter_name,p.name project_name FROM issues i LEFT JOIN users u ON i.reporter_id=u.id LEFT JOIN projects p ON i.project_id=p.id"
    params = ()
    if session["role"] == "Inspector":
        query += " WHERE i.reporter_id=?"
        params = (session["user_id"],)
    elif session["role"] != "Authority":
        conn.close()
        return "Access denied", 403
    query += " ORDER BY i.id DESC"
    issues = conn.execute(query, params).fetchall()
    counts = conn.execute("SELECT COUNT(*) total, SUM(status='Reported') reported, SUM(status='In Progress') progress, SUM(status='Resolved') resolved, SUM(priority='High') high FROM issues").fetchone()
    assignment_count = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
    conn.close()
    total = counts["total"] or 0
    reported = counts["reported"] or 0
    progress = counts["progress"] or 0
    resolved = counts["resolved"] or 0
    high = counts["high"] or 0
    trs = ""
    for i in issues:
        photo = f'<a href="/uploads/{esc(i["photo"])}" target="_blank"><img class="evidence" src="/uploads/{esc(i["photo"])}"></a>' if i["photo"] else "—"
        loc = esc(i["location"])
        if i["latitude"] and i["longitude"]:
            loc += f'<br><small>📍 {esc(i["latitude"])}, {esc(i["longitude"])}</small>'
        if session["role"] == "Authority":
            verify = "" if i["verified"] else f'<a class="btn btn-purple" href="/verify/{i["id"]}">🔍 Verify</a>'
            if i["status"] == "Reported":
                status_action = f'<a class="btn btn-orange" href="/update/{i["id"]}/In%20Progress">🟡 Start</a>'
            elif i["status"] == "In Progress":
                status_action = f'<a class="btn btn-green" href="/update/{i["id"]}/Resolved">✅ Resolve</a>'
            else:
                status_action = "✅ Resolved"
            action = verify + " " + status_action
        else:
            action = "🔒 View Only"
        trs += f'<tr><td>{esc(i["project_name"] or "-")}</td><td>{loc}</td><td>{esc(i["issue_type"])}</td><td>{esc(i["description"] or "-")}</td><td>{badge(i["priority"])}</td><td>{photo}</td><td>{badge(i["status"],"status")}</td><td>{esc(i["created_at"])}</td><td>{action}</td></tr>'
    body = f'''<div class="section-title"><div><h1>📊 Real-Time Monitoring Dashboard</h1><p style="color:#64748b">Central monitoring of PMU inspection findings and corrective status.</p></div><span class="role">DoSJE Monitoring</span></div><div class="stats"><div class="stat"><div class="num">{total}</div><small>Total Issues</small></div><div class="stat"><div class="num">{reported}</div><small>🔴 Reported</small></div><div class="stat"><div class="num">{progress}</div><small>🟡 In Progress</small></div><div class="stat"><div class="num">{resolved}</div><small>🟢 Resolved</small></div><div class="stat"><div class="num">{high}</div><small>🔴 High Priority</small></div><div class="stat"><div class="num">{assignment_count}</div><small>🎲 Inspections Assigned</small></div></div><div class="card"><h2>🚨 Inspection Reports</h2><div class="table-wrap"><table><tr><th>Project</th><th>Location + GPS</th><th>Issue</th><th>Description</th><th>Priority</th><th>Evidence</th><th>Status</th><th>Time</th><th>Action</th></tr>{trs or '<tr><td colspan="9" class="empty">🎉 No inspection issues found.</td></tr>'}</table></div></div>'''
    return page(body, "Monitoring Dashboard")


@app.route("/verify/<int:issue_id>")
def verify_issue(issue_id):
    if not role_required("Authority"):
        return "Access denied", 403
    conn = db()
    conn.execute("UPDATE issues SET verified=1 WHERE id=?", (issue_id,))
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
    conn.execute("UPDATE issues SET status=? WHERE id=?", (status, issue_id))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/analytics")
def analytics():
    if not role_required("Authority"):
        return "Access denied", 403
    conn = db()
    locations = conn.execute("SELECT location,COUNT(*) reports FROM issues GROUP BY location ORDER BY reports DESC").fetchall()
    inspectors = conn.execute("""SELECT u.name,u.unique_id,COUNT(a.id) assignments,
        SUM(CASE WHEN a.status='Completed' THEN 1 ELSE 0 END) completed
        FROM users u LEFT JOIN assignments a ON u.id=a.inspector_id
        WHERE u.role='Inspector' GROUP BY u.id ORDER BY assignments DESC""").fetchall()
    attendance = conn.execute("""SELECT u.name,u.unique_id,COUNT(at.id) records,
        SUM(CASE WHEN at.status='Present' THEN 1 ELSE 0 END) present
        FROM users u LEFT JOIN attendance at ON u.id=at.user_id
        WHERE u.role IN ('Project Staff','Beneficiary') GROUP BY u.id ORDER BY records DESC""").fetchall()
    repeated = conn.execute("SELECT location,COUNT(*) count FROM issues GROUP BY location HAVING COUNT(*)>=2 ORDER BY count DESC").fetchall()
    conn.close()
    locrows = "".join(f'<tr><td>{esc(x["location"])}</td><td>{x["reports"]}</td><td>{badge("High" if x["reports"]>3 else "Medium" if x["reports"]>=2 else "Low")}</td></tr>' for x in locations) or '<tr><td colspan="3" class="empty">No issue data.</td></tr>'
    irows = "".join(f'<tr><td>{esc(x["name"])}</td><td>{esc(x["unique_id"])}</td><td>{x["assignments"] or 0}</td><td>{x["completed"] or 0}</td></tr>' for x in inspectors) or '<tr><td colspan="4" class="empty">No Inspector data.</td></tr>'
    arows = "".join(f'<tr><td>{esc(x["name"])}</td><td>{esc(x["unique_id"])}</td><td>{x["records"] or 0}</td><td>{x["present"] or 0}</td></tr>' for x in attendance) or '<tr><td colspan="4" class="empty">No attendance records. Prototype analytics is ready for future attendance integration.</td></tr>'
    anomaly_text = ", ".join(f'{esc(x["location"])} ({x["count"]} findings)' for x in repeated) or "No repeated-location anomaly detected yet."
    body = f'''<div class="card"><h1>📈 AI/Automation Analytics Prototype</h1><div class="info">The current prototype uses explainable rule-based analytics: repeated findings at the same location increase priority, and attendance records can be summarized. This avoids claiming a trained AI model where none is installed.</div><div class="grid"><div class="feature"><div class="metric">{len(repeated)}</div><div class="mini">Repeated-location anomaly groups</div></div><div class="feature"><div class="metric">{len(inspectors)}</div><div class="mini">PMU Inspectors</div></div><div class="feature"><div class="metric">{sum((x["completed"] or 0) for x in inspectors)}</div><div class="mini">Completed inspections</div></div></div><h2>🔎 Anomaly Signal</h2><p>{anomaly_text}</p></div><div class="card"><h2>📍 Findings by Location</h2><div class="table-wrap"><table><tr><th>Location</th><th>Reports</th><th>Prototype Priority</th></tr>{locrows}</table></div></div><div class="card"><h2>🔍 PMU Inspection Activity</h2><div class="table-wrap"><table><tr><th>Inspector</th><th>ID</th><th>Assigned</th><th>Completed</th></tr>{irows}</table></div></div><div class="card"><h2>👥 Attendance Analytics</h2><div class="table-wrap"><table><tr><th>Person</th><th>ID</th><th>Records</th><th>Present</th></tr>{arows}</table></div></div>'''
    return page(body, "Analytics")


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if not role_required("Authority"):
        return "Access denied", 403
    conn = db()
    message = ""
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        project_id = request.form.get("project_id", "").strip()
        status = request.form.get("status", "Present")
        if not user_id.isdigit() or status not in ("Present", "Absent"):
            message = '<div class="info warning">Select a valid person and attendance status.</div>'
        else:
            person = conn.execute("SELECT id FROM users WHERE id=? AND role IN ('Project Staff','Beneficiary')", (int(user_id),)).fetchone()
            if not person:
                message = '<div class="info danger">Attendance can only be recorded for Project Staff or Beneficiary accounts.</div>'
            else:
                conn.execute("INSERT INTO attendance(user_id,project_id,attendance_date,status,captured_at) VALUES(?,?,?,?,?)", (int(user_id), int(project_id) if project_id.isdigit() else None, datetime.now().strftime("%Y-%m-%d"), status, now()))
                conn.commit()
                message = '<div class="info success">✅ Attendance record saved.</div>'
    people = conn.execute("SELECT id,name,unique_id,role FROM users WHERE role IN ('Project Staff','Beneficiary') ORDER BY name").fetchall()
    projects_rows = conn.execute("SELECT id,name FROM projects ORDER BY name").fetchall()
    rows = conn.execute("""SELECT at.*,u.name,u.unique_id,u.role,p.name project_name FROM attendance at JOIN users u ON at.user_id=u.id LEFT JOIN projects p ON at.project_id=p.id ORDER BY at.id DESC LIMIT 100""").fetchall()
    conn.close()
    people_options = "".join(f'<option value="{p["id"]}">{esc(p["name"])} ({esc(p["unique_id"])}) — {esc(p["role"])}</option>' for p in people)
    project_options = '<option value="">-- Optional project --</option>' + "".join(f'<option value="{p["id"]}">{esc(p["name"])}</option>' for p in projects_rows)
    trs = "".join(f'<tr><td>{esc(r["name"])}</td><td>{esc(r["role"])}</td><td>{esc(r["project_name"] or "-")}</td><td>{esc(r["attendance_date"])}</td><td>{badge(r["status"],"status")}</td><td>{esc(r["captured_at"])}</td></tr>' for r in rows)
    body = f'''<div class="card"><h1>👥 Attendance Capture</h1>{message}<form method="POST" class="form-grid"><div class="field"><label>Project Staff / Beneficiary</label><select name="user_id" required>{people_options or '<option value="">No eligible accounts</option>'}</select></div><div class="field"><label>Project</label><select name="project_id">{project_options}</select></div><div class="field"><label>Status</label><select name="status"><option>Present</option><option>Absent</option></select></div><div class="field" style="display:flex;align-items:end"><button class="btn btn-green">💾 Save Attendance</button></div></form></div><div class="card"><h2>Recent Attendance</h2><div class="table-wrap"><table><tr><th>Name</th><th>Role</th><th>Project</th><th>Date</th><th>Status</th><th>Captured</th></tr>{trs or '<tr><td colspan="6" class="empty">No attendance records.</td></tr>'}</table></div></div>'''
    return page(body, "Attendance")


@app.route("/cctv", methods=["GET", "POST"])
def cctv():
    if not role_required("Authority"):
        return "Access denied", 403
    conn = db()
    message = ""
    if request.method == "POST":
        location = request.form.get("location", "").strip()
        feed = request.form.get("feed_url", "").strip()
        project_id = request.form.get("project_id", "").strip()
        if not location or not feed or not safe_external_url(feed):
            message = '<div class="info warning">Enter a location and a valid http/https monitoring URL.</div>'
        else:
            conn.execute("INSERT INTO cctv_feeds(project_id,location,feed_url,created_at) VALUES(?,?,?,?)", (int(project_id) if project_id.isdigit() else None, location, feed, now()))
            conn.commit()
            message = '<div class="info success">✅ CCTV feed added.</div>'
    feeds = conn.execute("SELECT c.*,p.name project_name FROM cctv_feeds c LEFT JOIN projects p ON c.project_id=p.id ORDER BY c.id DESC").fetchall()
    projects_rows = conn.execute("SELECT id,name FROM projects ORDER BY name").fetchall()
    conn.close()
    project_options = '<option value="">-- Optional project --</option>' + "".join(f'<option value="{p["id"]}">{esc(p["name"])}</option>' for p in projects_rows)
    rows = "".join(f'<tr><td>{esc(f["project_name"] or "-")}</td><td>{esc(f["location"])}</td><td>{esc(f["created_at"])}</td><td><a class="btn" href="{esc(f["feed_url"])}" target="_blank" rel="noopener noreferrer">📹 Open Feed</a></td></tr>' for f in feeds) or '<tr><td colspan="4" class="empty">No CCTV feeds configured.</td></tr>'
    body = f'''<div class="card"><h1>📹 CCTV Monitoring Integration</h1>{message}<div class="info">For the prototype, CCTV is represented by authorized external monitoring URLs. A real camera stream requires a compatible stream/provider endpoint; this page does not pretend to generate a live camera feed.</div><form class="form-grid" method="POST"><div class="field"><label>Project / Institute</label><select name="project_id">{project_options}</select></div><div class="field"><label>Camera Location</label><input name="location" required></div><div class="field full"><label>Authorized Monitoring URL</label><input type="url" name="feed_url" placeholder="https://example.com/camera" required></div><div class="full"><button class="btn">➕ Add CCTV Feed</button></div></form></div><div class="card"><h2>Configured Feeds</h2><div class="table-wrap"><table><tr><th>Project</th><th>Location</th><th>Added</th><th>Feed</th></tr>{rows}</table></div></div>'''
    return page(body, "CCTV")


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
        title = request.form.get("title", "").strip()
        if not title:
            message = '<div class="info warning">Enter a meeting title.</div>'
        else:
            code = uuid.uuid4().hex[:10].upper()
            meeting_url = url_for("meeting_room", meeting_code=code, _external=True)
            conn.execute("INSERT INTO meetings(title,meeting_url,created_at,created_by,meeting_code) VALUES(?,?,?,?,?)", (title, meeting_url, now(), session["user_id"], code))
            conn.commit()
            message = f'<div class="info success">🎉 Meeting created: <b>{esc(title)}</b><br>Meeting code: <span class="meeting-code">{esc(code)}</span></div>'
    meetings_list = conn.execute("SELECT m.*,u.name authority_name FROM meetings m LEFT JOIN users u ON m.created_by=u.id ORDER BY m.id DESC").fetchall()
    conn.close()
    form = ''
    if session["role"] == "Authority":
        form = '<div class="card"><h1>🎥 Create Random VC Meeting</h1><p style="color:#64748b">Create a prototype coordination room for interaction with Project Incharge/Staff/Beneficiaries.</p><form method="POST"><div class="field"><label>Meeting Title</label><input name="title" placeholder="Random Project Staff / Beneficiary VC" required></div><button class="btn btn-purple">🔔 Create Meeting</button></form></div>'
    rows = "".join(f'<tr><td>{esc(m["title"])}</td><td>{esc(m["authority_name"] or "Authority")}</td><td>{esc(m["created_at"])}</td><td><a class="btn btn-purple" href="{esc(m["meeting_url"])}">🎥 Join</a></td></tr>' for m in meetings_list) or '<tr><td colspan="4" class="empty">No meetings available.</td></tr>'
    body = f'{message}{form}<div class="card"><h2>🎥 Available VC Meetings</h2><div class="table-wrap"><table><tr><th>Meeting</th><th>Created By</th><th>Created</th><th>Join</th></tr>{rows}</table></div></div>'
    return page(body, "Meetings")


@app.route("/meeting/<meeting_code>")
def meeting_room(meeting_code):
    if not logged_in():
        return redirect(url_for("login"))
    conn = db()
    meeting = conn.execute("SELECT m.*,u.name authority_name FROM meetings m LEFT JOIN users u ON m.created_by=u.id WHERE m.meeting_code=?", (meeting_code,)).fetchone()
    if not meeting:
        conn.close()
        return "Meeting not found", 404
    conn.execute("INSERT OR IGNORE INTO meeting_participants(meeting_id,user_id,joined_at) VALUES(?,?,?)", (meeting["id"], session["user_id"], now()))
    conn.commit()
    participants = conn.execute("SELECT u.name,u.role,p.joined_at FROM meeting_participants p JOIN users u ON p.user_id=u.id WHERE p.meeting_id=? ORDER BY p.joined_at", (meeting["id"],)).fetchall()
    conn.close()
    rows = "".join(f'<tr><td>{esc(p["name"])}</td><td>{esc(p["role"])}</td><td>🟢 Joined</td></tr>' for p in participants)
    body = f'<div class="card" style="text-align:center"><h1>🎥 Smart Inspection VC Room</h1><div class="info success">🟢 You joined successfully.<br><br>Meeting: <b>{esc(meeting["title"])}</b><br>Code: <span class="meeting-code">{esc(meeting_code)}</span><br>Joined as: <b>{esc(session["name"])}</b> ({esc(session["role"])})</div><p style="color:#64748b">Prototype coordination room. For production, connect a WebRTC/VC provider such as an approved institutional service.</p><a class="btn" href="/meetings">← Back to Meetings</a></div><div class="card"><h2>👥 Participants</h2><div class="table-wrap"><table><tr><th>Name</th><th>Role</th><th>Status</th></tr>{rows}</table></div></div>'
    return page(body, "Meeting Room")


@app.route("/api/latest-meeting")
def latest_meeting():
    if not logged_in():
        return jsonify({"logged_in": False}), 401
    if session.get("role") not in ("Inspector", "Project Staff", "Beneficiary"):
        return jsonify({"meeting": None})
    conn = db()
    meeting = conn.execute("SELECT m.id,m.title,m.created_at,m.meeting_url,u.name authority_name FROM meetings m LEFT JOIN users u ON m.created_by=u.id ORDER BY m.id DESC LIMIT 1").fetchone()
    conn.close()
    if not meeting:
        return jsonify({"meeting": None})
    return jsonify({"meeting": {"id": meeting["id"], "title": meeting["title"], "created_at": meeting["created_at"], "meeting_url": meeting["meeting_url"], "authority_name": meeting["authority_name"] or "Authority"}})


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.errorhandler(413)
def too_large(_):
    return page('<div class="card"><h1>File too large</h1><p>Please upload an image smaller than 10 MB.</p><a class="btn" href="/home">Back</a></div>', "Upload Error"), 413


@app.errorhandler(404)
def not_found(_):
    return page('<div class="card"><h1>404 — Page not found</h1><p>The requested page does not exist.</p><a class="btn" href="/home">Go Home</a></div>', "Not Found"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
