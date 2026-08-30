🏛️ SIMMS – Smart Inspection & Monitoring Management System
📌 About the Project

SIMMS (Smart Inspection & Monitoring Management System) is a web-based application designed to digitize and simplify the inspection and monitoring process.

The system provides a centralized platform where an Authority can manage users, assign inspections, monitor reported issues, analyze repeated problems, and coordinate with the inspection team. Workers and Inspectors can receive assignments, complete verification, conduct inspections, upload evidence, and report issues.

🎯 Problem Statement

Traditional inspection processes can involve manual reporting, delayed communication, and difficulty tracking repeated issues.

SIMMS helps solve these problems by providing a digital platform for:

📋 Inspection assignment and tracking
👥 Role-based user management
📷 Verification before inspections
📸 Evidence-based issue reporting
📊 Real-time monitoring dashboard
🤖 Smart priority detection
📈 Inspection analytics
🎥 Team meeting coordination
✨ Key Features
👩‍💼 Authority Module
Create and manage system users
Assign inspections to Workers or Inspectors
Monitor all reported issues
Verify inspection reports
Update issue status
View inspection analytics
Add and manage CCTV monitoring links
Create team meetings
👷 Worker & Inspector Module
Secure login using Unique ID and password
View assigned inspections
Complete face verification before inspection
Conduct field inspections
Report cleanliness, safety, and facility issues
Upload photo evidence
Add GPS location details
Track submitted reports
View and join team meetings
📊 Smart Monitoring Dashboard

The dashboard provides information about:

Total Issues
Reported Issues
Issues In Progress
Resolved Issues
High-Priority Issues
🤖 Smart Priority Detection

When multiple issues are reported from the same location, the system automatically increases the priority:

🟢 Low Priority
🟡 Medium Priority
🔴 High Priority
🎥 Meeting Coordination

Authorities can create team meetings with automatically generated meeting links. Workers and Inspectors can view available meeting information and join the meeting room.

🔄 System Workflow
Authority
    ↓
Inspection Assignment
    ↓
Worker / Inspector
    ↓
Face Verification
    ↓
Field Inspection
    ↓
Evidence & Issue Reporting
    ↓
Smart Priority Analysis
    ↓
Authority Dashboard Monitoring
    ↓
Verification & Resolution
🛠️ Technologies Used
Technology	Purpose
🐍 Python	Backend Development
🌶️ Flask	Web Framework
🗄️ SQLite	Database Management
🌐 HTML	Web Page Structure
🎨 CSS	User Interface Design
⚙️ JavaScript	Camera and GPS Features
🔐 Werkzeug	Password Security
📁 Project Structure
SIMMS/
│
├── app.py
├── requirements.txt
├── inspection.db
│
├── uploads/
│   └── Inspection evidence images
│
├── face_captures/
│   └── Verification photos
│
└── README.md
🚀 Installation and Setup
1️⃣ Clone the Repository
git clone <your-repository-url>
cd SIMMS
2️⃣ Install Dependencies
pip install -r requirements.txt
3️⃣ Run the Application
python app.py
4️⃣ Open in Browser

Open:

http://127.0.0.1:5000

🔐 Default Demo Accounts
Role	Unique ID	Password
👩‍💼 Authority	ADMIN001	admin123
🔍 Inspector	INS001	inspector123
👷 Worker	WORK001	worker123

⚠️ Note: These accounts are provided only for demonstration and testing purposes. Passwords should be changed in a production environment.

📸 Core Modules
🔐 Authentication & Role-Based Access
👥 User Management
🎲 Automated Inspection Assignment
📷 Face Verification
📋 Field Inspection
📸 Evidence Upload
📍 GPS Location Capture
📊 Real-Time Dashboard
🤖 Smart Priority Analysis
📈 Analytics
📹 CCTV Link Management
🎥 Team Meeting Coordination
🌟 Future Enhancements
🔔 Real-time browser push notifications
🤖 AI-based issue detection from images
🗺️ Interactive map integration
📱 Mobile application support
📹 Live CCTV streaming integration
📧 Email and SMS notifications
👤 Advanced facial recognition
👥 Project Team

Project Name: SIMMS
Full Form: Smart Inspection & Monitoring Management System

SIMMS aims to make inspection processes smarter, faster, transparent, and easier to manage through digital technology.

📄 License

This project is developed for educational and academic purposes.

⭐ If you like this project, don't forget to star the repository!
