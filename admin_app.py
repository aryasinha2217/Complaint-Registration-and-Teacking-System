# admin_app.py
"""
CRTS Admin/Staff Desktop App (Cosmo theme)
Save this as admin_app.py and run: python admin_app.py
Requires: pip install ttkbootstrap firebase-admin requests
"""

import tkinter as tk
from tkinter import simpledialog
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox
import threading, traceback
from datetime import datetime
import requests

from firebase_client import (
    signup_with_email_password,
    signin_with_email_password,
    create_user_doc,
    get_user_doc,
    get_all_complaints,
    get_complaint,
    update_complaint_status,
    add_complaint_update,
    get_complaint_updates,
    list_all_users,
    db,
)

# Admin signup secret
ADMIN_SIGNUP_CODE = "CRTS-FACULTY-999"

root = tk.Tk()
root.withdraw()
style = ttk.Style("cosmo")

session = {"uid": None, "email": None, "name": None, "role": None}
login_win = None
main_win = None

# ------------------------------
# Utilities
# ------------------------------
def center(win, w=1100, h=700):
    try:
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x, y = (sw - w) // 2, (sh - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
    except tk.TclError:
        pass

def toast(parent, msg, d=2200):
    try:
        t = tk.Toplevel(parent)
    except tk.TclError:
        return
    t.overrideredirect(True); t.attributes("-topmost", True)
    f = ttk.Frame(t, padding=10, bootstyle="secondary"); f.pack()
    ttk.Label(f, text=msg).pack()
    t.update_idletasks()
    x = t.winfo_screenwidth() - t.winfo_reqwidth() - 20
    y = t.winfo_screenheight() - t.winfo_reqheight() - 50
    t.geometry(f"+{x}+{y}")
    t.after(d, t.destroy)

def loader(parent, text="Please wait..."):
    try:
        L = tk.Toplevel(parent)
    except tk.TclError:
        return None
    L.title(""); L.geometry("300x100"); L.resizable(False, False)
    L.attributes("-topmost", True); L.grab_set()
    f = ttk.Frame(L, padding=12); f.pack(expand=True, fill="both")
    ttk.Label(f, text=text).pack(pady=(0, 8))
    p = ttk.Progressbar(f, mode="indeterminate", bootstyle="info")
    p.pack(fill="x"); p.start(10); L.update()
    return L

def run_thread(win, func, done=None):
    def worker():
        res, exc = None, None
        try:
            res = func()
        except Exception as e:
            exc = e
        def cb():
            # if window destroyed, skip callback
            try:
                if win is not None and not win.winfo_exists():
                    return
            except tk.TclError:
                return
            if done:
                try:
                    done(res, exc)
                except Exception:
                    print("Error in done callback:\n", traceback.format_exc())
        root.after(1, cb)
    threading.Thread(target=worker, daemon=True).start()

def fb_error(exc, login=False):
    """Map Firebase HTTP errors to user-friendly messages"""
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        try:
            data = exc.response.json()
            code = data.get("error", {}).get("message", "").upper()
        except Exception:
            return "Auth server error."
        if login:
            mapping = {
                "EMAIL_NOT_FOUND": "No account found.",
                "INVALID_PASSWORD": "Wrong password.",
                "USER_DISABLED": "Account disabled.",
                "INVALID_EMAIL": "Invalid email.",
                "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts."
            }
            return mapping.get(code, f"Login error: {code}")
        else:
            mapping = {
                "EMAIL_EXISTS": "Email already exists.",
                "INVALID_EMAIL": "Invalid email.",
                "WEAK_PASSWORD": "Weak password."
            }
            return mapping.get(code, f"Signup error: {code}")
    return str(exc)

