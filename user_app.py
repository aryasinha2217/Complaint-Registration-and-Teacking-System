import threading
import traceback
from datetime import datetime
import tkinter as tk
from typing import Optional

import requests
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox

from firebase_client import (
    signup_with_email_password,
    signin_with_email_password,
    create_user_doc,
    get_user_doc,
    create_complaint_doc,
    get_all_complaints,
    get_complaint_updates,
)

# -----------------------
# Global session & root
# -----------------------
session = {"idToken": None, "uid": None, "email": None, "name": None, "role": None}

root = tk.Tk()
root.withdraw()  # hidden root, used only for event loop / after

style = ttk.Style(theme="cosmo")

login_win: Optional[tk.Toplevel] = None
main_win: Optional[tk.Toplevel] = None


# -----------------------
# Utility helpers
# -----------------------
def center_window(win: tk.Toplevel, w: int = 1100, h: int = 700):
    try:
        win.update_idletasks()
        ws = win.winfo_screenwidth()
        hs = win.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except tk.TclError:
        pass


def safe_after(callback, delay=1):
    try:
        root.after(delay, callback)
    except tk.TclError:
        pass


def show_toast(parent: tk.Toplevel, message: str, duration: int = 2200):
    try:
        toast = tk.Toplevel(parent)
    except tk.TclError:
        return
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    frame = ttk.Frame(toast, padding=(10, 6), bootstyle="secondary")
    frame.pack()
    ttk.Label(frame, text=message).pack()
    toast.update_idletasks()
    x = toast.winfo_screenwidth() - toast.winfo_reqwidth() - 20
    y = toast.winfo_screenheight() - toast.winfo_reqheight() - 60
    toast.geometry(f"+{x}+{y}")
    toast.after(duration, toast.destroy)


def show_loader(parent: tk.Toplevel, text: str = "Please wait..."):
    try:
        loader = tk.Toplevel(parent)
    except tk.TclError:
        return None
    loader.title("")
    loader.geometry("320x110")
    loader.resizable(False, False)
    loader.attributes("-topmost", True)
    loader.grab_set()
    frm = ttk.Frame(loader, padding=12)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text=text).pack(pady=(0, 8))
    pb = ttk.Progressbar(frm, mode="indeterminate", bootstyle="info")
    pb.pack(fill="x")
    pb.start(10)
    loader.update()
    return loader


def safe_run_in_thread(source_win: Optional[tk.Toplevel], func, on_done=None):
    """
    Run func() in background, callback on main thread via root.after.
    Skips callback if source window is destroyed.
    """

    def worker():
        res = None
        exc = None
        try:
            res = func()
        except Exception as e:
            exc = e

        def cb():
            if source_win is not None:
                try:
                    if not source_win.winfo_exists():
                        return
                except tk.TclError:
                    return
            if on_done:
                try:
                    on_done(res, exc)
                except Exception:
                    print("Error in on_done:\n", traceback.format_exc())

        safe_after(cb)

    threading.Thread(target=worker, daemon=True).start()


def show_error(parent: Optional[tk.Toplevel], message: str):
    parent = parent or main_win or login_win or root
    try:
        Messagebox.show_error(message, parent=parent)
    except tk.TclError:
        print("Error dialog:", message)


def show_info(parent: Optional[tk.Toplevel], message: str):
    parent = parent or main_win or login_win or root
    show_toast(parent, message)


# -----------------------
# Firebase error mapping
# -----------------------
def map_firebase_error(exc: Exception, context: str) -> str:
    """
    Convert Firebase HTTP errors into user-friendly messages.
    context: "login" or "signup"
    """
    code = None

    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        try:
            data = exc.response.json()
            code = data.get("error", {}).get("message")
        except Exception:
            code = None

    # Try parsing code from string if not found
    if not code:
        s = str(exc)
        # fallback: basic text
        return "Something went wrong while contacting the server. Please try again."

    # Normalize
    code = code.upper()

    if context == "login":
        mapping = {
            "EMAIL_NOT_FOUND": "No account found with this email. Please sign up.",
            "INVALID_PASSWORD": "Incorrect password. Please try again.",
            "USER_DISABLED": "This account has been disabled. Contact support.",
            "INVALID_EMAIL": "Invalid email address format.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Try again later.",
        }
    else:  # signup
        mapping = {
            "EMAIL_EXISTS": "An account with this email already exists. Try logging in.",
            "INVALID_EMAIL": "Invalid email address format.",
            "OPERATION_NOT_ALLOWED": "Password sign-in is disabled for this project.",
            "WEAK_PASSWORD": "Password is too weak. Use at least 6 characters.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Try again later.",
        }

    return mapping.get(code, "Server error: " + code.replace("_", " ").title())


