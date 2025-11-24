# CRTS – Complaint Registration & Tracking System
### Desktop Application (Python, Tkinter, ttkbootstrap – Cosmo Theme, Firebase)

---

## 📌 Overview

CRTS is a complete desktop-based complaint management system designed for institutions, colleges, offices, and internal support environments.  
It contains **two fully separate desktop applications**:

- **CRTS_User.exe** – For students or normal users to register and track complaints  
- **CRTS_Admin.exe** – For faculty/staff/admins to view, manage, update, and close complaints  

These applications include:

- Firebase Authentication  
- Firestore Database  
- Multithreaded Tkinter UI (No freeze, no crash)  
- Cosmo theme (modern UI)  
- Toast messages  
- Loaders  
- Forward-only complaint lifecycle  
- Secret-code protected Admin signup  
- Staff/Admin role management  
- Secure timeline audit  

---

## 📁 Folder Structure

```
Complaint-Registration-and-Tracking-System/
│
├── user_app.py
├── admin_app.py
├── firebase_client.py
├── models.py
├── firebase_key.json
└── README.md
```

---

## 🔥 Firebase Setup Guide

### 1️⃣ Create project  
Go to https://console.firebase.google.com  
Create a new Firebase Project.

### 2️⃣ Enable Email/Password Login  
Firebase Console → Authentication → Sign-in Methods →  
Enable **Email/Password**.

### 3️⃣ Enable Firestore Database  
Firestore → Create Database → **Production Mode**.

### 4️⃣ Download Admin SDK Private Key  
Firebase Console → Project Settings → Service Accounts →  
Click **Generate New Private Key** → Save → Rename to:

```
firebase_key.json
```

Place it inside your project folder.

### 5️⃣ Add Web API Key  
Firebase Console → Project Settings → General →  
Copy **Web API Key** and paste it into `firebase_client.py`:

```
FIREBASE_WEB_API_KEY = "YOUR_API_KEY_HERE"
```

---

## 🔐 Admin/Staff Signup Secret Code

To protect unauthorized creation of Admin/Staff accounts, CRTS uses:

```
CRTS-FACULTY-999
```

### Why this code is needed?

- Firebase Auth cannot distinguish admin vs user by default  
- Prevents students from creating admin accounts  
- Ensures only authorized faculty can become staff/admin  
- Admin can later promote staff → admin  

When code matches → Role is set to `"staff"`.

---

## 🖥 Running the Apps (Development Mode)

Install dependencies:

```
python -m pip install ttkbootstrap firebase-admin requests pyinstaller
```

### Run User App
```
python user_app.py
```

### Run Admin App
```
python admin_app.py
```

---

## 🏗 Build Windows Executables (.exe)

### 1️⃣ Build User Application
```
pyinstaller --onefile --noconsole --add-data "firebase_key.json;." user_app.py
```

Creates:

```
dist/CRTS_User.exe
```

### 2️⃣ Build Admin Application
```
pyinstaller --onefile --noconsole --add-data "firebase_key.json;." admin_app.py
```

Creates:

```
dist/CRTS_Admin.exe
```

⚠ **Important:** Place `firebase_key.json` beside both `.exe` files:

```
CRTS/
│── CRTS_User.exe
│── CRTS_Admin.exe
│── firebase_key.json
```

---

## 👤 User App – Features

- Create new complaint  
- Title, category, priority  
- Description, contact, location  
- Complaint timeline tracking  
- Clean Cosmo UI  
- Filter/search  
- No freeze UI  
- Cannot close complaints  
- Only own complaints visible  

---

## 🧑‍🏫 Admin/Faculty App – Features

### Login
- Staff/Admin login  
- Signup with secret code  

### Dashboard
- Stats for: OPEN, IN_PROGRESS, RESOLVED, CLOSED  

### Complaints
- View ALL complaints (CLOSED hidden by default)  
- Filter by status  
- Search by title/email  
- Color-coded rows  
- Forward-only flow:

```
OPEN → IN_PROGRESS → RESOLVED → CLOSED
```

### Detailed View
- Full description  
- Timeline  
- Remarks + staff name  

### User Management (Admin Only)
- List all users  
- Change roles: user / staff / admin  

### Profile
- Staff can update name  
- Role editable only by admin  

---

## 🔄 Status Lifecycle Logic

```
OPEN → IN_PROGRESS → RESOLVED → CLOSED
```

Rules:
- No backward movement  
- CLOSED is final  
- CLOSED hidden unless filtered  
- Every update logs:
  - status
  - remark
  - updated_by
  - timestamp  

---

## 🧱 Firestore Database Structure

### `users` collection
```
users/
   uid/
      email
      name
      role
```

### `complaints` collection
```
complaints/
   complaintId/
      uid
      name
      email
      title
      description
      category
      priority
      location
      contact
      status
      created_at
```

### `complaint_updates` (subcollection)
```
complaints/complaintId/updates/
   updateId/
      status
      remark
      updated_by_uid
      updated_by_name
      updated_at
```

---

## 🔐 Security Considerations

- Secret code prevents unauthorized staff/admin creation  
- Users cannot elevate roles  
- Staff cannot become admin unless promoted  
- CLOSED complaints locked forever  
- Firestore secure via admin SDK rules  

---

## 🤝 Roles

| Role  | Permissions |
|-------|-------------|
| user  | Create complaints, view own complaints |
| staff | View all complaints, update statuses |
| admin | Manage users + all staff abilities |

---

## 🎯 Final Summary

CRTS provides:

- Fast, modern desktop UI  
- Firebase-backed complaint system  
- Security-first admin logic  
- Smooth multithreading (no freeze)  
- Executable-ready apps  
- Complete complaint tracking timeline  

It is stable, secure, scalable, and fully production-ready.