# ------------------------------
# Login / Signup window
# ------------------------------
def open_login():
    global login_win
    if login_win:
        try: login_win.destroy()
        except: pass

    w = tk.Toplevel(root); login_win = w
    w.title("CRTS Admin/Staff Login"); center(w, 500, 340); w.resizable(False, False)

    f = ttk.Frame(w, padding=18); f.pack(fill="both", expand=True)
    ttk.Label(f, text="CRTS Admin/Staff Portal", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

    ttk.Label(f, text="Email:").grid(row=1, column=0, sticky="w")
    e_email = ttk.Entry(f, width=40); e_email.grid(row=1, column=1, pady=5)

    ttk.Label(f, text="Password:").grid(row=2, column=0, sticky="w")
    e_pwd = ttk.Entry(f, width=40, show="*"); e_pwd.grid(row=2, column=1, pady=5)

    ttk.Label(f, text="Full Name (Signup):").grid(row=3, column=0, sticky="w")
    e_name = ttk.Entry(f, width=40); e_name.grid(row=3, column=1, pady=5)

    ttk.Label(f, text="Faculty Code:").grid(row=4, column=0, sticky="w")
    e_code = ttk.Entry(f, width=40, show="*"); e_code.grid(row=4, column=1, pady=5)

    def signup():
        email = e_email.get().strip(); pwd = e_pwd.get().strip()
        name = e_name.get().strip() or "Staff"
        code = e_code.get().strip()
        if not email or not pwd or not code:
            Messagebox.show_error("Email, password, and faculty code required.", parent=w); return
        if code != ADMIN_SIGNUP_CODE:
            Messagebox.show_error("Invalid faculty code.", parent=w); return

        L = loader(w, "Creating account...")
        def work(): return signup_with_email_password(email, pwd)
        def done(res, exc):
            try: L.destroy()
            except: pass
            if exc:
                Messagebox.show_error(fb_error(exc, login=False), parent=w); return
            uid = res.get("localId")
            try:
                create_user_doc(uid=uid, email=email, name=name, role="staff")
            except Exception:
                pass
            toast(w, "Staff account created. Please login.")
            e_code.delete(0, "end")
        run_thread(w, work, done)

    def login():
        email = e_email.get().strip(); pwd = e_pwd.get().strip()
        if not email or not pwd:
            Messagebox.show_error("Email & Password required.", parent=w); return
        L = loader(w, "Signing in...")
        def work(): return signin_with_email_password(email, pwd)
        def done(res, exc):
            try: L.destroy()
            except: pass
            if exc:
                Messagebox.show_error(fb_error(exc, login=True), parent=w); return
            uid = res.get("localId")
            session["uid"] = uid; session["email"] = email
            # load user doc (synchronously ok because small)
            try:
                user_doc = get_user_doc(uid)
            except Exception as e:
                Messagebox.show_error(f"Failed to fetch user profile: {e}", parent=w); return
            if not user_doc:
                Messagebox.show_error("No user profile in DB.", parent=w); return
            if user_doc.get("role") not in ("staff", "admin"):
                Messagebox.show_error("Not authorized for Admin Portal.", parent=w); return
            session["name"] = user_doc.get("name", email.split("@")[0])
            session["role"] = user_doc.get("role", "staff")
            try: w.destroy()
            except: pass
            open_main()
        run_thread(w, work, done)

    row = ttk.Frame(f); row.grid(row=5, column=1, sticky="e", pady=12)
    ttk.Button(row, text="Sign up", bootstyle="success", command=signup).pack(side="left", padx=5)
    ttk.Button(row, text="Login", bootstyle="primary", command=login).pack(side="left")

    def on_close():
        try: w.destroy()
        except: pass
        try: root.destroy()
        except: pass
    w.protocol("WM_DELETE_WINDOW", on_close)

# ------------------------------
# Main admin window
# ------------------------------
def open_main():
    global main_win
    if main_win:
        try: main_win.destroy()
        except: pass

    w = tk.Toplevel(root); main_win = w
    w.title("CRTS — Admin / Staff"); center(w, 1200, 750)

    # Topbar
    top = ttk.Frame(w, padding=10); top.pack(fill="x")
    ttk.Label(top, text=f"{session.get('name')} ({session.get('email')})  | Role: {session.get('role')}", font=("Segoe UI", 10)).pack(side="left")
    def logout():
        if Messagebox.yesno("Logout", "Do you really want to logout?", parent=w):
            try: w.destroy()
            except: pass
            open_login()
    ttk.Button(top, text="Logout", bootstyle="outline-secondary", command=logout).pack(side="right")

    body = ttk.Frame(w); body.pack(fill="both", expand=True)
    sidebar = ttk.Frame(body, padding=10, width=220, bootstyle="secondary")
    sidebar.pack(side="left", fill="y"); sidebar.pack_propagate(False)
    content = ttk.Frame(body, padding=10); content.pack(side="left", fill="both", expand=True)

    status_bar = ttk.Label(w, text="Ready", anchor="w", bootstyle="secondary"); status_bar.pack(side="bottom", fill="x")
    def set_status(msg, style="secondary"):
        try: status_bar.config(text=msg, bootstyle=f"inverse-{style}")
        except: status_bar.config(text=msg)

    def clear_content():
        for c in content.winfo_children():
            try: c.destroy()
            except: pass

    def activate(btn):
        for c in sidebar.winfo_children():
            if isinstance(c, ttk.Button): c.config(bootstyle="secondary-outline")
        btn.config(bootstyle="secondary")

    # ---------- Dashboard ----------
    def dashboard_view():
        clear_content(); activate(btn_dash)
        ttk.Label(content, text="Dashboard", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=8)
        frame = ttk.Frame(content); frame.pack(fill="x", pady=4)
        cards = {}
        for i, nm in enumerate(["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]):
            lf = ttk.Labelframe(frame, text=nm, padding=8); lf.grid(row=0, column=i, padx=6, sticky="nsew")
            ttk.Label(lf, text="...", font=("Segoe UI", 16, "bold")).pack()
            cards[nm] = lf; frame.columnconfigure(i, weight=1)

        L = loader(w, "Loading stats...")
        def work(): return get_all_complaints()
        def done(res, exc):
            try: L.destroy()
            except: pass
            if exc:
                Messagebox.show_error(str(exc), parent=w); return
            counts = {"OPEN": 0, "IN_PROGRESS": 0, "RESOLVED": 0, "CLOSED": 0}
            for _, d in res:
                s = d.get("status")
                if s in counts: counts[s] += 1
            for st, lf in cards.items():
                for child in lf.winfo_children():
                    try: child.destroy()
                    except: pass
                ttk.Label(lf, text=str(counts[st]), font=("Segoe UI", 20, "bold")).pack()
        run_thread(w, work, done)

    # ---------- Complaints ----------
    def complaints_view():
        clear_content(); activate(btn_comp)
        ttk.Label(content, text="All Complaints", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0,6))

        # Filters
        f = ttk.Frame(content); f.pack(fill="x", pady=6)
        ttk.Label(f, text="Status:").pack(side="left")
        status_var = ttk.StringVar(value="ALL")
        status_combo = ttk.Combobox(f, textvariable=status_var, values=("ALL","OPEN","IN_PROGRESS","RESOLVED","CLOSED"), width=14, state="readonly")
        status_combo.pack(side="left", padx=8)

        ttk.Label(f, text="Search Title/Email:").pack(side="left", padx=(10,4))
        search_var = ttk.StringVar()
        ttk.Entry(f, textvariable=search_var, width=30).pack(side="left")

        btn_refresh = ttk.Button(f, text="Refresh", bootstyle="outline-secondary"); btn_refresh.pack(side="left", padx=8)

        # Table
        tf = ttk.Frame(content); tf.pack(fill="both", expand=True)
        cols = ("cid","title","name","email","category","priority","status","created_at")
        tree = ttk.Treeview(tf, columns=cols, show="headings", bootstyle="info")
        tree.heading("cid", text=""); tree.column("cid", width=0, stretch=False)
        for c in cols[1:]:
            tree.heading(c, text=c.replace("_", " ").title())
        tree.column("title", width=300); tree.column("status", width=120)
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview); sb.pack(side="right", fill="y"); tree.configure(yscrollcommand=sb.set)

        # simple color tags
        tree.tag_configure("OPEN", foreground="#d9534f")
        tree.tag_configure("IN_PROGRESS", foreground="#0275d8")
        tree.tag_configure("RESOLVED", foreground="#5cb85c")
        tree.tag_configure("CLOSED", foreground="#6c757d")

        allowed = {"OPEN":["IN_PROGRESS"], "IN_PROGRESS":["RESOLVED"], "RESOLVED":["CLOSED"], "CLOSED":[]}
        cache = {"items": []}

        # bottom actions
        bf = ttk.Frame(content); bf.pack(fill="x", pady=6)
        next_state = ttk.StringVar()
        next_combo = ttk.Combobox(bf, textvariable=next_state, values=[], state="disabled", width=16)
        next_combo.pack(side="left")
        btn_update = ttk.Button(bf, text="Update Status", bootstyle="primary"); btn_update.pack(side="left", padx=8)
        btn_detail = ttk.Button(bf, text="View Details", bootstyle="secondary"); btn_detail.pack(side="left", padx=8)

        def populate():
            q = search_var.get().strip().lower()
            fs = status_var.get()
            tree.delete(*tree.get_children())
            for cid, d in cache["items"]:
                s = d.get("status", "")
                # show behavior: ALL hides CLOSED; specific status shows only that
                if fs == "ALL":
                    if s == "CLOSED":
                        continue
                else:
                    if s != fs:
                        continue
                t = d.get("title", "")
                em = d.get("email", "")
                if q and q not in t.lower() and q not in em.lower():
                    continue
                vals = (cid, t[:70], d.get("name",""), em, d.get("category",""), d.get("priority",""), s, d.get("created_at",""))
                tree.insert("", tk.END, values=vals, tags=(s,))

        def reload_data():
            L = loader(w, "Loading complaints...")
            set_status("Loading complaints...", "info")
            def work(): return get_all_complaints()
            def done(res, exc):
                try: L.destroy()
                except: pass
                if exc:
                    Messagebox.show_error(str(exc), parent=w); return
                cache["items"] = res
                populate()
                set_status(f"Loaded {len(res)} complaints", "secondary")
            run_thread(w, work, done)

        def on_select(e=None):
            sel = tree.focus()
            if not sel:
                next_combo.config(state="disabled", values=[]); btn_update.config(state="disabled"); return
            vals = tree.item(sel, "values")
            if not vals:
                next_combo.config(state="disabled", values=[]); btn_update.config(state="disabled"); return
            cur_status = vals[6]
            options = allowed.get(cur_status, [])
            if options:
                next_combo.config(state="readonly", values=options)
                next_state.set(options[0]); btn_update.config(state="normal")
            else:
                next_combo.config(state="disabled", values=[]); btn_update.config(state="disabled")

        tree.bind("<<TreeviewSelect>>", on_select)

        def do_update():
            sel = tree.focus()
            if not sel:
                Messagebox.show_error("Select a complaint.", parent=w); return
            vals = tree.item(sel, "values")
            cid, cur = vals[0], vals[6]
            nxt = next_state.get().strip()
            if nxt not in allowed.get(cur, []):
                Messagebox.show_error("Invalid state transition.", parent=w); return
            remark = simpledialog.askstring("Remark", f"Enter remark for {cur} → {nxt}:", parent=w)
            if remark is None: return
            L = loader(w, "Updating status...")
            def work():
                update_complaint_status(cid, nxt)
                add_complaint_update(cid, {
                    "status": nxt,
                    "remark": remark or "",
                    "updated_by_uid": session.get("uid"),
                    "updated_by_name": session.get("name"),
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            def done(_, exc):
                try: L.destroy()
                except: pass
                if exc:
                    Messagebox.show_error(str(exc), parent=w); return
                toast(w, "Status updated.")
                reload_data()
            run_thread(w, work, done)

        btn_update.config(command=do_update)

        def show_detail():
            sel = tree.focus()
            if not sel:
                Messagebox.show_error("Select a complaint.", parent=w); return
            cid = tree.item(sel, "values")[0]
            L = loader(w, "Loading complaint...")
            def work(): return get_complaint(cid)
            def done(doc, exc):
                try: L.destroy()
                except: pass
                if exc or not doc:
                    Messagebox.show_error("Failed to load complaint.", parent=w); return
                open_detail(cid, doc)
            run_thread(w, work, done)

        btn_detail.config(command=show_detail)
        btn_refresh.config(command=reload_data)
        reload_data()

    # ---------- Detail ----------
    def open_detail(cid, doc):
        d = tk.Toplevel(main_win); d.title("Complaint Detail"); center(d, 820, 580)
        top = ttk.Frame(d, padding=10); top.pack(fill="x")
        ttk.Label(top, text=doc.get("title",""), font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(top, text=f"User: {doc.get('name','')} <{doc.get('email','')}>").pack(anchor="w")
        ttk.Label(top, text=f"Category: {doc.get('category','')} | Priority: {doc.get('priority','')} | Status: {doc.get('status','')}").pack(anchor="w")
        pan = ttk.Panedwindow(d, orient="vertical"); pan.pack(fill="both", expand=True, padx=10, pady=8)

        lf1 = ttk.Labelframe(pan, text="Description", padding=8)
        txt = tk.Text(lf1, height=6, wrap="word"); txt.pack(fill="both", expand=True)
        txt.insert("1.0", doc.get("description","")); txt.config(state="disabled")
        pan.add(lf1, weight=1)

        lf2 = ttk.Labelframe(pan, text="Timeline", padding=8)
        lst = tk.Listbox(lf2, height=10); lst.pack(fill="both", expand=True)
        pan.add(lf2, weight=1)

        ttk.Button(d, text="Close", command=d.destroy).pack(pady=6)

        L = loader(d, "Loading timeline...")
        def work2(): return get_complaint_updates(cid)
        def done2(res, exc):
            try: L.destroy()
            except: pass
            if exc:
                lst.insert(tk.END, "Error loading timeline."); return
            if not res:
                lst.insert(tk.END, "No timeline yet."); return
            for _, u in reversed(res):
                lst.insert(tk.END, f"[{u.get('updated_at','')}] {u.get('status','')} by {u.get('updated_by_name','System')}")
                if u.get("remark"):
                    lst.insert(tk.END, "  - " + u.get("remark", ""))
                    lst.insert(tk.END, "")
        run_thread(d, work2, done2)

    # ---------- Users (admin only) ----------
    def users_view():
        clear_content(); activate(btn_users)
        if session.get("role") != "admin":
            Messagebox.show_error("Only admins can manage users.", parent=main_win); return
        ttk.Label(content, text="User Management", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=6)
        tf = ttk.Frame(content); tf.pack(fill="both", expand=True)
        cols = ("uid", "email", "name", "role")
        tree = ttk.Treeview(tf, columns=cols, show="headings", bootstyle="info")
        for c in cols:
            tree.heading(c, text=c.title()); tree.column(c, width=200)
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tf, orient="vertical", command=tree.yview); sb.pack(side="right", fill="y"); tree.configure(yscrollcommand=sb.set)
        bf = ttk.Frame(content); bf.pack(fill="x", pady=8)
        btn_change = ttk.Button(bf, text="Change Role", bootstyle="primary"); btn_change.pack(side="left")

        def reload_users():
            L = loader(main_win, "Loading users...")
            def work(): return list_all_users()
            def done(res, exc):
                try: L.destroy()
                except: pass
                if exc:
                    Messagebox.show_error(str(exc), parent=main_win); return
                tree.delete(*tree.get_children())
                for uid, doc in res:
                    tree.insert("", tk.END, values=(uid, doc.get("email",""), doc.get("name",""), doc.get("role","")))
            run_thread(main_win, work, done)

        def change_role():
            sel = tree.focus()
            if not sel:
                Messagebox.show_error("Select a user.", parent=main_win); return
            uid, email, name, role = tree.item(sel, "values")
            new = simpledialog.askstring("Role", f"{name} ({email})\nCurrent role: {role}\nEnter new role (user/staff/admin):", parent=main_win)
            if not new or new not in ("user", "staff", "admin"):
                Messagebox.show_error("Invalid role.", parent=main_win); return
            L = loader(main_win, "Updating role...")
            def work(): db.collection("users").document(uid).update({"role": new})
            def done(_, exc):
                try: L.destroy()
                except: pass
                if exc: Messagebox.show_error(str(exc), parent=main_win); return
                toast(main_win, "Role updated."); reload_users()
            run_thread(main_win, work, done)

        btn_change.config(command=change_role)
        reload_users()

    # ---------- Profile ----------
    def profile_view():
        clear_content(); activate(btn_prof)
        ttk.Label(content, text="My Profile", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=6)
        f = ttk.Frame(content); f.pack(fill="x", pady=8)
        ttk.Label(f, text="Name:", width=16).grid(row=0, column=0)
        name_var = ttk.StringVar(value=session.get("name",""))
        ttk.Entry(f, textvariable=name_var, width=40).grid(row=0, column=1, pady=5)
        ttk.Label(f, text="Email:", width=16).grid(row=1, column=0)
        e = ttk.Entry(f, width=40, state="readonly"); e.grid(row=1, column=1); e.insert(0, session.get("email",""))
        ttk.Label(f, text="Role:", width=16).grid(row=2, column=0); ttk.Label(f, text=session.get("role","")).grid(row=2, column=1, sticky="w")

        def save():
            new_name = name_var.get().strip()
            if not new_name: return
            L = loader(main_win, "Saving...")
            def work(): db.collection("users").document(session.get("uid")).update({"name": new_name})
            def done(_, exc):
                try: L.destroy()
                except: pass
                if exc: Messagebox.show_error(str(exc), parent=main_win); return
                session["name"] = new_name; toast(main_win, "Profile updated.")
            run_thread(main_win, work, done)
        ttk.Button(content, text="Save", bootstyle="primary", command=save).pack(anchor="e", pady=8)

    # Sidebar buttons
    btn_dash = ttk.Button(sidebar, text="Dashboard", bootstyle="secondary-outline", command=dashboard_view); btn_dash.pack(fill="x", pady=6)
    btn_comp = ttk.Button(sidebar, text="Complaints", bootstyle="secondary-outline", command=complaints_view); btn_comp.pack(fill="x", pady=6)
    btn_prof = ttk.Button(sidebar, text="My Profile", bootstyle="secondary-outline", command=profile_view); btn_prof.pack(fill="x", pady=6)
    btn_users = None
    if session.get("role") == "admin":
        btn_users = ttk.Button(sidebar, text="Users", bootstyle="secondary-outline", command=users_view); btn_users.pack(fill="x", pady=6)

    dashboard_view()
    # handle window close
    def on_close():
        try: w.destroy()
        except: pass
        open_login()
    w.protocol("WM_DELETE_WINDOW", on_close)

# Entry point
if __name__ == "__main__":
    open_login()
    root.mainloop()