def looks_like_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1]


# -----------------------
# LOGIN WINDOW
# -----------------------
login_win: Optional[tk.Toplevel]


def open_login_window():
    global login_win

    try:
        if login_win and login_win.winfo_exists():
            login_win.destroy()
    except tk.TclError:
        pass

    lw = tk.Toplevel(root)
    login_win = lw
    lw.title("CRTS — User Login")
    center_window(lw, 480, 360)
    lw.resizable(False, False)

    frame = ttk.Frame(lw, padding=18)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="CRTS User Portal", font=("Segoe UI", 14, "bold")).grid(
        row=0, column=0, columnspan=2, pady=(0, 14)
    )

    ttk.Label(frame, text="Email:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=6)
    email_entry = ttk.Entry(frame, width=40)
    email_entry.grid(row=1, column=1, pady=6)

    ttk.Label(frame, text="Password:", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=6)
    pwd_entry = ttk.Entry(frame, width=40, show="*")
    pwd_entry.grid(row=2, column=1, pady=6)

    ttk.Label(frame, text="Full Name (for signup):", font=("Segoe UI", 10)).grid(
        row=3, column=0, sticky="w", pady=6
    )
    name_entry = ttk.Entry(frame, width=40)
    name_entry.grid(row=3, column=1, pady=6)

    def disable_inputs(disabled: bool):
        state = "disabled" if disabled else "normal"
        for w in (email_entry, pwd_entry, name_entry):
            w.config(state=state)

    def do_signup():
        email = email_entry.get().strip()
        pwd = pwd_entry.get().strip()
        name = name_entry.get().strip() or "Unnamed User"

        if not email or not pwd:
            show_error(lw, "Email and password are required.")
            return
        if not looks_like_email(email):
            show_error(lw, "Please enter a valid email address.")
            return
        if len(pwd) < 6:
            show_error(lw, "Password must be at least 6 characters.")
            return

        loader = show_loader(lw, "Creating your account...")
        disable_inputs(True)

        def work():
            return signup_with_email_password(email, pwd)

        def done(res, exc):
            if loader:
                try:
                    loader.destroy()
                except tk.TclError:
                    pass
            disable_inputs(False)
            if exc:
                msg = map_firebase_error(exc, context="signup")
                show_error(lw, msg)
                return
            uid = res.get("localId")
            try:
                create_user_doc(uid=uid, email=email, name=name, role="user")
            except Exception as e:
                print("Warning: failed to create user doc:", e)
            show_info(lw, "Account created. Please login.")

        safe_run_in_thread(lw, work, done)

    def do_login():
        email = email_entry.get().strip()
        pwd = pwd_entry.get().strip()

        if not email or not pwd:
            show_error(lw, "Email and password are required.")
            return
        if not looks_like_email(email):
            show_error(lw, "Please enter a valid email address.")
            return

        loader = show_loader(lw, "Signing you in...")
        disable_inputs(True)

        def work():
            return signin_with_email_password(email, pwd)

        def done(res, exc):
            if loader:
                try:
                    loader.destroy()
                except tk.TclError:
                    pass
            disable_inputs(False)
            if exc:
                msg = map_firebase_error(exc, context="login")
                show_error(lw, msg)
                return

            session["idToken"] = res.get("idToken")
            session["uid"] = res.get("localId")
            session["email"] = email
            try:
                doc = get_user_doc(session["uid"])
                session["name"] = doc.get("name") if doc else email.split("@")[0]
                session["role"] = doc.get("role", "user") if doc else "user"
            except Exception:
                session["name"] = email.split("@")[0]
                session["role"] = "user"

            try:
                lw.destroy()
            except tk.TclError:
                pass
            open_main_window()

        safe_run_in_thread(lw, work, done)

    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=1, sticky="e", pady=(12, 0))
    ttk.Button(buttons, text="Sign up", bootstyle="success", command=do_signup).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Login", bootstyle="primary", command=do_login).pack(side="left")

    def on_close():
        try:
            lw.destroy()
        except tk.TclError:
            pass
        try:
            root.destroy()
        except tk.TclError:
            pass

    lw.protocol("WM_DELETE_WINDOW", on_close)


