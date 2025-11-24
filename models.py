# models.py
from typing import Optional
from firebase_client import get_user_doc, get_all_complaints, get_complaint, get_complaint_updates

def user_role(uid: str) -> Optional[str]:
    u = get_user_doc(uid)
    return u.get("role") if u else None

def complaints_for_user(uid: str, role: str):
    """
    If role == 'user' => return only complaints created by uid.
    else return all complaints
    """
    all_complaints = get_all_complaints()
    if role == "user":
        return [(cid, data) for cid, data in all_complaints if data.get("created_by_uid") == uid]
    return all_complaints
