#!/usr/bin/env python3
"""
I-KRET DESKTOP  ///  AI-Integrated Medical Appointment & Records System
A standalone, installable desktop edition of I-KRET (built in the spirit of
the JARVIS-X desktop assistant: single-file, Tkinter, no browser required).

Run directly with:   python ikret_desktop.py
Or package into a Windows .exe with PyInstaller (see build_exe.bat / README.md).

Data is stored locally in a small JSON file under the user's home folder
(~/.ikret_desktop/data.json) so the app keeps working between sessions and,
if that folder is shared (e.g. a shared/network drive between a doctor's
desk PC and a patient kiosk PC), a doctor's prescriptions, lab report edits
and schedule changes appear on the patient's screen automatically the next
refresh cycle (every few seconds) -- this is the "real-time" hand-off.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import random
import datetime
import uuid

# ============================================================================
#  PALETTE  (ported 1:1 from I-KRET's teal / amber / paper web design system)
# ============================================================================
PAPER        = "#F4EFE3"
PAPER_RAISED = "#FBF8F1"
INK          = "#182420"
INK_SOFT     = "#4B5751"
TEAL         = "#0E6B5C"
TEAL_DARK    = "#0A4A40"
TEAL_PALE    = "#DCEAE6"
AMBER        = "#E4A234"
AMBER_DARK   = "#B87A1C"
AMBER_PALE   = "#FBEBCD"
LINE         = "#D6CBB0"
DANGER       = "#B5432F"
DANGER_PALE  = "#F3DCD5"
WHITE        = "#FFFFFF"

F_HEAD  = ("Segoe UI", 15, "bold")
F_HEAD2 = ("Segoe UI", 12, "bold")
F_BODY  = ("Segoe UI", 10)
F_SMALL = ("Segoe UI", 9)
F_MONO  = ("Consolas", 10)
F_MONO_B = ("Consolas", 11, "bold")
F_EYEBROW = ("Segoe UI", 8, "bold")

DEPTS = ["General Medicine", "Paediatrics", "Orthopaedics", "Gynaecology", "ENT"]
TIMESLOTS = ["09:00-09:30", "09:30-10:00", "10:00-10:30", "10:30-11:00",
             "11:00-11:30", "11:30-12:00", "13:00-13:30", "13:30-14:00", "14:00-14:30"]
DOCTOR_MAP = {
    "General Medicine": "Dr. R. Saravanan", "Paediatrics": "Dr. K. Meena",
    "Orthopaedics": "Dr. S. Vignesh", "Gynaecology": "Dr. A. Lakshmi", "ENT": "Dr. P. Bala"
}
REFRESH_MS = 4000  # how often dashboards re-read the shared data file

# ============================================================================
#  DATA LAYER  (JSON file, atomic writes so partial writes never corrupt it)
# ============================================================================
APP_DIR = os.path.join(os.path.expanduser("~"), ".ikret_desktop")
DATA_FILE = os.path.join(APP_DIR, "data.json")


def _default_data():
    return {
        "doctors": {},          # cert_no -> {name, dept}
        "patients": {},         # mobile -> {name, aadhaar_last4}
        "appointments": [],     # list of appointment dicts
        "prescriptions": {},    # mobile -> list of prescription dicts
        "lab_reports": {},      # mobile -> list of lab report dicts
        "token_counter": 11,
    }


def ensure_store():
    os.makedirs(APP_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        save_data(_default_data())


def load_data():
    ensure_store()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        d = _default_data()
        save_data(d)
        return d


def save_data(d):
    os.makedirs(APP_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)


def today_str():
    return datetime.date.today().isoformat()


def now_str():
    return datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")


def new_token(data):
    n = data.get("token_counter", 11)
    data["token_counter"] = n + 1
    return f"B-{n}"


# ============================================================================
#  SMALL REUSABLE WIDGETS
# ============================================================================
class Card(tk.Frame):
    """A paper-raised panel with a teal/amber accent stripe, like the web card."""
    def __init__(self, parent, **kw):
        outer = kw.pop("padx", 22)
        outery = kw.pop("pady", 18)
        super().__init__(parent, bg=PAPER_RAISED, highlightbackground=LINE,
                          highlightthickness=1, bd=0)
        stripe = tk.Frame(self, bg=TEAL, height=4)
        stripe.pack(fill="x", side="top")
        self.body = tk.Frame(self, bg=PAPER_RAISED)
        self.body.pack(fill="both", expand=True, padx=outer, pady=outery)


def eyebrow(parent, text):
    row = tk.Frame(parent, bg=PAPER_RAISED)
    dot = tk.Canvas(row, width=8, height=8, bg=PAPER_RAISED, highlightthickness=0)
    dot.create_oval(1, 1, 7, 7, fill=AMBER, outline="")
    dot.pack(side="left", padx=(0, 6))
    tk.Label(row, text=text, font=F_EYEBROW, fg=TEAL_DARK, bg=PAPER_RAISED).pack(side="left")
    return row


def make_btn(parent, text, cmd, kind="primary", width=None):
    colors = {
        "primary": (TEAL, WHITE, TEAL_DARK),
        "amber":   (AMBER, INK, AMBER_DARK),
        "ghost":   (PAPER_RAISED, INK_SOFT, LINE),
        "danger":  (DANGER, WHITE, "#8f3323"),
    }
    bg, fg, active = colors.get(kind, colors["primary"])
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  activebackground=active, activeforeground=fg,
                  font=F_HEAD2, relief="flat", bd=0, cursor="hand2",
                  padx=14, pady=9, width=width)
    if kind == "ghost":
        b.configure(highlightbackground=LINE, highlightthickness=1)
    return b


def labeled_entry(parent, label, show=None, width=28):
    tk.Label(parent, text=label, font=F_SMALL, fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(8, 3))
    e = tk.Entry(parent, font=F_MONO, width=width, relief="solid", bd=1,
                 highlightthickness=1, highlightbackground=LINE, highlightcolor=TEAL, show=show)
    e.pack(fill="x", ipady=6)
    return e


def labeled_combo(parent, label, values, width=26):
    tk.Label(parent, text=label, font=F_SMALL, fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(8, 3))
    cb = ttk.Combobox(parent, values=values, state="readonly", font=F_BODY, width=width)
    cb.current(0)
    cb.pack(fill="x", ipady=3)
    return cb


def tag_label(parent, text, kind="normal"):
    bg = {"normal": TEAL_PALE, "urgent": DANGER_PALE, "pending": AMBER_PALE}.get(kind, TEAL_PALE)
    fg = {"normal": TEAL_DARK, "urgent": DANGER, "pending": AMBER_DARK}.get(kind, TEAL_DARK)
    return tk.Label(parent, text=text, font=("Segoe UI", 8, "bold"), bg=bg, fg=fg, padx=8, pady=2)


# ============================================================================
#  MAIN APPLICATION
# ============================================================================
class IKretApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("I-KRET Desktop  ///  AI-Integrated Medical Appointment System")
        self.geometry("980x680")
        self.minsize(880, 620)
        self.configure(bg=PAPER)

        self.data = load_data()
        self.session = {"role": None, "mobile": None, "cert": None, "name": None, "dept": None}

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=PAPER, borderwidth=0)
        style.configure("TNotebook.Tab", font=F_HEAD2, padding=(16, 10),
                        background=PAPER_RAISED, foreground=INK_SOFT)
        style.map("TNotebook.Tab", background=[("selected", TEAL)],
                  foreground=[("selected", WHITE)])
        style.configure("Treeview", font=F_BODY, rowheight=26, background=WHITE,
                         fieldbackground=WHITE, foreground=INK)
        style.configure("Treeview.Heading", font=F_HEAD2, background=TEAL_PALE, foreground=TEAL_DARK)

        # top bar
        top = tk.Frame(self, bg=TEAL, height=54)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        mark = tk.Label(top, text="IK", font=("Segoe UI", 14, "bold"), bg=AMBER, fg=INK,
                         width=3, height=1)
        mark.pack(side="left", padx=(16, 10), pady=10)
        brand = tk.Frame(top, bg=TEAL)
        brand.pack(side="left", pady=6)
        tk.Label(brand, text="I-KRET DESKTOP", font=("Segoe UI", 13, "bold"), bg=TEAL, fg=WHITE).pack(anchor="w")
        tk.Label(brand, text="Govt. OP Appointment & Records System", font=F_SMALL, bg=TEAL, fg=TEAL_PALE).pack(anchor="w")
        self.session_label = tk.Label(top, text="Not signed in", font=F_SMALL, bg=TEAL, fg=AMBER_PALE)
        self.session_label.pack(side="right", padx=18)

        # container that holds all screens
        self.container = tk.Frame(self, bg=PAPER)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (RoleScreen, PatientLoginScreen, DoctorLoginScreen,
                  PatientDashboard, DoctorDashboard):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.place(relx=0.5, rely=0.5, anchor="center")

        self.show("RoleScreen")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- navigation -------------------------------------------------
    def show(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    def sign_out(self):
        self.session = {"role": None, "mobile": None, "cert": None, "name": None, "dept": None}
        self.session_label.config(text="Not signed in")
        self.show("RoleScreen")

    def set_session_label(self):
        s = self.session
        if s["role"] == "doctor":
            self.session_label.config(text=f"Dr. session · {s['name']} · {s['dept']}")
        elif s["role"] == "patient":
            self.session_label.config(text=f"Patient session · {s['name']} · {s['mobile']}")

    # ---- persistence helpers -----------------------------------------
    def refresh_from_disk(self):
        self.data = load_data()

    def persist(self):
        save_data(self.data)

    def _on_close(self):
        self.persist()
        self.destroy()


# ============================================================================
#  SCREEN: ROLE SELECTION
# ============================================================================
class RoleScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        card = Card(self)
        card.pack(padx=10, pady=10)
        eyebrow(card.body, "STEP 1 · CHOOSE YOUR ROLE").pack(anchor="w", pady=(0, 10))
        tk.Label(card.body, text="Continue as", font=F_HEAD, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(card.body, text="Choose how you'd like to use I-KRET today.",
                 font=F_BODY, bg=PAPER_RAISED, fg=INK_SOFT).pack(anchor="w", pady=(2, 18))

        row = tk.Frame(card.body, bg=PAPER_RAISED)
        row.pack()
        for text, sub, cmd in [
            ("🧑  Patient", "Book & manage OP visits", lambda: app.show("PatientLoginScreen")),
            ("🩺  Doctor", "Manage OP queue & records", lambda: app.show("DoctorLoginScreen")),
        ]:
            tile = tk.Frame(row, bg=WHITE, highlightbackground=LINE, highlightthickness=1, width=210, height=140)
            tile.pack(side="left", padx=10)
            tile.pack_propagate(False)
            tk.Label(tile, text=text, font=("Segoe UI", 16, "bold"), bg=WHITE, fg=INK).pack(pady=(28, 6))
            tk.Label(tile, text=sub, font=F_SMALL, bg=WHITE, fg=INK_SOFT).pack()
            tile.bind("<Button-1>", lambda e, c=cmd: c())
            for child in tile.winfo_children():
                child.bind("<Button-1>", lambda e, c=cmd: c())

        tk.Label(card.body,
                 text="I-KRET Desktop · a college demonstration project inspired by\nTamil Nadu's hospital OP systems.",
                 font=F_SMALL, bg=PAPER_RAISED, fg=INK_SOFT, justify="center").pack(pady=(24, 0))


# ============================================================================
#  SCREEN: PATIENT LOGIN / VERIFY
# ============================================================================
class PatientLoginScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        card = Card(self)
        card.pack(padx=10, pady=10)
        eyebrow(card.body, "STEP 2 · PATIENT VERIFICATION").pack(anchor="w", pady=(0, 10))
        tk.Label(card.body, text="Verify your Aadhaar", font=F_HEAD, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(card.body, text="Your 12-digit Aadhaar number confirms identity for hospital\nrecords. It is never transmitted anywhere in this demo.",
                 font=F_BODY, bg=PAPER_RAISED, fg=INK_SOFT, justify="left").pack(anchor="w", pady=(2, 10))

        self.err = tk.Label(card.body, text="", font=F_SMALL, fg=DANGER, bg=DANGER_PALE, anchor="w")

        self.aadhaar_entry = labeled_entry(card.body, "Aadhaar number (12 digits)")
        self.name_entry = labeled_entry(card.body, "Full name")
        self.mobile_entry = labeled_entry(card.body, "Mobile number (10 digits)")

        btnrow = tk.Frame(card.body, bg=PAPER_RAISED)
        btnrow.pack(fill="x", pady=(16, 0))
        make_btn(btnrow, "Verify & continue", self.verify, "primary").pack(fill="x")
        make_btn(btnrow, "Back", lambda: app.show("RoleScreen"), "ghost").pack(fill="x", pady=(8, 0))

    def verify(self):
        self.err.pack_forget()
        aadhaar = "".join(ch for ch in self.aadhaar_entry.get() if ch.isdigit())
        name = self.name_entry.get().strip()
        mobile = "".join(ch for ch in self.mobile_entry.get() if ch.isdigit())
        if len(aadhaar) != 12:
            return self._show_err("Please enter a valid 12-digit Aadhaar number.")
        if not name:
            return self._show_err("Please enter your full name.")
        if len(mobile) != 10:
            return self._show_err("Please enter a valid 10-digit mobile number.")

        self.app.refresh_from_disk()
        data = self.app.data
        rec = data["patients"].get(mobile, {})
        rec.update({"name": name, "aadhaar_last4": aadhaar[-4:]})
        data["patients"][mobile] = rec
        self.app.persist()

        self.app.session.update({"role": "patient", "mobile": mobile, "name": name})
        self.app.set_session_label()
        self.app.show("PatientDashboard")

    def _show_err(self, msg):
        self.err.config(text=msg)
        self.err.pack(fill="x", pady=(0, 8))

    def on_show(self):
        self.err.pack_forget()


# ============================================================================
#  SCREEN: DOCTOR LOGIN / VERIFY
# ============================================================================
class DoctorLoginScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        card = Card(self)
        card.pack(padx=10, pady=10)
        eyebrow(card.body, "STEP 2 · DOCTOR VERIFICATION").pack(anchor="w", pady=(0, 10))
        tk.Label(card.body, text="Registration certificate", font=F_HEAD, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(card.body, text="Enter your Tamil Nadu Medical Council (TNMC) registration\nnumber to access the doctor dashboard.",
                 font=F_BODY, bg=PAPER_RAISED, fg=INK_SOFT, justify="left").pack(anchor="w", pady=(2, 10))

        self.err = tk.Label(card.body, text="", font=F_SMALL, fg=DANGER, bg=DANGER_PALE, anchor="w")

        self.name_entry = labeled_entry(card.body, "Full name")
        self.cert_entry = labeled_entry(card.body, "TNMC certificate / registration no.")
        self.dept_combo = labeled_combo(card.body, "Department", DEPTS)

        btnrow = tk.Frame(card.body, bg=PAPER_RAISED)
        btnrow.pack(fill="x", pady=(16, 0))
        make_btn(btnrow, "Verify & enter dashboard", self.verify, "primary").pack(fill="x")
        make_btn(btnrow, "Back", lambda: app.show("RoleScreen"), "ghost").pack(fill="x", pady=(8, 0))

    def verify(self):
        self.err.pack_forget()
        name = self.name_entry.get().strip()
        cert = self.cert_entry.get().strip()
        dept = self.dept_combo.get()
        if not name:
            return self._show_err("Please enter your full name.")
        if len(cert) < 6:
            return self._show_err("Please enter a valid TNMC certificate number.")

        self.app.refresh_from_disk()
        data = self.app.data
        data["doctors"][cert] = {"name": name, "dept": dept}
        self.app.persist()

        self.app.session.update({"role": "doctor", "cert": cert, "name": name, "dept": dept})
        self.app.set_session_label()
        self.app.show("DoctorDashboard")

    def _show_err(self, msg):
        self.err.config(text=msg)
        self.err.pack(fill="x", pady=(0, 8))

    def on_show(self):
        self.err.pack_forget()


# ============================================================================
#  SCREEN: PATIENT DASHBOARD
# ============================================================================
class PatientDashboard(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        self._after_id = None

        outer = tk.Frame(self, bg=PAPER)
        outer.pack(padx=10, pady=10)

        header = tk.Frame(outer, bg=PAPER)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="My Services", font=F_HEAD, bg=PAPER, fg=INK).pack(side="left")
        make_btn(header, "Log out", app.sign_out, "ghost").pack(side="right")

        nb = ttk.Notebook(outer, width=820, height=560)
        nb.pack(fill="both", expand=True)

        self.tab_book = tk.Frame(nb, bg=PAPER_RAISED)
        self.tab_appts = tk.Frame(nb, bg=PAPER_RAISED)
        self.tab_presc = tk.Frame(nb, bg=PAPER_RAISED)
        self.tab_labs = tk.Frame(nb, bg=PAPER_RAISED)

        nb.add(self.tab_book, text="  Book Appointment  ")
        nb.add(self.tab_appts, text="  My Appointments  ")
        nb.add(self.tab_presc, text="  Prescriptions  ")
        nb.add(self.tab_labs, text="  Lab Reports  ")

        self._build_book_tab()
        self._build_appts_tab()
        self._build_presc_tab()
        self._build_labs_tab()

    # ---------------- Book appointment ----------------
    def _build_book_tab(self):
        f = self.tab_book
        pad = tk.Frame(f, bg=PAPER_RAISED)
        pad.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(pad, text="Book your OP visit", font=F_HEAD2, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(pad, text="Choose a department, date and time slot.", font=F_SMALL,
                 bg=PAPER_RAISED, fg=INK_SOFT).pack(anchor="w", pady=(2, 12))

        self.dept_combo = labeled_combo(pad, "Department", DEPTS)
        self.date_entry = labeled_entry(pad, "Preferred date (YYYY-MM-DD)")
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        self.date_entry.insert(0, tomorrow)

        tk.Label(pad, text="Preferred time slot", font=F_SMALL, fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(8, 3))
        self.slot_var = tk.StringVar(value=TIMESLOTS[0])
        slot_frame = tk.Frame(pad, bg=PAPER_RAISED)
        slot_frame.pack(fill="x")
        for i, slot in enumerate(TIMESLOTS):
            rb = tk.Radiobutton(slot_frame, text=slot, variable=self.slot_var, value=slot,
                                 font=F_MONO, bg=PAPER_RAISED, fg=INK_SOFT, selectcolor=TEAL_PALE,
                                 indicatoron=False, padx=8, pady=6, width=11)
            rb.grid(row=i // 3, column=i % 3, padx=3, pady=3)

        self.book_err = tk.Label(pad, text="", font=F_SMALL, fg=DANGER, bg=PAPER_RAISED)
        self.book_err.pack(anchor="w", pady=(6, 0))
        make_btn(pad, "Book appointment", self.book_appointment, "amber").pack(anchor="w", pady=(12, 0))

    def book_appointment(self):
        self.book_err.config(text="")
        date_str = self.date_entry.get().strip()
        try:
            datetime.date.fromisoformat(date_str)
        except ValueError:
            self.book_err.config(text="Please enter a valid date as YYYY-MM-DD.")
            return
        dept = self.dept_combo.get()
        slot = self.slot_var.get()
        mobile = self.app.session["mobile"]

        self.app.refresh_from_disk()
        data = self.app.data
        # check clash for same doctor/slot/date
        for a in data["appointments"]:
            if a["date"] == date_str and a["time"] == slot and a["dept"] == dept and a["status"] != "cancelled":
                self.book_err.config(text="That slot is already taken for this department — pick another.")
                return

        token = new_token(data)
        appt = {
            "id": str(uuid.uuid4())[:8],
            "mobile": mobile,
            "patient_name": self.app.session["name"],
            "dept": dept,
            "doctor": DOCTOR_MAP.get(dept, "Duty Doctor"),
            "date": date_str,
            "time": slot,
            "token": token,
            "status": "waiting",
            "created": now_str(),
        }
        data["appointments"].append(appt)
        self.app.persist()
        messagebox.showinfo("Appointment booked",
                             f"Booked! Token {token} · {dept} · {date_str} {slot}\nAttending: {appt['doctor']}")

    # ---------------- My appointments ----------------
    def _build_appts_tab(self):
        f = self.tab_appts
        pad = tk.Frame(f, bg=PAPER_RAISED)
        pad.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(pad, text="Your appointment orders", font=F_HEAD2, bg=PAPER_RAISED, fg=INK).pack(anchor="w", pady=(0, 8))
        cols = ("token", "dept", "doctor", "date", "time", "status")
        self.appts_tree = ttk.Treeview(pad, columns=cols, show="headings", height=14)
        headers = {"token": "Token", "dept": "Department", "doctor": "Doctor",
                    "date": "Date", "time": "Time slot", "status": "Status"}
        for c in cols:
            self.appts_tree.heading(c, text=headers[c])
            self.appts_tree.column(c, width=120, anchor="center")
        self.appts_tree.pack(fill="both", expand=True)

    def _refresh_appts(self):
        for i in self.appts_tree.get_children():
            self.appts_tree.delete(i)
        mobile = self.app.session["mobile"]
        rows = [a for a in self.app.data["appointments"] if a["mobile"] == mobile]
        rows.sort(key=lambda a: (a["date"], a["time"]))
        for a in rows:
            self.appts_tree.insert("", "end", values=(a["token"], a["dept"], a["doctor"],
                                                        a["date"], a["time"], a["status"].title()))

    # ---------------- Prescriptions (real-time from doctor) ----------------
    def _build_presc_tab(self):
        f = self.tab_presc
        pad = tk.Frame(f, bg=PAPER_RAISED)
        pad.pack(fill="both", expand=True, padx=20, pady=16)
        row = tk.Frame(pad, bg=PAPER_RAISED)
        row.pack(fill="x")
        tk.Label(row, text="Prescriptions from your doctor", font=F_HEAD2, bg=PAPER_RAISED, fg=INK).pack(side="left")
        tk.Label(row, text="● live", font=F_SMALL, fg=TEAL, bg=PAPER_RAISED).pack(side="right")
        self.presc_list = tk.Frame(pad, bg=PAPER_RAISED)
        self.presc_list.pack(fill="both", expand=True, pady=(10, 0))

    def _refresh_presc(self):
        for w in self.presc_list.winfo_children():
            w.destroy()
        mobile = self.app.session["mobile"]
        items = self.app.data["prescriptions"].get(mobile, [])
        if not items:
            tk.Label(self.presc_list, text="No prescriptions yet.", font=F_BODY,
                     bg=PAPER_RAISED, fg=INK_SOFT).pack(anchor="w")
            return
        for p in reversed(items):
            row = tk.Frame(self.presc_list, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=f"{p['medicine']}  —  {p['dosage']}, {p['duration']}",
                     font=F_MONO_B, bg=WHITE, fg=INK, anchor="w").pack(fill="x", padx=10, pady=(8, 0))
            tk.Label(row, text=f"Prescribed by {p['doctor']} · {p['date']}", font=F_SMALL,
                     bg=WHITE, fg=INK_SOFT, anchor="w").pack(fill="x", padx=10, pady=(0, 8))

    # ---------------- Lab reports (view) ----------------
    def _build_labs_tab(self):
        f = self.tab_labs
        pad = tk.Frame(f, bg=PAPER_RAISED)
        pad.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(pad, text="Your lab reports", font=F_HEAD2, bg=PAPER_RAISED, fg=INK).pack(anchor="w", pady=(0, 8))
        cols = ("test", "status", "result", "date")
        self.labs_tree = ttk.Treeview(pad, columns=cols, show="headings", height=14)
        headers = {"test": "Test", "status": "Status", "result": "Result", "date": "Date"}
        for c in cols:
            self.labs_tree.heading(c, text=headers[c])
            self.labs_tree.column(c, width=150 if c != "result" else 260, anchor="w")
        self.labs_tree.pack(fill="both", expand=True)

    def _refresh_labs(self):
        for i in self.labs_tree.get_children():
            self.labs_tree.delete(i)
        mobile = self.app.session["mobile"]
        items = self.app.data["lab_reports"].get(mobile, [])
        for r in items:
            self.labs_tree.insert("", "end", values=(r["test"], r["status"].title(),
                                                       r.get("result", "—"), r.get("date", "—")))

    # ---------------- lifecycle ----------------
    def on_show(self):
        self.app.refresh_from_disk()
        self._refresh_appts()
        self._refresh_presc()
        self._refresh_labs()
        self._schedule_refresh()

    def _schedule_refresh(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(REFRESH_MS, self._tick)

    def _tick(self):
        if self.app.session["role"] != "patient":
            return
        self.app.refresh_from_disk()
        self._refresh_appts()
        self._refresh_presc()
        self._refresh_labs()
        self._schedule_refresh()


# ============================================================================
#  SCREEN: DOCTOR DASHBOARD
# ============================================================================
class DoctorDashboard(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        self._after_id = None
        self.selected_mobile = None

        outer = tk.Frame(self, bg=PAPER)
        outer.pack(padx=10, pady=10)

        header = tk.Frame(outer, bg=PAPER)
        header.pack(fill="x", pady=(0, 8))
        tk.Label(header, text="Doctor Dashboard", font=F_HEAD, bg=PAPER, fg=INK).pack(side="left")
        make_btn(header, "Log out", app.sign_out, "ghost").pack(side="right")

        nb = ttk.Notebook(outer, width=880, height=580)
        nb.pack(fill="both", expand=True)

        self.tab_queue = tk.Frame(nb, bg=PAPER_RAISED)
        self.tab_presc = tk.Frame(nb, bg=PAPER_RAISED)
        self.tab_labs = tk.Frame(nb, bg=PAPER_RAISED)
        self.tab_schedule = tk.Frame(nb, bg=PAPER_RAISED)

        nb.add(self.tab_queue, text="  Today's Queue  ")
        nb.add(self.tab_presc, text="  Write Prescription  ")
        nb.add(self.tab_labs, text="  Lab Reports  ")
        nb.add(self.tab_schedule, text="  Schedule Arrivals  ")

        self._build_queue_tab()
        self._build_presc_tab()
        self._build_labs_tab()
        self._build_schedule_tab()

    # ---------------- Queue tab ----------------
    def _build_queue_tab(self):
        f = self.tab_queue
        pad = tk.Frame(f, bg=PAPER_RAISED)
        pad.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(pad, text="Today's OP queue", font=F_HEAD2, bg=PAPER_RAISED, fg=INK).pack(anchor="w", pady=(0, 8))
        cols = ("token", "patient", "mobile", "time", "status")
        self.queue_tree = ttk.Treeview(pad, columns=cols, show="headings", height=13)
        headers = {"token": "Token", "patient": "Patient", "mobile": "Mobile",
                    "time": "Time slot", "status": "Status"}
        for c in cols:
            self.queue_tree.heading(c, text=headers[c])
            self.queue_tree.column(c, width=140, anchor="center")
        self.queue_tree.pack(fill="both", expand=True)

        btnrow = tk.Frame(pad, bg=PAPER_RAISED)
        btnrow.pack(fill="x", pady=(10, 0))
        make_btn(btnrow, "Mark selected as In Progress", self._mark_in_progress, "primary").pack(side="left")
        make_btn(btnrow, "Mark selected as Completed", self._mark_completed, "amber").pack(side="left", padx=8)

    def _refresh_queue(self):
        for i in self.queue_tree.get_children():
            self.queue_tree.delete(i)
        dept = self.app.session["dept"]
        today = today_str()
        rows = [a for a in self.app.data["appointments"]
                if a["dept"] == dept and a["date"] == today and a["status"] != "cancelled"]
        rows.sort(key=lambda a: a["time"])
        for a in rows:
            self.queue_tree.insert("", "end", iid=a["id"],
                                    values=(a["token"], a["patient_name"], a["mobile"], a["time"], a["status"].title()))

    def _mark_in_progress(self):
        self._set_selected_status("in progress")

    def _mark_completed(self):
        self._set_selected_status("completed")

    def _set_selected_status(self, status):
        sel = self.queue_tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a patient in the queue first.")
            return
        appt_id = sel[0]
        self.app.refresh_from_disk()
        for a in self.app.data["appointments"]:
            if a["id"] == appt_id:
                a["status"] = status
                break
        self.app.persist()
        self._refresh_queue()

    # ---------------- Prescription tab (REAL-TIME to patient) ----------------
    def _build_presc_tab(self):
        f = self.tab_presc
        pad = tk.Frame(f, bg=PAPER_RAISED)
        pad.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(pad, text="Write a prescription", font=F_HEAD2, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(pad, text="Saved prescriptions appear on the patient's device automatically.",
                 font=F_SMALL, bg=PAPER_RAISED, fg=INK_SOFT).pack(anchor="w", pady=(2, 10))

        self.presc_patient_combo = labeled_combo(pad, "Patient (today's queue)", ["—"])
        self.med_entry = labeled_entry(pad, "Medicine name")
        self.dosage_entry = labeled_entry(pad, "Dosage (e.g. 1-0-1 after food)")
        self.duration_entry = labeled_entry(pad, "Duration (e.g. 5 days)")

        make_btn(pad, "Send prescription to patient", self._send_prescription, "primary").pack(anchor="w", pady=(12, 12))

        tk.Label(pad, text="Prescription history for selected patient", font=F_HEAD2,
                 bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        cols = ("medicine", "dosage", "duration", "doctor", "date")
        self.presc_hist_tree = ttk.Treeview(pad, columns=cols, show="headings", height=8)
        for c in cols:
            self.presc_hist_tree.heading(c, text=c.title())
            self.presc_hist_tree.column(c, width=140, anchor="w")
        self.presc_hist_tree.pack(fill="both", expand=True, pady=(6, 0))

    def _patient_options(self):
        """List of 'Name (mobile)' strings from today's + all appointments for this doctor's dept."""
        dept = self.app.session["dept"]
        seen, options = set(), []
        for a in sorted(self.app.data["appointments"], key=lambda a: a["date"], reverse=True):
            if a["dept"] != dept:
                continue
            key = a["mobile"]
            if key in seen:
                continue
            seen.add(key)
            options.append(f"{a['patient_name']} ({a['mobile']})")
        return options or ["—"]

    def _selected_mobile_from_combo(self, combo):
        val = combo.get()
        if "(" in val and val.endswith(")"):
            return val.rsplit("(", 1)[1][:-1]
        return None

    def _send_prescription(self):
        mobile = self._selected_mobile_from_combo(self.presc_patient_combo)
        if not mobile:
            messagebox.showwarning("No patient selected", "Choose a patient first.")
            return
        med = self.med_entry.get().strip()
        dosage = self.dosage_entry.get().strip()
        duration = self.duration_entry.get().strip()
        if not med or not dosage or not duration:
            messagebox.showwarning("Missing info", "Fill in medicine, dosage and duration.")
            return

        self.app.refresh_from_disk()
        data = self.app.data
        entry = {
            "medicine": med, "dosage": dosage, "duration": duration,
            "doctor": self.app.session["name"], "date": now_str(),
        }
        data["prescriptions"].setdefault(mobile, []).append(entry)
        self.app.persist()

        self.med_entry.delete(0, "end")
        self.dosage_entry.delete(0, "end")
        self.duration_entry.delete(0, "end")
        self._refresh_presc_history(mobile)
        messagebox.showinfo("Sent", "Prescription saved — visible on the patient's dashboard in real time.")

    def _refresh_presc_history(self, mobile):
        for i in self.presc_hist_tree.get_children():
            self.presc_hist_tree.delete(i)
        for p in self.app.data["prescriptions"].get(mobile, []):
            self.presc_hist_tree.insert("", "end", values=(p["medicine"], p["dosage"], p["duration"],
                                                            p["doctor"], p["date"]))

    def _on_presc_patient_change(self, event=None):
        mobile = self._selected_mobile_from_combo(self.presc_patient_combo)
        if mobile:
            self._refresh_presc_history(mobile)

    # ---------------- Lab reports tab (ADD + EDIT) ----------------
    def _build_labs_tab(self):
        f = self.tab_labs
        pad = tk.Frame(f, bg=PAPER_RAISED)
        pad.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(pad, text="Manage lab reports", font=F_HEAD2, bg=PAPER_RAISED, fg=INK).pack(anchor="w", pady=(0, 8))

        self.labs_patient_combo = labeled_combo(pad, "Patient (today's queue)", ["—"])

        cols = ("test", "status", "result", "date")
        self.labs_tree = ttk.Treeview(pad, columns=cols, show="headings", height=8)
        for c in cols:
            self.labs_tree.heading(c, text=c.title())
            self.labs_tree.column(c, width=170 if c != "result" else 260, anchor="w")
        self.labs_tree.pack(fill="both", expand=True, pady=(10, 10))
        self.labs_tree.bind("<<TreeviewSelect>>", self._on_lab_row_select)

        formrow = tk.Frame(pad, bg=PAPER_RAISED)
        formrow.pack(fill="x")
        left = tk.Frame(formrow, bg=PAPER_RAISED)
        left.pack(side="left", fill="x", expand=True, padx=(0, 10))
        right = tk.Frame(formrow, bg=PAPER_RAISED)
        right.pack(side="left", fill="x", expand=True)

        self.lab_test_entry = labeled_entry(left, "Test name")
        self.lab_status_combo = labeled_combo(left, "Status", ["Pending", "Ready"])
        self.lab_result_entry = labeled_entry(right, "Result / notes", width=34)

        btnrow = tk.Frame(pad, bg=PAPER_RAISED)
        btnrow.pack(fill="x", pady=(10, 0))
        make_btn(btnrow, "Add new lab report", self._add_lab_report, "amber").pack(side="left")
        make_btn(btnrow, "Save changes to selected report", self._update_lab_report, "primary").pack(side="left", padx=8)

    def _refresh_lab_reports(self, mobile):
        for i in self.labs_tree.get_children():
            self.labs_tree.delete(i)
        items = self.app.data["lab_reports"].get(mobile, [])
        for idx, r in enumerate(items):
            self.labs_tree.insert("", "end", iid=str(idx), values=(r["test"], r["status"].title(),
                                                                     r.get("result", "—"), r.get("date", "—")))

    def _on_lab_row_select(self, event=None):
        sel = self.labs_tree.selection()
        if not sel:
            return
        mobile = self._selected_mobile_from_combo(self.labs_patient_combo)
        if not mobile:
            return
        idx = int(sel[0])
        items = self.app.data["lab_reports"].get(mobile, [])
        if idx >= len(items):
            return
        r = items[idx]
        self.lab_test_entry.delete(0, "end"); self.lab_test_entry.insert(0, r["test"])
        self.lab_result_entry.delete(0, "end"); self.lab_result_entry.insert(0, r.get("result", ""))
        self.lab_status_combo.set(r["status"].title())

    def _add_lab_report(self):
        mobile = self._selected_mobile_from_combo(self.labs_patient_combo)
        if not mobile:
            messagebox.showwarning("No patient selected", "Choose a patient first.")
            return
        test = self.lab_test_entry.get().strip()
        if not test:
            messagebox.showwarning("Missing info", "Enter a test name.")
            return
        status = self.lab_status_combo.get().lower() or "pending"
        result = self.lab_result_entry.get().strip()

        self.app.refresh_from_disk()
        data = self.app.data
        entry = {"test": test, "status": status, "result": result, "date": today_str()}
        data["lab_reports"].setdefault(mobile, []).append(entry)
        self.app.persist()
        self._refresh_lab_reports(mobile)
        self.lab_test_entry.delete(0, "end")
        self.lab_result_entry.delete(0, "end")
        messagebox.showinfo("Added", "Lab report added — visible on the patient's dashboard.")

    def _update_lab_report(self):
        sel = self.labs_tree.selection()
        mobile = self._selected_mobile_from_combo(self.labs_patient_combo)
        if not sel or not mobile:
            messagebox.showwarning("No selection", "Select an existing lab report row to edit.")
            return
        idx = int(sel[0])

        self.app.refresh_from_disk()
        data = self.app.data
        items = data["lab_reports"].get(mobile, [])
        if idx >= len(items):
            messagebox.showwarning("Not found", "That row no longer exists — refresh and try again.")
            return
        items[idx]["test"] = self.lab_test_entry.get().strip() or items[idx]["test"]
        items[idx]["status"] = self.lab_status_combo.get().lower() or items[idx]["status"]
        items[idx]["result"] = self.lab_result_entry.get().strip()
        items[idx]["date"] = today_str()
        self.app.persist()
        self._refresh_lab_reports(mobile)
        messagebox.showinfo("Updated", "Lab report updated — the patient will see the change.")

    def _on_labs_patient_change(self, event=None):
        mobile = self._selected_mobile_from_combo(self.labs_patient_combo)
        if mobile:
            self._refresh_lab_reports(mobile)

    # ---------------- Schedule tab (arrival timing) ----------------
    def _build_schedule_tab(self):
        f = self.tab_schedule
        pad = tk.Frame(f, bg=PAPER_RAISED)
        pad.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(pad, text="Schedule patient arrival timing", font=F_HEAD2, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(pad, text="Select an appointment below, choose a new date/time, then reschedule.",
                 font=F_SMALL, bg=PAPER_RAISED, fg=INK_SOFT).pack(anchor="w", pady=(2, 10))

        cols = ("token", "patient", "mobile", "date", "time", "status")
        self.sched_tree = ttk.Treeview(pad, columns=cols, show="headings", height=11)
        for c in cols:
            self.sched_tree.heading(c, text=c.title())
            self.sched_tree.column(c, width=130, anchor="center")
        self.sched_tree.pack(fill="both", expand=True, pady=(0, 10))
        self.sched_tree.bind("<<TreeviewSelect>>", self._on_sched_row_select)

        formrow = tk.Frame(pad, bg=PAPER_RAISED)
        formrow.pack(fill="x")
        self.sched_date_entry = labeled_entry(formrow, "New date (YYYY-MM-DD)", width=18)
        self.sched_date_entry.pack(side="left", padx=(0, 12))
        tk.Label(formrow, text="New time slot", font=F_SMALL, fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(8, 3))
        self.sched_slot_combo = ttk.Combobox(formrow, values=TIMESLOTS, state="readonly", font=F_BODY, width=16)
        self.sched_slot_combo.current(0)
        self.sched_slot_combo.pack(side="left", ipady=3)

        btnrow = tk.Frame(pad, bg=PAPER_RAISED)
        btnrow.pack(fill="x", pady=(12, 0))
        make_btn(btnrow, "Reschedule selected appointment", self._reschedule_selected, "primary").pack(side="left")
        make_btn(btnrow, "Cancel selected appointment", self._cancel_selected, "danger").pack(side="left", padx=8)

    def _refresh_schedule(self):
        for i in self.sched_tree.get_children():
            self.sched_tree.delete(i)
        dept = self.app.session["dept"]
        rows = [a for a in self.app.data["appointments"] if a["dept"] == dept]
        rows.sort(key=lambda a: (a["date"], a["time"]))
        for a in rows:
            self.sched_tree.insert("", "end", iid=a["id"],
                                    values=(a["token"], a["patient_name"], a["mobile"],
                                            a["date"], a["time"], a["status"].title()))

    def _on_sched_row_select(self, event=None):
        sel = self.sched_tree.selection()
        if not sel:
            return
        vals = self.sched_tree.item(sel[0], "values")
        self.sched_date_entry.delete(0, "end")
        self.sched_date_entry.insert(0, vals[3])
        if vals[4] in TIMESLOTS:
            self.sched_slot_combo.set(vals[4])

    def _reschedule_selected(self):
        sel = self.sched_tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select an appointment to reschedule.")
            return
        new_date = self.sched_date_entry.get().strip()
        try:
            datetime.date.fromisoformat(new_date)
        except ValueError:
            messagebox.showwarning("Invalid date", "Please enter a valid date as YYYY-MM-DD.")
            return
        new_slot = self.sched_slot_combo.get()
        appt_id = sel[0]

        self.app.refresh_from_disk()
        for a in self.app.data["appointments"]:
            if a["id"] == appt_id:
                a["date"], a["time"] = new_date, new_slot
                a["status"] = "waiting"
                break
        self.app.persist()
        self._refresh_schedule()
        self._refresh_queue()
        messagebox.showinfo("Rescheduled", f"Patient arrival updated to {new_date} {new_slot}.")

    def _cancel_selected(self):
        sel = self.sched_tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select an appointment to cancel.")
            return
        appt_id = sel[0]
        if not messagebox.askyesno("Confirm", "Cancel this appointment?"):
            return
        self.app.refresh_from_disk()
        for a in self.app.data["appointments"]:
            if a["id"] == appt_id:
                a["status"] = "cancelled"
                break
        self.app.persist()
        self._refresh_schedule()
        self._refresh_queue()

    # ---------------- lifecycle ----------------
    def on_show(self):
        self.app.refresh_from_disk()
        options = self._patient_options()
        self.presc_patient_combo["values"] = options
        self.presc_patient_combo.set(options[0])
        self.presc_patient_combo.bind("<<ComboboxSelected>>", self._on_presc_patient_change)
        self.labs_patient_combo["values"] = options
        self.labs_patient_combo.set(options[0])
        self.labs_patient_combo.bind("<<ComboboxSelected>>", self._on_labs_patient_change)

        self._refresh_queue()
        self._on_presc_patient_change()
        self._on_labs_patient_change()
        self._refresh_schedule()
        self._schedule_refresh()

    def _schedule_refresh(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(REFRESH_MS, self._tick)

    def _tick(self):
        if self.app.session["role"] != "doctor":
            return
        self.app.refresh_from_disk()
        self._refresh_queue()
        self._refresh_schedule()
        self._schedule_refresh()


# ============================================================================
#  ENTRY POINT
# ============================================================================
def main():
    app = IKretApp()
    app.mainloop()


if __name__ == "__main__":
    main()