# -----------------------
# MAIN USER WINDOW
# -----------------------
main_win: Optional[tk.Toplevel]


def open_main_window():
    global main_win

    try:
        if main_win and main_win.winfo_exists():
            main_win.destroy()
    except tk.TclError:
        pass

    mw = tk.Toplevel(root)
    main_win = mw
    mw.title("CRTS — User Portal")
    center_window(mw, 1150, 720)

    # top bar
    topbar = ttk.Frame(mw, padding=(10, 8))
    topbar.pack(side="top", fill="x")
    ttk.Label(
        topbar,
        text=f"Logged in as: {session.get('name')} ({session.get('email')})",
        font=("Segoe UI", 10),
    ).pack(side="left")

    def do_logout():
        if Messagebox.yesno("Logout", "Do you really want to logout?", parent=mw):
            try:
                mw.destroy()
            except tk.TclError:
                pass
            session.update({"idToken": None, "uid": None, "email": None, "name": None, "role": None})
            open_login_window()

    ttk.Button(
        topbar, text="Logout", bootstyle="outline-secondary", command=do_logout
    ).pack(side="right")

    # body
    body = ttk.Frame(mw)
    body.pack(fill="both", expand=True)

    sidebar = ttk.Frame(body, padding=10, width=200, bootstyle="secondary")
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    content = ttk.Frame(body, padding=10)
    content.pack(side="left", fill="both", expand=True)

    status_bar = ttk.Label(mw, text="Ready", anchor="w", bootstyle="secondary")
    status_bar.pack(side="bottom", fill="x")

    def set_status(msg: str, style: str = "secondary"):
        try:
            status_bar.config(text=msg, bootstyle=f"inverse-{style}")
        except tk.TclError:
            pass

    current_view = {"name": None}

    def clear_content():
        for w in content.winfo_children():
            try:
                w.destroy()
            except tk.TclError:
                pass

    def mark_active(btn: ttk.Button):
        for child in sidebar.winfo_children():
            if isinstance(child, ttk.Button):
                child.config(bootstyle="secondary-outline")
        btn.config(bootstyle="secondary")

    def fetch_user_complaints(on_done):
        loader = show_loader(mw, "Loading your complaints...")
        set_status("Loading complaints...", "info")

        def work():
            all_docs = get_all_complaints()
            uid = session.get("uid")
            return [(cid, d) for cid, d in all_docs if d.get("created_by_uid") == uid]

        def done(res, exc):
            if loader:
                try:
                    loader.destroy()
                except tk.TclError:
                    pass
            if exc:
                set_status("Failed to load complaints", "danger")
                show_error(mw, f"Error fetching complaints:\n{exc}")
                on_done([], exc)
                return
            set_status(f"Loaded {len(res)} complaints", "secondary")
            on_done(res, None)

        safe_run_in_thread(mw, work, done)

    # -------- Views --------
    def show_dashboard():
        current_view["name"] = "dashboard"
        clear_content()
        ttk.Label(content, text="Dashboard", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 10))

        stats_frame = ttk.Frame(content)
        stats_frame.pack(fill="x", pady=6)

        cards = {}
        for i, status in enumerate(["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]):
            card = ttk.Labelframe(stats_frame, text=status, padding=10)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            ttk.Label(card, text="...", font=("Segoe UI", 16, "bold")).pack()
            cards[status] = card
            stats_frame.columnconfigure(i, weight=1)

        def fill_stats(data, exc):
            if exc:
                return
            counts = {"OPEN": 0, "IN_PROGRESS": 0, "RESOLVED": 0, "CLOSED": 0}
            for _, d in data:
                st = d.get("status", "OPEN")
                if st in counts:
                    counts[st] += 1
            for st, card in cards.items():
                for child in card.winfo_children():
                    try:
                        child.destroy()
                    except tk.TclError:
                        pass
                ttk.Label(card, text=str(counts[st]), font=("Segoe UI", 18, "bold")).pack()
                ttk.Label(card, text="complaints", font=("Segoe UI", 9)).pack()

        fetch_user_complaints(fill_stats)
        ttk.Label(
            content,
            text="\nQuick stats for your complaints.\nUse 'New Complaint' or 'My Complaints' from the left.",
            justify="left",
        ).pack(anchor="w")

    def show_new_complaint():
        current_view["name"] = "new"
        clear_content()

        ttk.Label(content, text="Submit New Complaint", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 12))

        form = ttk.Frame(content)
        form.pack(fill="both", expand=True, padx=10, pady=6)

        left = ttk.Frame(form)
        left.pack(side="left", fill="both", expand=True, padx=(0, 16))

        ttk.Label(left, text="Title *", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", pady=4)
        title_var = ttk.StringVar()
        ttk.Entry(left, textvariable=title_var, width=60).grid(row=0, column=1, pady=4)

        ttk.Label(left, text="Category", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", pady=4)
        category_var = ttk.StringVar()
        category_combo = ttk.Combobox(
            left,
            textvariable=category_var,
            values=["IT", "HR", "Facilities", "Finance", "Admin", "Other"],
            state="readonly",
            width=28,
        )
        category_combo.grid(row=1, column=1, sticky="w", pady=4)
        category_combo.set("Other")

        ttk.Label(left, text="Priority", font=("Segoe UI", 11)).grid(row=2, column=0, sticky="w", pady=4)
        priority_var = ttk.StringVar()
        priority_combo = ttk.Combobox(
            left,
            textvariable=priority_var,
            values=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            state="readonly",
            width=28,
        )
        priority_combo.grid(row=2, column=1, sticky="w", pady=4)
        priority_combo.set("MEDIUM")

        ttk.Label(left, text="Location", font=("Segoe UI", 11)).grid(row=3, column=0, sticky="w", pady=4)
        location_var = ttk.StringVar()
        ttk.Entry(left, textvariable=location_var, width=40).grid(row=3, column=1, pady=4)

        ttk.Label(left, text="Contact", font=("Segoe UI", 11)).grid(row=4, column=0, sticky="w", pady=4)
        contact_var = ttk.StringVar(value=session.get("email"))
        ttk.Entry(left, textvariable=contact_var, width=40).grid(row=4, column=1, pady=4)

        ttk.Label(left, text="Description *", font=("Segoe UI", 11)).grid(
            row=5, column=0, sticky="nw", pady=(6, 4)
        )
        desc_text = tk.Text(left, width=72, height=10, wrap="word")
        desc_text.grid(row=5, column=1, pady=(0, 8))

        submit_btn = ttk.Button(left, text="Submit Complaint", bootstyle="primary")
        submit_btn.grid(row=6, column=1, sticky="e", pady=(6, 0))

        right = ttk.Frame(form, width=260)
        right.pack(side="left", fill="y")
        ttk.Label(right, text="Guidelines", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            right,
            text="• Keep title short but clear.\n"
                 "• Explain the issue and impact.\n"
                 "• Use CRITICAL only for urgent outages.\n"
                 "• You can track status in 'My Complaints'.",
            wraplength=240,
            justify="left",
        ).pack(anchor="w")
        last_label = ttk.Label(right, text="Last submitted: None", bootstyle="info")
        last_label.pack(anchor="w", pady=(12, 0))

        def submit():
            title = title_var.get().strip()
            desc = desc_text.get("1.0", "end").strip()
            if not title or not desc:
                show_error(mw, "Title and Description are required.")
                return

            data = {
                "title": title,
                "description": desc,
                "category": category_var.get() or "Other",
                "priority": priority_var.get() or "MEDIUM",
                "location": location_var.get() or "",
                "contact": contact_var.get() or session.get("email"),
                "status": "OPEN",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "created_by_uid": session.get("uid"),
                "name": session.get("name"),
                "email": session.get("email"),
            }

            submit_btn.config(state="disabled")
            loader = show_loader(mw, "Submitting complaint...")

            def work():
                return create_complaint_doc(data)

            def done(res, exc):
                if loader:
                    try:
                        loader.destroy()
                    except tk.TclError:
                        pass
                submit_btn.config(state="normal")
                if exc:
                    show_error(mw, f"Failed to submit complaint:\n{exc}")
                    return
                title_var.set("")
                desc_text.delete("1.0", "end")
                last_label.config(
                    text=f"Last submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                show_info(mw, "Complaint submitted successfully.")
                set_status("Complaint submitted", "success")

            safe_run_in_thread(mw, work, done)

        submit_btn.config(command=submit)

    def show_my_complaints():
        current_view["name"] = "my"
        clear_content()

        header = ttk.Frame(content)
        header.pack(fill="x")
        ttk.Label(header, text="My Complaints", font=("Segoe UI", 14, "bold")).pack(side="left", pady=(0, 8))

        filter_frame = ttk.Frame(content)
        filter_frame.pack(fill="x", pady=(4, 8))

        ttk.Label(filter_frame, text="Status:").pack(side="left", padx=(0, 4))
        status_filter = ttk.StringVar(value="ALL")
        status_combo = ttk.Combobox(
            filter_frame,
            textvariable=status_filter,
            values=["ALL", "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"],
            state="readonly",
            width=14,
        )
        status_combo.pack(side="left", padx=(0, 12))

        ttk.Label(filter_frame, text="Search Title:").pack(side="left")
        search_var = ttk.StringVar()
        ttk.Entry(filter_frame, textvariable=search_var, width=30).pack(side="left", padx=(6, 12))

        refresh_btn = ttk.Button(filter_frame, text="Refresh", bootstyle="outline-secondary")
        refresh_btn.pack(side="left")

        table_frame = ttk.Frame(content)
        table_frame.pack(fill="both", expand=True)

        # First column is internal ID, hidden
        cols = ("cid", "title", "category", "priority", "status", "created_at")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18, bootstyle="info")

        tree.heading("cid", text="")
        tree.column("cid", width=0, stretch=False)  # hidden ID column

        for c in ("title", "category", "priority", "status", "created_at"):
            tree.heading(c, text=c.replace("_", " ").title())

        tree.column("title", width=320)
        tree.column("category", width=120)
        tree.column("priority", width=100)
        tree.column("status", width=120)
        tree.column("created_at", width=140)

        tree.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        bottom = ttk.Frame(content)
        bottom.pack(fill="x", pady=(6, 0))
        detail_btn = ttk.Button(bottom, text="View Details", bootstyle="secondary")
        detail_btn.pack(side="left")

        data_cache = {"items": []}

        def populate():
            q = search_var.get().strip().lower()
            st_filter = status_filter.get()

            for r in tree.get_children():
                tree.delete(r)

            for cid, d in data_cache["items"]:
                st = d.get("status", "")
                if st_filter != "ALL" and st != st_filter:
                    continue
                title = d.get("title", "")
                if q and q not in title.lower():
                    continue
                pr = d.get("priority", "")
                # inline label style for priority & status
                pr_disp = f"[{pr}]" if pr else ""
                st_disp = f"[{st}]" if st else ""
                tree.insert(
                    "",
                    tk.END,
                    values=(cid, title[:80], d.get("category", ""), pr_disp, st_disp, d.get("created_at", "")),
                )

        def reload():
            fetch_user_complaints(on_done_reload)

        def on_done_reload(res, exc):
            if exc:
                show_error(mw, f"Failed to reload:\n{exc}")
                return
            data_cache["items"] = res
            populate()

        refresh_btn.config(command=reload)

        def show_detail():
            sel = tree.focus()
            if not sel:
                show_error(mw, "Select a complaint to view details.")
                return
            vals = tree.item(sel, "values")
            if not vals:
                show_error(mw, "No data found for this row.")
                return
            cid = vals[0]

            doc = None
            for id_, dd in data_cache["items"]:
                if id_ == cid:
                    doc = dd
                    break
            if not doc:
                show_error(mw, "Complaint not found. Try refreshing.")
                return

            detail = tk.Toplevel(mw)
            detail.title("Complaint Details")
            center_window(detail, 820, 560)

            top = ttk.Frame(detail, padding=10)
            top.pack(fill="x")
            ttk.Label(top, text=doc.get("title", ""), font=("Segoe UI", 13, "bold")).pack(anchor="w")
            ttk.Label(
                top,
                text=f"Category: {doc.get('category','')} | Priority: {doc.get('priority','')} | Status: {doc.get('status','')}",
            ).pack(anchor="w")
            ttk.Label(
                top,
                text=f"Location: {doc.get('location','-')} | Contact: {doc.get('contact','-')}",
            ).pack(anchor="w", pady=(2, 0))
            ttk.Label(
                top,
                text=f"Created at: {doc.get('created_at','')}",
                bootstyle="secondary",
            ).pack(anchor="w", pady=(2, 6))

            pan = ttk.Panedwindow(detail, orient="vertical")
            pan.pack(fill="both", expand=True, padx=10, pady=(0, 8))

            desc_frame = ttk.Labelframe(pan, text="Description", padding=8)
            txt = tk.Text(desc_frame, height=6, wrap="word")
            txt.pack(fill="both", expand=True)
            txt.insert("1.0", doc.get("description", ""))
            txt.config(state="disabled")
            pan.add(desc_frame, weight=1)

            timeline_frame = ttk.Labelframe(pan, text="Status Timeline", padding=8)
            lst = tk.Listbox(timeline_frame, height=10)
            lst.pack(fill="both", expand=True)
            pan.add(timeline_frame, weight=1)

            btn_row = ttk.Frame(detail)
            btn_row.pack(fill="x", padx=10, pady=(0, 8))
            ttk.Button(btn_row, text="Close", bootstyle="secondary", command=detail.destroy).pack(side="right")

            loader = show_loader(detail, "Loading timeline...")

            def work():
                return get_complaint_updates(cid)

            def done(res, exc):
                if loader:
                    try:
                        loader.destroy()
                    except tk.TclError:
                        pass
                if exc:
                    show_error(detail, f"Failed to load timeline:\n{exc}")
                    return
                if not res:
                    lst.insert(tk.END, "No status updates yet.")
                    return
                for _, upd in reversed(res):
                    ts = upd.get("updated_at", "")
                    st = upd.get("status", "")
                    by = upd.get("updated_by_name", "System")
                    rm = upd.get("remark", "")
                    lst.insert(tk.END, f"[{ts}] {st} by {by}")
                    if rm:
                        lst.insert(tk.END, f"  - {rm}")
                        lst.insert(tk.END, "")

            safe_run_in_thread(detail, work, done)

        detail_btn.config(command=show_detail)
        reload()

    def show_profile():
        current_view["name"] = "profile"
        clear_content()

        ttk.Label(content, text="My Profile", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))

        frm = ttk.Frame(content)
        frm.pack(fill="x", pady=8)

        ttk.Label(frm, text="Name:", width=16, anchor="w").grid(row=0, column=0, pady=6)
        name_var = ttk.StringVar(value=session.get("name", ""))
        ttk.Entry(frm, textvariable=name_var, width=40).grid(row=0, column=1, pady=6)

        ttk.Label(frm, text="Email:", width=16, anchor="w").grid(row=1, column=0, pady=6)
        email_entry = ttk.Entry(frm, width=40, state="readonly")
        email_entry.grid(row=1, column=1, pady=6)
        email_entry.insert(0, session.get("email", ""))

        ttk.Label(frm, text="Role:", width=16, anchor="w").grid(row=2, column=0, pady=6)
        ttk.Label(frm, text=session.get("role", "user")).grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(
            content,
            text="Only name is editable from the user app.",
            bootstyle="secondary",
        ).pack(anchor="w", pady=(6, 0))

        def save_profile():
            new_name = name_var.get().strip() or session.get("name")
            from firebase_client import db

            try:
                db.collection("users").document(session["uid"]).update({"name": new_name})
                session["name"] = new_name
                show_info(mw, "Profile updated.")
            except Exception as e:
                show_error(mw, f"Failed to update profile:\n{e}")

        ttk.Button(content, text="Save", bootstyle="primary", command=save_profile).pack(
            anchor="e", pady=(8, 0)
        )

    # Sidebar buttons
    btn_dashboard = ttk.Button(
        sidebar,
        text="Dashboard",
        bootstyle="secondary-outline",
        command=lambda: [mark_active(btn_dashboard), show_dashboard()],
    )
    btn_dashboard.pack(fill="x", pady=(0, 6))

    btn_new = ttk.Button(
        sidebar,
        text="New Complaint",
        bootstyle="secondary-outline",
        command=lambda: [mark_active(btn_new), show_new_complaint()],
    )
    btn_new.pack(fill="x", pady=(0, 6))

    btn_my = ttk.Button(
        sidebar,
        text="My Complaints",
        bootstyle="secondary-outline",
        command=lambda: [mark_active(btn_my), show_my_complaints()],
    )
    btn_my.pack(fill="x", pady=(0, 6))

    btn_profile = ttk.Button(
        sidebar,
        text="My Profile",
        bootstyle="secondary-outline",
        command=lambda: [mark_active(btn_profile), show_profile()],
    )
    btn_profile.pack(fill="x", pady=(0, 6))

    mark_active(btn_dashboard)
    show_dashboard()

    def on_close_main():
        try:
            mw.destroy()
        except tk.TclError:
            pass
        session.update({"idToken": None, "uid": None, "email": None, "name": None, "role": None})
        open_login_window()

    mw.protocol("WM_DELETE_WINDOW", on_close_main)


# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    open_login_window()
    root.mainloop()
