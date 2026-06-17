Electronic Diary – Offline Desktop App
A lightweight offline desktop application for schools to manage grades, attendance, and parent communication without internet.

📋 Overview
Electronic Diary is a simple, self-contained desktop application designed for teachers and parents to track student performance. The system runs entirely on local networks – no cloud, no internet, no third-party servers. All data stays within your school's local environment, ensuring complete privacy and security.

The application consists of two separate components:

Teacher App – for managing classes, students, grades, and attendance
Parent App – for viewing child's academic performance in real time

✨ Key Features
For Teachers
Create and manage student groups (classes)
Add students with their personal information
Record grades and track attendance
Maintain a digital journal with custom columns
Generate unique access tokens for each group
Run a local server on your PC to share data
All data stored locally in SQLite database
Dark/light theme support
Customizable interface colors and borders

For Parents
Connect to teacher's PC using a unique token
View grades and attendance in real time
Offline data storage – data persists locally
Encrypted communication with teacher's server
Support for multiple children/groups
Dark/light theme support
Customizable interface

Security
Token-based authentication – each group has a unique token
XOR encryption for data in transit and local storage
Password protection for parent accounts

No internet connection required – all communication is local

🛠️ Technology Stack
Component	Technology
Language	Python 3.13
GUI Framework	PyQt5
Database	SQLite3
Networking	Socket programming (TCP/IP)
Encryption	XOR-based custom encryption
Data Format	JSON for data exchange
📦 Installation
Requirements
Python 3.13 or higher
PyQt5 library

Steps
Install Python 3.13 from python.org
Install PyQt5:

bash
pip install PyQt5
Download the application files:

prepod.py – Teacher application
parent.py – Parent application
Run the application:
For Teacher: python prepod.py
For Parent: python parent.py
Note: The application creates a bibi folder on your Desktop where all data, settings, and local storage are kept.

🚀 Usage Guide
Teacher App
First Launch:

Enter your full name and subject

Set a password (used to secure your local data)

Creating a Group:

Click "Создать группу" (Create Group)
Enter group name and student list (one per line)
The system generates a unique token for this group

Managing the Journal:

Select a group from the left panel
Double-click column headers to rename them
Add columns for grades, attendance, or any custom data
Fill in data for each student

Sharing with Parents:

The token is displayed in the group list
Copy the token and share it with parents
Parents paste this token into their app to connect

Local Server:

The teacher app automatically starts a server on port 50000
Parents connect to your PC's local IP address
The server runs in the background – no extra setup needed

Parent App
First Launch:

Register with your full name and your child's full name
Set a password for local data encryption
Connecting to Teacher:
Click "Добавить группу" (Add Group)
Paste the token received from the teacher
Format: token@ip:port (e.g., abc123@192.168.1.100:50000)

Viewing Data:

Select the connected group from the left panel
The journal automatically updates when the teacher makes changes

👥 Who Is This For?
Schools that prefer offline solutions without cloud dependency
Teachers who want a simple, fast tool for grade management
Parents who want real-time access to their child's performance
Educational institutions with limited internet access
