# app.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from firebase_client import (
    signup_with_email_password, signin_with_email_password,
    create_user_doc, get_user_doc, create_complaint_doc,
    get_complaint, update_complaint_status, add_complaint_update,
    get_complaint_updates, list_all_users, get_all_complaints as get_all_complaints_fn
)
import firebase_client

# NOTE: Some imports above refer to functions defined in firebase_client.py and models.py
# Make sure files are in the same folder and FIREBASE_API_KEY is set.

# ---------------------------
# Small UI helpers
# ---------------------------

def center_window(win, w=1000, h=600):
    ws = win.winfo_screenwidth()
    hs = win.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

# ---------------------------
# Global state for logged-in user
# ---------------------------
session = {
    "idToken": None,
    "uid": None,
    "email": None,
    "name": None,
    "role": None
}

# ---------------------------
# Auth screens
# ---------------------------

def show_login_window():
    root = tk.Tk()
    root.title("CRTS - Login")
    center_window(root, 480, 360)
    frm = ttk.Frame(root, padding=20)
    frm.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frm, text="Email:").grid(row=0, column=0, sticky="w")
    email_entry = ttk.Entry(frm, width=40); email_entry.grid(row=0, column=1, pady=6)

    ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="w")
    pwd_entry = ttk.Entry(frm, width=40, show="*"); pwd_entry.grid(row=1, column=1, pady=6)

    ttk.Label(frm, text="Name (for signup):").grid(row=2, column=0, sticky="w")
    name_entry = ttk.Entry(frm, width=40); name_entry.grid(row=2, column=1, pady=6)

    def do_signup():
        email = email_entry.get().strip()
        pwd = pwd_entry.get().strip()
        name = name_entry.get().strip() or "Unnamed"
        if not email or not pwd:
            messagebox.showerror("Error", "Email and password required for signup.")
            return
        try:
            res = signup_with_email_password(email, pwd)
            # res contains localId (uid) and idToken
            uid = res.get("localId")
            id_token = res.get("idToken")
            # create metadata doc in users collection
            create_user_doc(uid=uid, email=email, name=name, role="user")
            messagebox.showinfo("Success", "Account created. Please login now.")
        except Exception as e:
            messagebox.showerror("Signup failed", str(e))

    def do_login():
        email = email_entry.get().strip()
        pwd = pwd_entry.get().strip()
        if not email or not pwd:
            messagebox.showerror("Error", "Email and password required.")
            return
        try:
            res = signin_with_email_password(email, pwd)
            # res: idToken, localId
            session["idToken"] = res.get("idToken")
            session["uid"] = res.get("localId")
            session["email"] = email
            # fetch user doc to get name & role
            user_doc = get_user_doc(session["uid"])
            session["name"] = user_doc.get("name") if user_doc else email.split('@')[0]
            session["role"] = user_doc.get("role") if user_doc else "user"
            root.destroy()
            show_main_window()
        except Exception as e:
            messagebox.showerror("Login failed", str(e))

    btn_signup = ttk.Button(frm, text="Sign up", command=do_signup)
    btn_signup.grid(row=3, column=0, pady=12)
    btn_login = ttk.Button(frm, text="Login", command=do_login)
    btn_login.grid(row=3, column=1, pady=12, sticky="w")

    root.mainloop()

# ---------------------------
# Main App Window
# ---------------------------

