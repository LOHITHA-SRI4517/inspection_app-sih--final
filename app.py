from flask import Flask, request, redirect, url_for, session, send_from_directory, render_template_string, jsonify
import sqlite3, os, uuid, random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import escape

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-before-production')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'inspection.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
FACE_FOLDER = os.path.join(BASE_DIR, 'face_captures')
os.makedirs(UPLOAD_FOLDER, exist_ok=True); os.makedirs(FACE_FOLDER, exist_ok=True)
app.config.update(UPLOAD_FOLDER=UPLOAD_FOLDER, FACE_FOLDER=FACE_FOLDER, MAX_CONTENT_LENGTH=10*1024*1024)
ALLOWED_EXTENSIONS={'png','jpg','jpeg','gif','webp'}

def now(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def db():
    c=sqlite3.connect(DATABASE); c.row_factory=sqlite3.Row; return c
def logged_in(): return 'user_id' in session
def esc(x): return '' if x is None else str(escape(str(x)))
def allowed_file(n): return '.' in n and n.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS
def role_required(role): return logged_in() and session.get('role')==role
def priority_for(n): return 'High' if n>=4 else ('Medium' if n>=2 else 'Low')

def init_db():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, unique_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, location TEXT NOT NULL, assigned_at TEXT NOT NULL, status TEXT DEFAULT 'Assigned', face_verified INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS issues(id INTEGER PRIMARY KEY AUTOINCREMENT, location TEXT NOT NULL, issue_type TEXT NOT NULL, description TEXT, created_at TEXT NOT NULL, status TEXT DEFAULT 'Reported', priority TEXT DEFAULT 'Low', photo TEXT, reporter_id INTEGER, latitude TEXT, longitude TEXT, verified INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS cctv_feeds(id INTEGER PRIMARY KEY AUTOINCREMENT, location TEXT NOT NULL, feed_url TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS meetings(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, meeting_code TEXT UNIQUE, created_at TEXT NOT NULL, created_by INTEGER);
    CREATE TABLE IF NOT EXISTS meeting_participants(id INTEGER PRIMARY KEY AUTOINCREMENT, meeting_id INTEGER NOT NULL, user_id INTEGER NOT NULL, joined_at TEXT NOT NULL);
    '''); c.commit(); c.close()

STYLE='''<style>
*{box-sizing:border-box} body{margin:0;font-family:Arial,Helvetica,sans-serif;background:linear-gradient(135deg,#eef2f7,#dfe6f1);color:#26364f;min-height:100vh}a{text-decoration:none}.navbar{background:linear-gradient(90deg,#1b2944,#3157b4);padding:14px 5%;display:flex;justify-content:space-between;align-items:center;gap:15px;position:sticky;top:0;z-index:10;box-shadow:0 2px 8px #0002}.brand{font-size:20px;font-weight:bold;color:#fff}.navlinks{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end}.navlinks a{padding:9px 10px;color:#fff;border-radius:8px;font-weight:bold}.navlinks a:hover{background:#fff2}.container{max-width:1280px;margin:auto;padding:35px 18px}.card{background:#fff;border-radius:18px;padding:25px;margin-bottom:20px;box-shadow:0 10px 28px #18243b18}.hero{min-height:380px;border-radius:24px;padding:55px 30px;text-align:center;background:linear-gradient(135deg,#eef3fb,#fff,#eef1f8)}.hero h1{font-size:46px;color:#2d4a80;margin:15px auto}.hero p{font-size:18px;line-height:1.6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}.feature{background:#fff;border-radius:17px;padding:24px;box-shadow:0 8px 22px #18243b15}.feature h3{color:#314a78}.btn{display:inline-block;border:0;padding:12px 18px;border-radius:10px;background:#3567bd;color:#fff;font-weight:bold;cursor:pointer;margin:3px}.btn:hover{opacity:.9;transform:translateY(-1px)}.btn-green{background:#16836f}.btn-purple{background:#6738c9}.btn-orange{background:#ef5b05}.btn-red{background:#c0392b}.form-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:15px}.full{grid-column:1/-1}.field label{display:block;margin-bottom:6px;font-weight:bold}input,select,textarea{width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:9px;font-size:15px}textarea{min-height:100px}.info{background:#e7edf7;border-left:5px solid #3262b8;border-radius:9px;padding:14px;margin:15px 0}.success{background:#ecfdf5;border-left-color:#16836f}.error{background:#fef2f2;border-left-color:#c0392b}.warning{background:#fff7ed;border-left-color:#ef5b05}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px}.stat{background:#fff;padding:20px;border-radius:14px;box-shadow:0 5px 18px #18243b12}.num{font-size:30px;font-weight:bold;color:#3157b4}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:650px}th{background:#24375f;color:#fff}th,td{padding:12px;text-align:left;border-bottom:1px solid #e2e8f0}.badge,.role{display:inline-block;background:#e9eef8;padding:7px 14px;border-radius:22px;font-weight:bold}.low{background:#dcfce7}.medium{background:#fef3c7}.high{background:#fee2e2}.login-box{max-width:460px;margin:35px auto}.footer{text-align:center;padding:25px;color:#64748b}.role-home-card{background:#fff;border-radius:24px;padding:55px 35px 38px;text-align:center;box-shadow:0 12px 35px #0f172a18}.role-home-card h1{color:#29477a;font-size:40px;margin:0 0 20px}.role-line{font-size:20px;margin-bottom:18px}.role-access-message{background:#e7edf7;border-left:5px solid #3262b8;border-radius:10px;padding:18px;margin:22px 0 24px;font-size:19px}.role-actions{display:flex;justify-content:center;flex-wrap:wrap;gap:12px}.role-action{display:inline-block;padding:15px 24px;border-radius:11px;color:#fff!important;font-size:17px;font-weight:bold;min-width:175px}.action-blue{background:#3567bd}.action-purple{background:#6738c9}.action-green{background:#16836f}.action-orange{background:#ef5b05}.action-red{background:#c0392b}.camera{width:100%;min-height:360px;border:0;border-radius:12px;background:#111827}.chart-box{min-height:320px}@media(max-width:700px){.navbar{flex-direction:column;align-items:flex-start}.navlinks{justify-content:flex-start}.hero h1,.role-home-card h1{font-size:30px}.form-grid{grid-template-columns:1fr}.full{grid-column:auto}.role-home-card{padding:35px 18px}.role-action{width:100%}}
</style><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'''
LAYOUT='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}}</title></head><body>{{navbar|safe}}<main class="container">{{body|safe}}</main><div class="footer">SIMMS • Smart Real-Time Monitoring & Inspection System</div><script>function popup(t){alert(t)}</script></body></html>'''

def nav():
    if not logged_in(): return '''<div class="navbar"><a class="brand" href="/">🏛️ Smart Monitoring & Inspection System</a><div class="navlinks"><a href="/login">🔐 Login</a></div></div>'''
    role=session.get('role','')
    links='<a href="/home">🏠 Home</a><a href="/dashboard">📊 Dashboard</a>'
    if role in ('Worker','Inspector'): links+='<a href="/my-assignments">📌 My Assignments</a>'
    if role=='Authority': links+='<a href="/users">👥 Users</a><a href="/assignments">🎲 Assign</a><a href="/analytics">📈 Analytics</a><a href="/cctv">📹 CCTV</a>'
    elif role=='Inspector': links+='<a href="/reports">📄 Reports</a><a href="/cctv">📹 CCTV</a>'
    links+='<a href="/meetings">🎥 Meetings</a><a href="/logout">🚪 Logout</a>'
    return '<div class="navbar"><a class="brand" href="/home">🏛️ Smart Monitoring & Inspection</a><div class="navlinks">%s</div></div>'%links

def page(body,title='SIMMS'): return render_template_string(STYLE+LAYOUT,body=body,navbar=nav(),title=title)

@app.route('/')
def landing():
    body='''<section class="hero"><h1>Smart Real-Time Monitoring & Inspection System</h1><p>A digital platform for field inspection, evidence collection and real-time issue monitoring.</p><a class="btn" href="/login">🔐 Login to System</a></section><section class="grid" style="margin-top:25px"><div class="feature"><h3>👷 Field Inspection</h3><p>Workers and Inspectors conduct inspections directly from assigned locations.</p></div><div class="feature"><h3>📸 Evidence Capture</h3><p>Upload photographic evidence with inspection reports.</p></div><div class="feature"><h3>📍 GPS Location</h3><p>Capture the location of field inspection reports.</p></div><div class="feature"><h3>🤖 Smart Priority</h3><p>Repeated problems automatically receive higher priority.</p></div></section>'''
    return page(body,'SIMMS | Smart Inspection System')

@app.route('/login',methods=['GET','POST'])
def login():
    if logged_in(): return redirect(url_for('home'))
    msg=''
    if request.method=='POST':
        uid=request.form.get('unique_id','').strip().upper(); pw=request.form.get('password','')
        c=db(); u=c.execute('SELECT * FROM users WHERE unique_id=?',(uid,)).fetchone(); c.close()
        if u and check_password_hash(u['password'],pw):
            session.update(user_id=u['id'],name=u['name'],role=u['role'],unique_id=u['unique_id']); return redirect(url_for('home'))
        msg='<div class="info error">❌ Invalid Unique ID or password.</div>'
    body='''<div class="card login-box"><h1>🔐 Login</h1><p>Sign in using your official SIMMS account.</p>%s<form method="post"><div class="field"><label>Unique ID</label><input name="unique_id" required></div><br><div class="field"><label>Password</label><input type="password" name="password" required></div><button class="btn" style="margin-top:15px;width:100%%">Login</button></form><p style="text-align:center"><a href="/forgot-password">Forgot Password?</a></p></div>'''%msg
    return page(body,'Login')

@app.route('/forgot-password',methods=['GET','POST'])
def forgot_password():
    msg=''
    if request.method=='POST':
        uid=request.form.get('unique_id','').strip().upper(); new=request.form.get('new_password','')
        if len(new)<4: msg='<div class="info error">Password must contain at least 4 characters.</div>'
        else:
            c=db(); cur=c.execute('UPDATE users SET password=? WHERE unique_id=?',(generate_password_hash(new),uid)); c.commit(); c.close()
            msg='<div class="info success">✅ Password reset successfully. You can now log in.</div>' if cur.rowcount else '<div class="info error">❌ Unique ID was not found.</div>'
    body='''<div class="card login-box"><h1>🔑 Reset Password</h1><p>Enter your registered Unique ID and choose a new password.</p>%s<form method="post"><div class="field"><label>Unique ID</label><input name="unique_id" required></div><br><div class="field"><label>New Password</label><input type="password" name="new_password" minlength="4" required></div><button class="btn" style="margin-top:15px;width:100%%">Reset Password</button></form><p><a href="/login">← Back to Login</a></p></div>'''%msg
    return page(body,'Forgot Password')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('landing'))

@app.route('/home')
def home():
    if not logged_in(): return redirect(url_for('login'))
    role=session.get('role',''); name=esc(session.get('name','User'))
    if role=='Authority': actions='''<a class="role-action action-purple" href="/users">👥 Manage Users</a><a class="role-action action-orange" href="/assignments">🎲 Assign Inspection</a><a class="role-action action-green" href="/analytics">📈 Analytics</a><a class="role-action action-blue" href="/dashboard">📊 Dashboard</a>'''
    elif role=='Worker': actions='''<a class="role-action action-purple" href="/my-assignments">📌 My Assignments</a><a class="role-action action-blue" href="/my-assignments">📝 Conduct Inspection</a><a class="role-action action-green" href="/dashboard">📊 Dashboard</a>'''
    elif role=='Inspector': actions='''<a class="role-action action-purple" href="/my-assignments">📌 My Assignments</a><a class="role-action action-blue" href="/my-assignments">📝 Conduct Inspection</a><a class="role-action action-orange" href="/reports">📄 Inspection Reports</a><a class="role-action action-red" href="/cctv">📹 CCTV Monitoring</a><a class="role-action action-green" href="/dashboard">📊 Dashboard</a>'''
    else: actions='<a class="role-action action-blue" href="/dashboard">📊 Dashboard</a>'
    body='''<div class="role-home-card"><h1>Welcome, %s! 👋</h1><div class="role-line">Role: <span class="role">%s</span></div><div class="role-access-message">🔐 Role-based access is active.</div><div class="role-actions">%s</div></div>'''%(name,esc(role),actions)
    return page(body,'SIMMS | Workspace')

@app.route('/users',methods=['GET','POST'])
def users():
    if not role_required('Authority'): return 'Access denied',403
    msg=''; c=db()
    if request.method=='POST':
        uid=request.form.get('unique_id','').strip().upper(); name=request.form.get('name','').strip(); pw=request.form.get('password',''); role=request.form.get('role','Worker')
        if not uid or not name or not pw or role not in ('Worker','Inspector','Authority'): msg='<div class="info error">Please enter valid user details.</div>'
        else:
            try: c.execute('INSERT INTO users(unique_id,name,password,role,created_at) VALUES(?,?,?,?,?)',(uid,name,generate_password_hash(pw),role,now())); c.commit(); msg='<div class="info success">✅ User created successfully.</div>'
            except sqlite3.IntegrityError: msg='<div class="info error">❌ This Unique ID already exists.</div>'
    users=c.execute('SELECT * FROM users ORDER BY id DESC').fetchall(); c.close()
    rows=''.join('<tr><td>%s</td><td>%s</td><td><span class="role">%s</span></td><td>%s</td></tr>'%(esc(u['unique_id']),esc(u['name']),esc(u['role']),esc(u['created_at'])) for u in users) or '<tr><td colspan="4">No users yet.</td></tr>'
    body='''<div class="card"><h1>👥 User Management</h1>%s<form method="post" class="form-grid"><div class="field"><label>Name</label><input name="name" required></div><div class="field"><label>Unique ID</label><input name="unique_id" required></div><div class="field"><label>Password</label><input type="password" name="password" required></div><div class="field"><label>Role</label><select name="role"><option>Worker</option><option>Inspector</option><option>Authority</option></select></div><div class="full"><button class="btn btn-purple">➕ Create User</button></div></form></div><div class="card"><h2>Registered Users</h2><div class="table-wrap"><table><tr><th>Unique ID</th><th>Name</th><th>Role</th><th>Created</th></tr>%s</table></div></div>'''%(msg,rows)
    return page(body,'Users')

@app.route('/assignments',methods=['GET','POST'])
def assignments():
    if not role_required('Authority'): return 'Access denied',403
    c=db(); msg=''
    workers=c.execute("SELECT id,name,unique_id FROM users WHERE role IN ('Worker','Inspector')").fetchall()
    if request.method=='POST':
        loc=request.form.get('location','').strip()
        if not loc: msg='<div class="info error">Please enter a location.</div>'
        elif not workers: msg='<div class="info warning">No workers or inspectors are available.</div>'
        else:
            s=random.choice(workers); c.execute('INSERT INTO assignments(user_id,location,assigned_at,status,face_verified) VALUES(?,?,?,?,0)',(s['id'],loc,now(),'Assigned')); c.commit(); msg='<div class="info success">✅ Inspection assigned to %s (%s).</div>'%(esc(s['name']),esc(s['unique_id']))
    recent=c.execute('SELECT a.*,u.name,u.role FROM assignments a JOIN users u ON a.user_id=u.id ORDER BY a.id DESC LIMIT 20').fetchall(); c.close()
    rows=''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'%(esc(a['location']),esc(a['name']),esc(a['role']),esc(a['status'])) for a in recent) or '<tr><td colspan="4">No assignments yet.</td></tr>'
    body='''<div class="card"><h1>🎲 Assign Inspection</h1>%s<form method="post" class="form-grid"><div class="field full"><label>Inspection Location</label><input name="location" placeholder="Enter field location" required></div><div class="full"><button class="btn btn-orange">🎲 Assign Randomly</button></div></form></div><div class="card"><h2>Recent Assignments</h2><div class="table-wrap"><table><tr><th>Location</th><th>Assigned To</th><th>Role</th><th>Status</th></tr>%s</table></div></div>'''%(msg,rows)
    return page(body,'Assign Inspection')

@app.route('/my-assignments')
def my_assignments():
    if not logged_in() or session.get('role') not in ('Worker','Inspector'): return 'Access denied',403
    c=db(); data=c.execute('SELECT * FROM assignments WHERE user_id=? ORDER BY id DESC',(session['user_id'],)).fetchall(); c.close(); rows=''
    for a in data:
        if a['status']=='Completed': action='<span class="badge low">Completed</span>'
        elif not a['face_verified']: action='<a class="btn btn-purple" href="/face-verification/%s">📷 Verify</a>'%a['id']
        else: action='<a class="btn" href="/inspection/%s">📝 Conduct Inspection</a>'%a['id']
        rows+='<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'%(esc(a['location']),esc(a['assigned_at']),esc(a['status']),action)
    rows=rows or '<tr><td colspan="4">No assignments available.</td></tr>'
    return page('''<div class="card"><h1>📋 My Inspection Assignments</h1><div class="info">Complete verification and then submit your field inspection form.</div><div class="table-wrap"><table><tr><th>Location</th><th>Assigned Time</th><th>Status</th><th>Action</th></tr>%s</table></div></div>'''%rows,'My Assignments')

@app.route('/face-verification/<int:assignment_id>',methods=['GET','POST'])
def face_verification(assignment_id):
    if not logged_in() or session.get('role') not in ('Worker','Inspector'): return 'Access denied',403
    c=db(); a=c.execute('SELECT * FROM assignments WHERE id=? AND user_id=?',(assignment_id,session['user_id'])).fetchone()
    if not a: c.close(); return 'Assignment not found',404
    if request.method=='POST':
        photo=request.files.get('face_photo')
        if photo and photo.filename and allowed_file(photo.filename):
            name='verification_'+uuid.uuid4().hex+'.'+secure_filename(photo.filename).rsplit('.',1)[1].lower(); photo.save(os.path.join(FACE_FOLDER,name)); c.execute('UPDATE assignments SET face_verified=1 WHERE id=?',(assignment_id,)); c.commit(); c.close(); return redirect(url_for('inspection',assignment_id=assignment_id))
    c.close(); body='''<div class="card login-box"><h1>📷 Field Verification</h1><div class="info">Capture or upload a verification photo before starting the inspection at <b>%s</b>.</div><form method="post" enctype="multipart/form-data"><div class="field"><label>Verification Photo</label><input type="file" name="face_photo" accept="image/*" capture="user" required></div><button class="btn btn-purple" style="margin-top:15px">✅ Verify & Continue</button></form></div>'''%esc(a['location']); return page(body,'Verification')

@app.route('/inspection/<int:assignment_id>',methods=['GET','POST'])
def inspection(assignment_id):
    if not logged_in() or session.get('role') not in ('Worker','Inspector'): return 'Access denied',403
    c=db(); a=c.execute("SELECT * FROM assignments WHERE id=? AND user_id=? AND face_verified=1 AND status='Assigned'",(assignment_id,session['user_id'])).fetchone()
    if not a: c.close(); return 'Inspection access denied',403
    if request.method=='POST':
        cleanliness=request.form.get('cleanliness',''); safety=request.form.get('safety',''); facilities=request.form.get('facilities',''); desc=request.form.get('description','').strip(); lat=request.form.get('latitude',''); lon=request.form.get('longitude',''); photo=request.files.get('photo'); photo_name=None
        if photo and photo.filename and allowed_file(photo.filename): photo_name=uuid.uuid4().hex+'.'+secure_filename(photo.filename).rsplit('.',1)[1].lower(); photo.save(os.path.join(UPLOAD_FOLDER,photo_name))
        issue_type='Inspection: Cleanliness=%s, Safety=%s, Facilities=%s'%(cleanliness,safety,facilities)
        count=c.execute('SELECT COUNT(*) n FROM issues WHERE location=? AND status!=\'Resolved\'',(a['location'],)).fetchone()['n']; priority=priority_for(count+1)
        c.execute('INSERT INTO issues(location,issue_type,description,created_at,status,priority,photo,reporter_id,latitude,longitude,verified) VALUES(?,?,?,?,?,?,?,?,?,?,1)',(a['location'],issue_type,desc,now(),'Reported',priority,photo_name,session['user_id'],lat,lon)); c.execute("UPDATE assignments SET status='Completed' WHERE id=?",(assignment_id,)); c.commit(); c.close(); return redirect(url_for('dashboard'))
    c.close(); body='''<div class="card"><h1>📝 Conduct Inspection</h1><div class="info">Location: <b>%s</b></div><form method="post" enctype="multipart/form-data" class="form-grid"><div class="field"><label>Cleanliness</label><select name="cleanliness" required><option>Good</option><option>Average</option><option>Poor</option></select></div><div class="field"><label>Safety</label><select name="safety" required><option>Safe</option><option>Needs Attention</option><option>Unsafe</option></select></div><div class="field"><label>Facilities</label><select name="facilities" required><option>Good</option><option>Average</option><option>Poor</option></select></div><div class="field"><label>📸 Evidence Photo</label><input type="file" name="photo" accept="image/*"></div><div class="field"><label>Latitude</label><input id="latitude" name="latitude" readonly></div><div class="field"><label>Longitude</label><input id="longitude" name="longitude" readonly></div><div class="full"><button type="button" class="btn btn-purple" onclick="getLocation()">📍 Get Current Location</button></div><div class="field full"><label>📝 Inspection Observation</label><textarea name="description" placeholder="Describe observations or issues..."></textarea></div><div class="full"><button class="btn">📤 Submit Inspection</button></div></form></div><script>function getLocation(){navigator.geolocation?navigator.geolocation.getCurrentPosition(p=>{latitude.value=p.coords.latitude;longitude.value=p.coords.longitude},()=>popup('Please allow location permission.')):popup('Geolocation is not supported.')}</script>'''%esc(a['location']); return page(body,'Inspection Form')

@app.route('/uploads/<path:filename')
def uploaded_file(filename): return send_from_directory(UPLOAD_FOLDER,filename)

@app.route('/dashboard')
def dashboard():
    if not logged_in(): return redirect(url_for('login'))
    c=db(); role=session.get('role'); params=[]; where=''
    if role in ('Worker','Inspector'): where=' WHERE reporter_id=?'; params=[session['user_id']]
    issues=c.execute('SELECT * FROM issues'+where+' ORDER BY id DESC',params).fetchall(); c.close(); total=len(issues); reported=sum(i['status']=='Reported' for i in issues); progress=sum(i['status']=='In Progress' for i in issues); resolved=sum(i['status']=='Resolved' for i in issues)
    rows=''
    for i in issues:
        photo='<a href="/uploads/%s" target="_blank">📷 View</a>'%esc(i['photo']) if i['photo'] else '—'; action=''
        if role=='Authority': action='<a class="btn btn-orange" href="/update/%s/In%%20Progress">Start</a><a class="btn btn-green" href="/update/%s/Resolved">Resolve</a>'%(i['id'],i['id'])
        rows+='<tr><td>%s</td><td>%s</td><td>%s</td><td><span class="badge %s">%s</span></td><td>%s</td><td>%s</td><td>%s</td></tr>'%(esc(i['location']),esc(i['issue_type']),esc(i['description']),str(i['priority']).lower(),esc(i['priority']),photo,esc(i['status']),action)
    rows=rows or '<tr><td colspan="7">No inspection reports available.</td></tr>'
    body='''<div class="stats"><div class="stat"><div class="num">%s</div><small>Total Reports</small></div><div class="stat"><div class="num">%s</div><small>Reported</small></div><div class="stat"><div class="num">%s</div><small>In Progress</small></div><div class="stat"><div class="num">%s</div><small>Resolved</small></div></div><div class="card"><h2>🚨 Inspection Reports</h2><div class="table-wrap"><table><tr><th>Location</th><th>Issue</th><th>Description</th><th>Priority</th><th>Evidence</th><th>Status</th><th>Action</th></tr>%s</table></div></div>'''%(total,reported,progress,resolved,rows)
    return page(body,'Dashboard')

@app.route('/reports')
def reports():
    if not logged_in() or session.get('role')!='Inspector': return 'Access denied',403
    c=db(); issues=c.execute('SELECT * FROM issues WHERE reporter_id=? ORDER BY id DESC',(session['user_id'],)).fetchall(); c.close(); rows=''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'%(esc(i['location']),esc(i['created_at']),esc(i['priority']),esc(i['status'])) for i in issues) or '<tr><td colspan="4">No reports submitted yet.</td></tr>'
    return page('''<div class="card"><h1>📄 My Inspection Reports</h1><div class="table-wrap"><table><tr><th>Location</th><th>Submitted</th><th>Priority</th><th>Status</th></tr>%s</table></div></div>'''%rows,'Inspection Reports')

@app.route('/update/<int:issue_id>/<status>')
def update_status(issue_id,status):
    if not role_required('Authority'): return 'Access denied',403
    if status not in ('Reported','In Progress','Resolved'): return 'Invalid status',400
    c=db(); c.execute('UPDATE issues SET status=? WHERE id=?',(status,issue_id)); c.commit(); c.close(); return redirect(url_for('dashboard'))

@app.route('/analytics')
def analytics():
    if not role_required('Authority'): return 'Access denied',403
    c=db(); loc=c.execute('SELECT location,COUNT(*) reports FROM issues GROUP BY location ORDER BY reports DESC').fetchall(); pri=c.execute('SELECT priority,COUNT(*) count FROM issues GROUP BY priority').fetchall(); c.close(); labels=[r['location'] for r in loc]; vals=[r['reports'] for r in loc]; pl=[r['priority'] for r in pri]; pv=[r['count'] for r in pri]
    body='''<div class="card"><h1>📈 Analytics</h1><p>Visual overview of inspection reports and priorities.</p></div><div class="grid"><div class="card chart-box"><canvas id="locationChart"></canvas></div><div class="card chart-box"><canvas id="priorityChart"></canvas></div></div><script>new Chart(document.getElementById('locationChart'),{type:'bar',data:{labels:%s,datasets:[{label:'Reports by Location',data:%s}]},options:{responsive:true}});new Chart(document.getElementById('priorityChart'),{type:'doughnut',data:{labels:%s,datasets:[{label:'Priority',data:%s}]},options:{responsive:true}});</script>'''%(repr(labels),repr(vals),repr(pl),repr(pv))
    return page(body,'Analytics')

@app.route('/cctv',methods=['GET','POST'])
def cctv():
    if not logged_in() or session.get('role') not in ('Authority','Inspector'): return 'Access denied',403
    c=db(); msg=''; role=session.get('role')
    if request.method=='POST':
        if role!='Authority': c.close(); return 'Only Authority can add CCTV sources',403
        loc=request.form.get('location','').strip(); url=request.form.get('feed_url','').strip()
        if loc and url: c.execute('INSERT INTO cctv_feeds(location,feed_url,created_at) VALUES(?,?,?)',(loc,url,now())); c.commit(); msg='<div class="info success">✅ CCTV source added.</div>'
    feeds=c.execute('SELECT * FROM cctv_feeds ORDER BY id DESC').fetchall(); c.close()
    add='''<form method="post" class="form-grid"><div class="field"><label>Camera Location</label><input name="location" required></div><div class="field"><label>Authorized Monitoring URL</label><input type="url" name="feed_url" required></div><div class="full"><button class="btn btn-purple">➕ Add CCTV Source</button></div></form>''' if role=='Authority' else '<div class="info">👁️ Inspector view: authorized monitoring sources are read-only.</div>'
    cards=''.join('<div class="card"><h3>📹 %s</h3><p><a class="btn" href="%s" target="_blank" rel="noopener">Open Authorized Feed</a></p><small>Added %s</small></div>'%(esc(f['location']),esc(f['feed_url']),esc(f['created_at'])) for f in feeds) or '<div class="info warning">No CCTV monitoring sources added yet.</div>'
    return page('<div class="card"><h1>📹 CCTV Monitoring Center</h1>%s%s</div><div class="grid">%s</div>'%(msg,add,cards),'CCTV Monitoring')

@app.route('/meetings',methods=['GET','POST'])
def meetings():
    if not logged_in(): return redirect(url_for('login'))
    c=db(); msg=''
    if request.method=='POST':
        if session.get('role')!='Authority': c.close(); return 'Only Authority can create meetings',403
        title=request.form.get('title','').strip()
        if title: code=uuid.uuid4().hex[:10].upper(); c.execute('INSERT INTO meetings(title,meeting_code,created_at,created_by) VALUES(?,?,?,?)',(title,code,now(),session['user_id'])); c.commit(); msg='<div class="info success">✅ Meeting created successfully.</div>'
    data=c.execute('SELECT * FROM meetings ORDER BY id DESC').fetchall(); c.close(); rows=''.join('<tr><td>%s</td><td>%s</td><td><a class="btn" href="/meeting/%s">Join</a></td></tr>'%(esc(m['title']),esc(m['created_at']),esc(m['meeting_code'])) for m in data) or '<tr><td colspan="3">No meetings available.</td></tr>'
    form='''<div class="card"><h2>Create Meeting</h2><form method="post"><div class="field"><label>Meeting Title</label><input name="title" required></div><button class="btn btn-purple" style="margin-top:10px">🎥 Create Meeting</button></form></div>''' if session.get('role')=='Authority' else ''
    return page('%s%s<div class="card"><h1>🎥 Coordination Meetings</h1><div class="table-wrap"><table><tr><th>Title</th><th>Created</th><th>Action</th></tr>%s</table></div></div>'%(msg,form,rows),'Meetings')

@app.route('/meeting/<meeting_code>')
def meeting_room(meeting_code):
    if not logged_in(): return redirect(url_for('login'))
    c=db(); m=c.execute('SELECT * FROM meetings WHERE meeting_code=?',(meeting_code,)).fetchone()
    if not m: c.close(); return 'Meeting not found',404
    c.execute('INSERT INTO meeting_participants(meeting_id,user_id,joined_at) VALUES(?,?,?)',(m['id'],session['user_id'],now())); c.commit(); people=c.execute('SELECT u.name,u.role FROM meeting_participants p JOIN users u ON u.id=p.user_id WHERE p.meeting_id=? GROUP BY u.id',(m['id'],)).fetchall(); c.close(); rows=''.join('<tr><td>%s</td><td>%s</td><td>🟢 Joined</td></tr>'%(esc(p['name']),esc(p['role'])) for p in people)
    return page('''<div class="card" style="text-align:center"><h1>🎥 SIMMS Coordination Room</h1><div class="info success">🟢 You have joined the coordination room.<br><br>Meeting: <b>%s</b><br>Code: <b>%s</b></div><a class="btn" href="/meetings">← Back to Meetings</a></div><div class="card"><h2>👥 Participants</h2><div class="table-wrap"><table><tr><th>Name</th><th>Role</th><th>Status</th></tr>%s</table></div></div>'''%(esc(m['title']),esc(m['meeting_code']),rows),'Meeting Room')

@app.route('/api/dashboard')
def dashboard_api():
    if not logged_in(): return jsonify(error='Login required'),401
    c=db(); total=c.execute('SELECT COUNT(*) n FROM issues').fetchone()['n']; resolved=c.execute("SELECT COUNT(*) n FROM issues WHERE status='Resolved'").fetchone()['n']; c.close(); return jsonify(total_reports=total,resolved=resolved)

init_db()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
