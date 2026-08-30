# SIMMS - Smart Inspection & Monitoring Management System

## About

SIMMS is a web-based application designed to manage and monitor inspection activities digitally. It helps authorities, inspectors, and workers coordinate inspections, report issues, track their status, and manage the complete inspection process in one system.

## Features

- Role-based login for Authority, Inspector, and Worker
- User management
- Automated inspection assignment
- Face verification before starting an inspection
- Field inspection and issue reporting
- Photo evidence upload
- GPS location capture
- Issue priority detection based on repeated reports
- Monitoring dashboard
- Issue verification and status updates
- Inspection analytics
- CCTV monitoring link management
- Team meeting coordination

## How It Works

1. The Authority assigns an inspection to a Worker or Inspector.
2. The assigned user completes face verification.
3. The Worker or Inspector performs the inspection and submits a report.
4. Issues can include descriptions, photo evidence, and location details.
5. The system automatically assigns priority based on repeated issues at the same location.
6. The Authority monitors, verifies, and updates the issue status through the dashboard.

## Technologies Used

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript
- Werkzeug

pip install -r requirements.txt

Install the required packages:

pip install -r requirements.txt

Run the application:

python app.py

Open the application in your browser:

http://127.0.0.1:5000
Project Structure
SIMMS/
├── app.py
├── requirements.txt
├── inspection.db
├── uploads/
├── face_captures/
└── README.md
Demo Accounts
Authority: ADMIN001
Inspector: INS001
Worker: WORK001
Project Purpose

SIMMS aims to make the inspection process more organized, transparent, and efficient by providing a centralized platform for inspection management and monitoring.

Future Improvements
Real-time notifications
AI-based issue detection
Interactive maps
Live CCTV integration
Mobile application support
