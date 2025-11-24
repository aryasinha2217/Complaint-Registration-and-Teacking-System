# firebase_client.py
import firebase_admin
from firebase_admin import credentials, firestore, auth as admin_auth
import requests
import os

# ----- CONFIG: Replace by your API key (or export as env var) -----
# You should set FIREBASE_API_KEY as environment variable or paste it here for quick dev.
FIREBASE_API_KEY = "AIzaSyD_cc8oQn6dyXYoZHk45VtXCRf7Qo3TMg0"

# Path to service account JSON (firebase_key.json)
SERVICE_ACCOUNT_PATH = "firebase_key.json"

# Initialize firebase-admin
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()


# -----------------------
# Auth via REST (client-side)
# -----------------------
# We use Identity Toolkit REST endpoints to sign up / sign in with email/password
FIREBASE_REST_SIGNUP = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
FIREBASE_REST_SIGNIN = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"


def signup_with_email_password(email: str, password: str):
    """
    Create a user via Firebase Auth REST API (email & password).
    Returns the JSON response containing idToken, localId (uid), etc.
    """
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    resp = requests.post(FIREBASE_REST_SIGNUP, json=payload)
    resp.raise_for_status()
    return resp.json()


def signin_with_email_password(email: str, password: str):
    """
    Sign in existing user. Returns JSON with idToken, localId (uid), etc.
    """
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    resp = requests.post(FIREBASE_REST_SIGNIN, json=payload)
    resp.raise_for_status()
    return resp.json()


# -----------------------
# Firestore helper methods (server-side via admin SDK)
# -----------------------

def create_user_doc(uid: str, email: str, name: str, role: str = "user"):
    """
    Create a document in users collection to store metadata and role.
    """
    doc_ref = db.collection("users").document(uid)
    doc_ref.set({
        "email": email,
        "name": name,
        "role": role
    })


def get_user_doc(uid: str):
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def list_all_users():
    users = db.collection("users").stream()
    return [(u.id, u.to_dict()) for u in users]


# Complaint helpers

def create_complaint_doc(doc_data: dict):
    """
    doc_data should include required fields:
    title, name, email, category, description, priority, status, created_at, created_by_uid
    """
    doc_ref = db.collection("complaints").add(doc_data)
    return doc_ref


def get_all_complaints():
    docs = db.collection("complaints").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [(d.id, d.to_dict()) for d in docs]


def get_complaint(complaint_id: str):
    doc = db.collection("complaints").document(complaint_id).get()
    return doc.to_dict() if doc.exists else None


def update_complaint_status(complaint_id: str, status: str):
    db.collection("complaints").document(complaint_id).update({
        "status": status,
        "updated_at": firestore.SERVER_TIMESTAMP
    })


def add_complaint_update(complaint_id: str, update_data: dict):
    """
    Add an update to subcollection 'updates' under the complaint.
    update_data: status, remark, updated_by_uid, updated_by_name, updated_at (string)
    """
    updates_col = db.collection("complaints").document(complaint_id).collection("updates")
    updates_col.add(update_data)


def get_complaint_updates(complaint_id: str):
    col = db.collection("complaints").document(complaint_id).collection("updates") \
        .order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
    return [(d.id, d.to_dict()) for d in col]