def show_main_window():
    main = tk.Tk()
    main.title(f"CRTS - Logged in as {session['email']} ({session['role']})")
    center_window(main, 1100, 650)

    # Frames
    top = ttk.Frame(main, padding=10)
    top.pack(fill=tk.X)

    mid = ttk.Frame(main, padding=10)
    mid.pack(fill=tk.BOTH, expand=True)

    bottom = ttk.Frame(main, padding=10)
    bottom.pack(fill=tk.X)

    # Top: Create complaint form
    ttk.Label(top, text="Title:").grid(row=0, column=0, sticky="w")
    title_var = tk.StringVar(); ttk.Entry(top, textvariable=title_var, width=40).grid(row=0, column=1, padx=6)

    ttk.Label(top, text="Category:").grid(row=0, column=2, sticky="w")
    category_var = tk.StringVar(); ttk.Entry(top, textvariable=category_var, width=20).grid(row=0, column=3, padx=6)

    ttk.Label(top, text="Priority:").grid(row=0, column=4, sticky="w")
    priority_var = tk.StringVar()
    priority_combo = ttk.Combobox(top, textvariable=priority_var, values=("LOW", "MEDIUM", "HIGH"), width=10, state="readonly")
    priority_combo.current(1); priority_combo.grid(row=0, column=5, padx=6)

    ttk.Label(top, text="Description:").grid(row=1, column=0, sticky="nw", pady=6)
    desc_text = tk.Text(top, width=80, height=4); desc_text.grid(row=1, column=1, columnspan=5, pady=6, sticky="w")

    def on_create_complaint():
        title = title_var.get().strip()
        category = category_var.get().strip() or "General"
        priority = priority_var.get().strip() or "MEDIUM"
        description = desc_text.get("1.0", tk.END).strip()
        if not title or not description:
            messagebox.showerror("Error", "Title and description required.")
            return
        doc = {
            "title": title,
            "name": session.get("name"),
            "email": session.get("email"),
            "category": category,
            "description": description,
            "priority": priority,
            "status": "OPEN",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_by_uid": session.get("uid")
        }
        try:
            create_complaint_doc(doc)
            messagebox.showinfo("Success", "Complaint created.")
            title_var.set(""); category_var.set(""); desc_text.delete("1.0", tk.END)
            load_complaints()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    create_btn = ttk.Button(top, text="Create Complaint", command=on_create_complaint)
    create_btn.grid(row=2, column=5, sticky="e", pady=6)

    # Middle: Treeview table for complaints
    cols = ("id", "title", "name", "email", "category", "priority", "status", "created_at")
    tree = ttk.Treeview(mid, columns=cols, show="headings", height=18)
    for c in cols:
        tree.heading(c, text=c.title())
        tree.column(c, width=140 if c == "title" else 110)
    tree.column("id", width=220)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scroll = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def load_complaints():
        # clear
        for r in tree.get_children():
            tree.delete(r)
        try:
            # If user role is 'user' -> show only own complaints; else show all
            if session["role"] == "user":
                all_docs = get_all_complaints_fn()
                # filter locally to user's created_by_uid
                filtered = [(cid, d) for cid, d in all_docs if d.get("created_by_uid") == session["uid"]]
            else:
                filtered = get_all_complaints_fn()
            for cid, d in filtered:
                tree.insert("", tk.END, values=(
                    cid,
                    d.get("title", "")[:30],
                    d.get("name", ""),
                    d.get("email", ""),
                    d.get("category", ""),
                    d.get("priority", ""),
                    d.get("status", ""),
                    d.get("created_at", "")
                ))
        except Exception as e:
            messagebox.showerror("Error loading complaints", str(e))

    # Bottom: controls for status update & details
    status_var = tk.StringVar()
    status_combo = ttk.Combobox(bottom, textvariable=status_var, values=("OPEN","IN_PROGRESS","RESOLVED","CLOSED"), state="readonly", width=15)
    status_combo.current(0); status_combo.pack(side=tk.LEFT, padx=6)

    def on_update_status():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Select", "Select a complaint from the list.")
            return
        cid = tree.item(sel, "values")[0]
        new_status = status_var.get()
        # Only staff or admin can change status
        if session["role"] not in ("staff", "admin"):
            messagebox.showerror("Permission denied", "Only staff/admin can change status.")
            return
        remark = tk.simpledialog.askstring("Remark", "Enter remark (optional):")
        try:
            update_complaint_status(cid, new_status)
            # add update entry
            add_complaint_update(cid, {
                "status": new_status,
                "remark": remark or "",
                "updated_by_uid": session.get("uid"),
                "updated_by_name": session.get("name"),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            messagebox.showinfo("Success", "Status updated.")
            load_complaints()
        except Exception as e:
            messagebox.showerror("Update failed", str(e))

    update_btn = ttk.Button(bottom, text="Update Status (staff/admin)", command=on_update_status)
    update_btn.pack(side=tk.LEFT, padx=6)

    def on_show_detail():
        sel = tree.focus()
        if not sel:
            messagebox.showerror("Select", "Select a complaint from the list.")
            return
        cid = tree.item(sel, "values")[0]
        d = get_complaint(cid)
        updates = get_complaint_updates(cid)
        detail_win = tk.Toplevel(main)
        detail_win.title(f"Complaint {cid}")
        detail_win.geometry("800x500")
        tk.Label(detail_win, text=f"Title: {d.get('title','')}", font=("Arial", 14, "bold")).pack(anchor="w", padx=8, pady=4)
        tk.Label(detail_win, text=f"By: {d.get('name')} ({d.get('email')})").pack(anchor="w", padx=8)
        tk.Label(detail_win, text=f"Category: {d.get('category')} | Priority: {d.get('priority')} | Status: {d.get('status')}").pack(anchor="w", padx=8, pady=6)
        tk.Label(detail_win, text="Description:", font=("Arial", 12, "underline")).pack(anchor="w", padx=8)
        txt = tk.Text(detail_win, height=6, wrap="word")
        txt.pack(fill=tk.BOTH, padx=8, pady=4)
        txt.insert("1.0", d.get("description",""))
        txt.config(state=tk.DISABLED)

        tk.Label(detail_win, text="Updates / History:", font=("Arial", 12, "underline")).pack(anchor="w", padx=8, pady=6)
        listbox = tk.Listbox(detail_win, height=8)
        listbox.pack(fill=tk.BOTH, padx=8, pady=4, expand=True)
        for uid, u in updates:
            ts = u.get("updated_at", "")
            st = u.get("status", "")
            by = u.get("updated_by_name", "")
            rk = u.get("remark", "")
            listbox.insert(tk.END, f"[{ts}] {st} by {by} - {rk}")

    detail_btn = ttk.Button(bottom, text="Show Detail", command=on_show_detail)
    detail_btn.pack(side=tk.LEFT, padx=6)

    refresh_btn = ttk.Button(bottom, text="Refresh", command=load_complaints)
    refresh_btn.pack(side=tk.LEFT, padx=6)

    # Admin area: manage roles (only for admin)
    def on_admin_panel():
        if session["role"] != "admin":
            messagebox.showerror("Not allowed", "Admin access only.")
            return
        admin_win = tk.Toplevel(main)
        admin_win.title("Admin Console - Manage Users")
        admin_win.geometry("700x500")
        tv = ttk.Treeview(admin_win, columns=("uid","email","name","role"), show="headings")
        for c in ("uid","email","name","role"):
            tv.heading(c, text=c.title())
            tv.column(c, width=160)
        tv.pack(fill=tk.BOTH, expand=True)
        for uid, doc in list_all_users():
            tv.insert("", tk.END, values=(uid, doc.get("email",""), doc.get("name",""), doc.get("role","")))
        def promote():
            sel = tv.focus()
            if not sel:
                messagebox.showerror("Select", "Select user row")
                return
            uid = tv.item(sel,"values")[0]
            new_role = tk.simpledialog.askstring("Role", "Enter new role (user/staff/admin):")
            if new_role not in ("user","staff","admin"):
                messagebox.showerror("Invalid", "Role must be user/staff/admin")
                return
            # update in Firestore
            firebase_client.db.collection("users").document(uid).update({"role": new_role})
            messagebox.showinfo("Success", "Role updated")
            admin_win.destroy()
        btn_promote = ttk.Button(admin_win, text="Change Role", command=promote)
        btn_promote.pack(pady=6)

    admin_btn = ttk.Button(bottom, text="Admin Console", command=on_admin_panel)
    admin_btn.pack(side=tk.RIGHT, padx=6)

    # initial load
    load_complaints()
    main.mainloop()

# ---------------------------
# Start here
# ---------------------------

if __name__ == "__main__":
    show_login_window()
