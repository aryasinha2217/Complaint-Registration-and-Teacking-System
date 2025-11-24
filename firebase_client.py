# firebase_client.py
import firebase_admin
from firebase_admin import credentials, firestore, auth as admin_auth
import requests
import os
import sys
from datetime import datetime

# -------------------------------------------------------
# FIREBASE CONFIG
# -------------------------------------------------------

# IMPORTANT: Keep your API key safe.
# For now it's hardcoded; you can replace with env var later.
FIREBASE_API_KEY = "<Add your API key>" #



# -------------------------------------------------------
# RESOURCE PATH FIX (supports PyInstaller .exe)
# -------------------------------------------------------
def resource_path(filename):
    """
    Get absolute path to a bundled resource.
    Works for development (.py) AND when compiled into .exe.
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller temp folder
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)


SERVICE_ACCOUNT_PATH = resource_path("firebase_key.json")


# -------------------------------------------------------
# FIREBASE ADMIN INITIALIZATION (FireStore)
# -------------------------------------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# -------------------------------------------------------
# REST AUTH ENDPOINTS (Signup/Login)
# -------------------------------------------------------
FIREBASE_REST_SIGNUP = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
)

FIREBASE_REST_SIGNIN = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
)


# -------------------------------------------------------
# AUTH HELPERS
# -------------------------------------------------------
def signup_with_email_password(email: str, password: str):
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    resp = requests.post(FIREBASE_REST_SIGNUP, json=payload)
    resp.raise_for_status()
    return resp.json()


def signin_with_email_password(email: str, password: str):
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    resp = requests.post(FIREBASE_REST_SIGNIN, json=payload)
    resp.raise_for_status()
    return resp.json()


# -------------------------------------------------------
# USER HELPERS
# -------------------------------------------------------
def create_user_doc(uid: str, email: str, name: str, role="user"):
    doc_ref = db.collection("users").document(uid)
    doc_ref.set(
        {
            "email": email,
            "name": name,
            "role": role,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


def get_user_doc(uid: str):
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def list_all_users():
    users = db.collection("users").stream()
    return [(u.id, u.to_dict()) for u in users]


# -------------------------------------------------------
# COMPLAINT HELPERS
# -------------------------------------------------------
def create_complaint_doc(doc_data: dict):
    """
    doc_data includes:
        title, description, category, priority,
        location, contact, status,
        created_at, created_by_uid, name, email
    """
    return db.collection("complaints").add(doc_data)


def get_all_complaints():
    """
    'created_at' is stored as a string, so Firestore cannot order by timestamp directly.
    We save timestamp as string YYYY-MM-DD HH:MM:SS so lexicographic order works.
    """
    docs = (
        db.collection("complaints")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    return [(d.id, d.to_dict()) for d in docs]


def get_complaint(complaint_id: str):
    doc = db.collection("complaints").document(complaint_id).get()
    return doc.to_dict() if doc.exists else None


def update_complaint_status(complaint_id: str, status: str):
    """
    Admin will use this.
    """
    db.collection("complaints").document(complaint_id).update(
        {
            "status": status,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )


def add_complaint_update(complaint_id: str, update_data: dict):
    """
    update_data MUST include:
        status
        remark
        updated_by_uid
        updated_by_name
        updated_at (string: YYYY-MM-DD HH:MM:SS)
    """
    updates_col = (
        db.collection("complaints").document(complaint_id).collection("updates")
    )
    updates_col.add(update_data)


def get_complaint_updates(complaint_id: str):
    """
    ordered by updated_at DESCENDING
    Our updated_at is saved as a string "2025-02-24 13:45:55",
    So ordering works correctly in Firestore.
    """
    col = (
        db.collection("complaints")
        .document(complaint_id)
        .collection("updates")
        .order_by("updated_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    return [(d.id, d.to_dict()) for d in col]
