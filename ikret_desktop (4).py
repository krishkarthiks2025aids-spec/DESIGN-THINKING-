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

NEW IN THIS BUILD
-----------------
1. Every screen now carries the Tamil Nadu Government Health Branch
   watermark background (add_branch_background is called from every
   screen's __init__, not just the role picker).
2. A "Medicine Assistant" sits next to the doctor's prescription field.
   As the doctor types, it live-filters MEDICINES by the letters typed
   and lists matches; clicking a suggestion drops it straight into the
   field.
3. A "Health Assistant" tab on the patient dashboard asks the patient's
   preferred language and their area, then live-suggests the nearest
   government hospital (name + address + distance), refreshing itself
   every few seconds the way a live locator would.
4. The patient dashboard's own text (tab names, headings, buttons) is
   re-rendered in the patient's chosen language using the existing
   TRANSLATIONS / tr() language packs.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import random
import datetime
import uuid

# QR code support -- optional. If 'qrcode' isn't installed, the app still
# runs fine; QR panels just show a note telling you what to pip install.
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
from PIL import ImageTk

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
#  AI ASSISTANT DATA  —  medicine reference, govt. hospitals, language packs
# ============================================================================
MEDICINES = {
    "A": ["Amoxicillin", "Azithromycin", "Aspirin", "Atorvastatin", "Amlodipine", "Albendazole"],
    "B": ["Betadine", "Betamethasone", "Bisacodyl", "Budesonide"],
    "C": ["Ciprofloxacin", "Cetirizine", "Chloroquine", "Clopidogrel", "Cough Syrup (Tixylix)"],
    "D": ["Diclofenac", "Domperidone", "Doxycycline", "Dolo 650 (Paracetamol)"],
    "E": ["Enalapril", "Erythromycin", "Ezetimibe"],
    "F": ["Ferrous Sulphate", "Folic Acid", "Furosemide", "Fluconazole"],
    "G": ["Gentamicin", "Glimepiride", "Glyceryl Trinitrate"],
    "H": ["Hydrochlorothiazide", "Hydroxychloroquine"],
    "I": ["Ibuprofen", "Insulin (Human Mixtard)", "Isosorbide Dinitrate"],
    "L": ["Levothyroxine", "Lisinopril", "Loratadine", "Losartan"],
    "M": ["Metformin", "Metronidazole", "Montelukast", "Multivitamin (Becosules)"],
    "N": ["Nifedipine", "Norfloxacin"],
    "O": ["Omeprazole", "Ondansetron", "ORS (Oral Rehydration Salts)"],
    "P": ["Paracetamol", "Pantoprazole", "Prednisolone", "Phenytoin"],
    "R": ["Ranitidine", "Rabeprazole"],
    "S": ["Salbutamol Inhaler", "Sertraline"],
    "T": ["Tetanus Toxoid", "Tramadol", "Telmisartan"],
    "V": ["Vitamin D3", "Vitamin B12"],
    "Z": ["Zinc Sulphate"],
}
# Flat, sorted list used by the autocomplete assistant.
ALL_MEDICINES = sorted({m for group in MEDICINES.values() for m in group})

GOVT_HOSPITALS = [
    {"name": "Government General Hospital", "area": "Chennai",
     "address": "Park Town, Chennai - 600003", "distance_km": 2.4},
    {"name": "Government Rajaji Hospital", "area": "Madurai",
     "address": "Panagal Nagar, Madurai - 625020", "distance_km": 3.1},
    {"name": "Coimbatore Medical College Hospital", "area": "Coimbatore",
     "address": "Trichy Road, Coimbatore - 641018", "distance_km": 1.8},
    {"name": "Govt. Mohan Kumaramangalam Medical College Hospital", "area": "Salem",
     "address": "Steel Plant Road, Salem - 636030", "distance_km": 4.6},
    {"name": "Thanjavur Medical College Hospital", "area": "Thanjavur",
     "address": "Thanjavur - 613004", "distance_km": 2.9},
    {"name": "Government Vellore Medical College Hospital", "area": "Vellore",
     "address": "Adukamparai, Vellore - 632011", "distance_km": 3.7},
    {"name": "Tirunelveli Medical College Hospital", "area": "Tirunelveli",
     "address": "High Ground, Tirunelveli - 627011", "distance_km": 2.2},
    {"name": "Government Hospital, Tiruppur", "area": "Tiruppur",
     "address": "Kumaran Road, Tiruppur - 641601", "distance_km": 2.0},
    {"name": "Government Erode Medical College Hospital", "area": "Erode",
     "address": "Perundurai, Erode - 638053", "distance_km": 3.3},
    {"name": "Government Primary Health Centre (nearest PHC)", "area": "Local",
     "address": "Ask your Village Health Nurse for the exact address", "distance_km": 1.1},
]

LANGUAGES = ["English", "Tamil", "Hindi"]

TRANSLATIONS = {
    "English": {
        "my_services": "My Services", "book": "Book Appointment", "appts": "My Appointments",
        "presc": "Prescriptions", "labs": "Lab Reports", "assistant": "Health Assistant",
        "assistant_title": "I-KRET Health Assistant",
        "assistant_sub": "Tell the assistant your language and area — it finds the\nnearest government hospital and keeps the list live.",
        "lang_label": "Preferred language", "loc_label": "Your area / city",
        "find_hosp": "Find nearby government hospital",
        "hosp_results": "Nearby government hospitals (live)",
        "no_loc": "Enter your area and tap 'Find nearby government hospital'.",
        "logout": "Log out",
        "dept_label": "Department", "slot_label": "Preferred time slot",
        "book_btn": "Confirm booking", "token_msg": "Your token number is",
        "no_appts": "No appointments yet.", "no_presc": "No prescriptions yet.",
        "no_labs": "No lab reports yet.", "welcome": "Welcome",
        "updated": "Updated just now", "distance": "km away",
    },
    "Tamil": {
        "my_services": "எனது சேவைகள்", "book": "நேரம் பதிவு செய்யவும்", "appts": "எனது நேரங்கள்",
        "presc": "மருந்து சீட்டுகள்", "labs": "ஆய்வக அறிக்கைகள்", "assistant": "சுகாதார உதவியாளர்",
        "assistant_title": "I-KRET சுகாதார உதவியாளர்",
        "assistant_sub": "உங்கள் மொழி மற்றும் பகுதியை உதவியாளரிடம் கூறுங்கள் —\nஅருகிலுள்ள அரசு மருத்துவமனையை உடனடியாகக் காட்டும்.",
        "lang_label": "விருப்பமான மொழி", "loc_label": "உங்கள் பகுதி / நகரம்",
        "find_hosp": "அருகிலுள்ள அரசு மருத்துவமனையைக் கண்டறியவும்",
        "hosp_results": "அருகிலுள்ள அரசு மருத்துவமனைகள் (நேரடி)",
        "no_loc": "உங்கள் பகுதியை உள்ளிட்டு பொத்தானை அழுத்தவும்.",
        "logout": "வெளியேறு",
        "dept_label": "பிரிவு", "slot_label": "விருப்பமான நேரம்",
        "book_btn": "பதிவை உறுதிசெய்யவும்", "token_msg": "உங்கள் டோக்கன் எண்",
        "no_appts": "இதுவரை நேரங்கள் இல்லை.", "no_presc": "இதுவரை மருந்து சீட்டுகள் இல்லை.",
        "no_labs": "இதுவரை அறிக்கைகள் இல்லை.", "welcome": "வணக்கம்",
        "updated": "இப்போதுதான் புதுப்பிக்கப்பட்டது", "distance": "கி.மீ தொலைவில்",
    },
    "Hindi": {
        "my_services": "मेरी सेवाएं", "book": "अपॉइंटमेंट बुक करें", "appts": "मेरी अपॉइंटमेंट",
        "presc": "नुस्खे", "labs": "लैब रिपोर्ट", "assistant": "स्वास्थ्य सहायक",
        "assistant_title": "I-KRET स्वास्थ्य सहायक",
        "assistant_sub": "सहायक को अपनी भाषा और क्षेत्र बताएं — यह नज़दीकी\nसरकारी अस्पताल तुरंत दिखाएगा।",
        "lang_label": "पसंदीदा भाषा", "loc_label": "आपका क्षेत्र / शहर",
        "find_hosp": "नज़दीकी सरकारी अस्पताल खोजें",
        "hosp_results": "नज़दीकी सरकारी अस्पताल (लाइव)",
        "no_loc": "अपना क्षेत्र दर्ज करें और बटन दबाएं।",
        "logout": "लॉग आउट",
        "dept_label": "विभाग", "slot_label": "पसंदीदा समय",
        "book_btn": "बुकिंग की पुष्टि करें", "token_msg": "आपका टोकन नंबर",
        "no_appts": "अभी तक कोई अपॉइंटमेंट नहीं।", "no_presc": "अभी तक कोई नुस्खा नहीं।",
        "no_labs": "अभी तक कोई रिपोर्ट नहीं।", "welcome": "नमस्ते",
        "updated": "अभी अपडेट हुआ", "distance": "किमी दूर",
    },
}


def tr(lang, key):
    pack = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
    return pack.get(key, TRANSLATIONS["English"].get(key, key))


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
#  APPOINTMENT QR CODES  —  encode a booking, scan/paste it back, look it up
# ============================================================================
def appointment_qr_payload(appt):
    """A compact '|'-delimited string encoded into the QR so any scanner (or
    I-KRET's own Scan screen) can reconstruct the booking offline, with no
    server round-trip needed."""
    fields = ["IKRET-APPT", appt.get("id", ""), appt.get("token", ""),
              appt.get("patient_name", ""), appt.get("mobile", ""), appt.get("dept", ""),
              appt.get("doctor", ""), appt.get("slot", ""), appt.get("date", ""),
              appt.get("status", "")]
    return "|".join(str(f) for f in fields)


def parse_appointment_qr(text):
    """Parse a scanned/pasted QR payload back into a dict, or None if the
    text isn't an I-KRET appointment code."""
    if not text:
        return None
    parts = text.strip().split("|")
    if len(parts) < 10 or parts[0] != "IKRET-APPT":
        return None
    keys = ["tag", "id", "token", "patient_name", "mobile", "dept",
            "doctor", "slot", "date", "status"]
    return dict(zip(keys, parts))


def find_appointment_by_id(data, appt_id):
    for a in data.get("appointments", []):
        if a.get("id") == appt_id:
            return a
    return None


def make_qr_photo(data_str, box_size=5, border=2):
    """Render a scannable QR PhotoImage for a Tkinter Label. Returns None if
    the optional 'qrcode' package isn't installed (pip install qrcode)."""
    if not QR_AVAILABLE or not data_str:
        return None
    qr = qrcode.QRCode(box_size=box_size, border=border)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color=TEAL_DARK, back_color=WHITE).convert("RGB")
    return ImageTk.PhotoImage(img)


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


def add_branch_background(frame, subtitle="TAMIL NADU GOVERNMENT HEALTH BRANCH · I-KRET"):
    """Draws a subtle teal cross-hatch watermark behind a screen's content so
    every page visibly ties back to the govt. health branch this app serves.
    Called from every screen's __init__ so the watermark is universal."""
    canvas = tk.Canvas(frame, bg=PAPER, highlightthickness=0, bd=0)
    canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
    canvas.lower("all")  # keep it behind whatever gets packed/placed on top

    def redraw(event=None):
        canvas.delete("all")
        w = frame.winfo_width() or 980
        h = frame.winfo_height() or 680
        canvas.configure(width=w, height=h)
        step = 90
        for y in range(-step, h + step, step):
            for x in range(-step, w + step, step):
                sz = 9
                canvas.create_line(x - sz, y, x + sz, y, fill=LINE, width=2)
                canvas.create_line(x, y - sz, x, y + sz, fill=LINE, width=2)
        canvas.create_text(w - 14, h - 12, anchor="se", text=subtitle, font=F_SMALL, fill=LINE)
        canvas.lower()

    frame.bind("<Configure>", redraw)
    frame.after(50, redraw)
    return canvas


def add_tech_hero_background(frame, corner_text="I-KRET · SMART OP BOOKING"):
    """A dark navy-to-teal glow gradient with soft halo rings, echoing the
    phone + stethoscope hero art used in I-KRET's marketing banner. Used only
    on the home / role-selection screen, so the app opens on a bold splash
    before settling into the calmer paper-registry look used in the rest of
    the flow."""
    TOP = (7, 20, 38)       # near-black navy
    BOTTOM = (10, 62, 66)   # deep teal
    canvas = tk.Canvas(frame, highlightthickness=0, bd=0)
    canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
    canvas.lower("all")

    def lerp(a, b, t):
        return int(a + (b - a) * t)

    def redraw(event=None):
        canvas.delete("all")
        w = frame.winfo_width() or 980
        h = frame.winfo_height() or 680
        canvas.configure(width=w, height=h)

        steps = 90
        for i in range(steps):
            t = i / steps
            r, g, b = (lerp(TOP[k], BOTTOM[k], t) for k in range(3))
            color = f"#{r:02x}{g:02x}{b:02x}"
            y0, y1 = int(h * i / steps), int(h * (i + 1) / steps) + 1
            canvas.create_rectangle(0, y0, w, y1, fill=color, outline=color)

        # soft halo rings, standing in for the glowing phone/device motif
        cx, cy = int(w * 0.5), int(h * 0.66)
        for rad, ring_color, ring_w in [(190, "#123B44", 10), (140, "#1B5A62", 8), (95, "#2C8B8F", 6)]:
            canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                outline=ring_color, width=ring_w)
        canvas.create_oval(cx - 34, cy - 34, cx + 34, cy + 34, fill="#39C7C0", outline="")

        # faint circuit-dot texture for a 'tech' feel
        for gx in range(0, w, 52):
            for gy in range(0, h, 52):
                canvas.create_oval(gx, gy, gx + 2, gy + 2, fill="#0F3A3C", outline="")

        canvas.create_text(w - 16, 16, anchor="ne", text=corner_text,
                            font=F_EYEBROW, fill="#8FE0D8")
        canvas.lower()

    frame.bind("<Configure>", redraw)
    frame.after(50, redraw)
    return canvas


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
#  MEDICINE ASSISTANT  —  live autocomplete for the doctor's prescription pad
# ============================================================================
class MedicineAssistant(tk.Frame):
    """An entry field + a live-filtering suggestion list. As the doctor types
    each letter, the box below narrows to medicines whose name starts with
    (or contains) what's typed so far, pulled straight from MEDICINES."""
    def __init__(self, parent, on_pick=None):
        super().__init__(parent, bg=PAPER_RAISED)
        self.on_pick = on_pick

        tk.Label(self, text="Medicine name (assistant suggests as you type)",
                 font=F_SMALL, fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(8, 3))
        self.entry = tk.Entry(self, font=F_MONO, relief="solid", bd=1,
                               highlightthickness=1, highlightbackground=LINE,
                               highlightcolor=TEAL)
        self.entry.pack(fill="x", ipady=6)
        self.entry.bind("<KeyRelease>", self._on_key)

        eyebrow(self, "MEDICINE ASSISTANT · LIVE MATCHES").pack(anchor="w", pady=(8, 4))
        list_wrap = tk.Frame(self, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
        list_wrap.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_wrap, font=F_BODY, height=6, bd=0,
                                   highlightthickness=0, activestyle="none",
                                   selectbackground=TEAL_PALE, selectforeground=TEAL_DARK)
        self.listbox.pack(fill="both", expand=True, padx=1, pady=1)
        self.listbox.bind("<<ListboxSelect>>", self._on_pick_suggestion)
        self._refresh_list("")

    def _matches(self, prefix):
        prefix = prefix.strip().upper()
        if not prefix:
            return ALL_MEDICINES[:12]
        letter = prefix[0]
        pool = MEDICINES.get(letter, [])
        starts = [m for m in pool if m.upper().startswith(prefix)]
        contains = [m for m in ALL_MEDICINES if prefix in m.upper() and m not in starts]
        return (starts + contains)[:12]

    def _refresh_list(self, prefix):
        self.listbox.delete(0, tk.END)
        for m in self._matches(prefix):
            self.listbox.insert(tk.END, m)

    def _on_key(self, event=None):
        self._refresh_list(self.entry.get())

    def _on_pick_suggestion(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        value = self.listbox.get(sel[0])
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        if self.on_pick:
            self.on_pick(value)

    def get(self):
        return self.entry.get().strip()

    def clear(self):
        self.entry.delete(0, tk.END)
        self._refresh_list("")


# ============================================================================
#  HEALTH ASSISTANT  —  language + live nearby government hospital finder
# ============================================================================
class HealthAssistant(tk.Frame):
    """Asks the patient's preferred language and area, then keeps a live
    (auto-refreshing) list of the nearest government hospitals on screen."""
    def __init__(self, parent, app, on_language_change=None):
        super().__init__(parent, bg=PAPER_RAISED)
        self.app = app
        self.on_language_change = on_language_change
        self.lang = "English"
        self._after_id = None
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        lang = self.lang

        eyebrow(self, "AI HEALTH ASSISTANT").pack(anchor="w", pady=(4, 6))
        tk.Label(self, text=tr(lang, "assistant_title"), font=F_HEAD, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(self, text=tr(lang, "assistant_sub"), font=F_BODY, bg=PAPER_RAISED,
                 fg=INK_SOFT, justify="left").pack(anchor="w", pady=(2, 14))

        row = tk.Frame(self, bg=PAPER_RAISED)
        row.pack(fill="x")

        left = tk.Frame(row, bg=PAPER_RAISED)
        left.pack(side="left", fill="y", padx=(0, 18))
        tk.Label(left, text=tr(lang, "lang_label"), font=F_SMALL, fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(0, 3))
        self.lang_combo = ttk.Combobox(left, values=LANGUAGES, state="readonly", font=F_BODY, width=16)
        self.lang_combo.set(lang)
        self.lang_combo.pack(anchor="w", ipady=3)
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_change)

        right = tk.Frame(row, bg=PAPER_RAISED)
        right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text=tr(lang, "loc_label"), font=F_SMALL, fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(0, 3))
        self.loc_entry = tk.Entry(right, font=F_MONO, relief="solid", bd=1,
                                   highlightthickness=1, highlightbackground=LINE, highlightcolor=TEAL)
        self.loc_entry.pack(fill="x", ipady=6)

        make_btn(self, tr(lang, "find_hosp"), self._find_hospitals, "amber").pack(anchor="w", pady=(12, 4))

        eyebrow(self, tr(lang, "hosp_results")).pack(anchor="w", pady=(14, 6))
        self.results_wrap = tk.Frame(self, bg=PAPER_RAISED)
        self.results_wrap.pack(fill="both", expand=True)
        self.status_label = tk.Label(self, text="", font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED)
        self.status_label.pack(anchor="w", pady=(6, 0))

        self._area = None
        self._render_placeholder()

    def _on_lang_change(self, event=None):
        self.lang = self.lang_combo.get()
        if self.on_language_change:
            self.on_language_change(self.lang)
        had_area = self._area
        self._build()
        if had_area:
            self.loc_entry.insert(0, had_area)
            self._find_hospitals()

    def _render_placeholder(self):
        for w in self.results_wrap.winfo_children():
            w.destroy()
        tk.Label(self.results_wrap, text=tr(self.lang, "no_loc"), font=F_BODY,
                 fg=INK_SOFT, bg=PAPER_RAISED, justify="left").pack(anchor="w")

    def _find_hospitals(self):
        area = self.loc_entry.get().strip()
        if not area:
            self._render_placeholder()
            return
        self._area = area
        self._render_results()
        # keep the list "live" -- re-poll on an interval like a real locator
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(REFRESH_MS, self._live_tick)

    def _live_tick(self):
        if self._area and self.winfo_exists():
            self._render_results(jitter=True)
            self._after_id = self.after(REFRESH_MS, self._live_tick)

    def _matching_hospitals(self, area):
        area_low = area.lower()
        direct = [h for h in GOVT_HOSPITALS if area_low in h["area"].lower()]
        if direct:
            return direct
        # No exact area match -- fall back to the nearest PHC plus 2 closest
        # listed hospitals by distance, same behaviour a live locator would
        # show while it widens its search radius.
        fallback = sorted(GOVT_HOSPITALS, key=lambda h: h["distance_km"])[:3]
        return fallback

    def _render_results(self, jitter=False):
        for w in self.results_wrap.winfo_children():
            w.destroy()
        matches = self._matching_hospitals(self._area)
        ranked = []
        for h in matches:
            dist = h["distance_km"]
            if jitter:
                dist = max(0.5, dist + random.uniform(-0.3, 0.3))
            ranked.append((dist, h))
        ranked.sort(key=lambda t: t[0])

        for dist, h in ranked:
            card = tk.Frame(self.results_wrap, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
            card.pack(fill="x", pady=4)
            inner = tk.Frame(card, bg=WHITE)
            inner.pack(fill="x", padx=12, pady=8)
            tk.Label(inner, text=h["name"], font=F_HEAD2, bg=WHITE, fg=INK).pack(anchor="w")
            tk.Label(inner, text=h["address"], font=F_SMALL, bg=WHITE, fg=INK_SOFT).pack(anchor="w")
            tag_label(inner, f"{dist:.1f} {tr(self.lang, 'distance')}", "normal").pack(anchor="w", pady=(4, 0))

        self.status_label.config(text=f"{tr(self.lang, 'updated')} · {now_str()}")


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
        self.session = {"role": None, "mobile": None, "cert": None, "name": None,
                         "dept": None, "lang": "English"}

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
        for F in (RoleScreen, PatientLoginScreen, DoctorLoginScreen, ScanScreen,
                  PatientDashboard, DoctorDashboard):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show("RoleScreen")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- navigation -------------------------------------------------
    def show(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    def sign_out(self):
        self.session = {"role": None, "mobile": None, "cert": None, "name": None,
                         "dept": None, "lang": "English"}
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
        add_tech_hero_background(self)
        card = Card(self)
        card.pack(padx=10, pady=10, expand=True)
        eyebrow(card.body, "STEP 1 · CHOOSE YOUR ROLE").pack(anchor="w", pady=(0, 10))
        tk.Label(card.body, text="Continue as", font=F_HEAD, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(card.body, text="Choose how you'd like to use I-KRET today.",
                 font=F_BODY, bg=PAPER_RAISED, fg=INK_SOFT).pack(anchor="w", pady=(2, 18))

        row = tk.Frame(card.body, bg=PAPER_RAISED)
        row.pack()
        for text, sub, cmd in [
            ("🧑  Patient", "Book & manage OP visits", lambda: app.show("PatientLoginScreen")),
            ("🩺  Doctor", "Manage OP queue & records", lambda: app.show("DoctorLoginScreen")),
            ("🔍  Scan / Verify", "Scan a QR to view a booking", lambda: app.show("ScanScreen")),
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
        add_tech_hero_background(self)
        card = Card(self)
        card.pack(padx=10, pady=10, expand=True)
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

    def _show_err(self, msg):
        self.err.config(text=msg)
        self.err.pack(fill="x", pady=(0, 8), before=self.aadhaar_entry.master.winfo_children()[0]
                       if False else None)
        # simplest reliable placement: just re-pack under the heading area
        self.err.pack_forget()
        self.err.pack(anchor="w", pady=(0, 8))

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

        app = self.app
        app.refresh_from_disk()
        app.data.setdefault("patients", {})
        app.data["patients"][mobile] = {"name": name, "aadhaar_last4": aadhaar[-4:]}
        app.persist()
        app.session.update({"role": "patient", "mobile": mobile, "name": name, "lang": "English"})
        app.set_session_label()
        app.show("PatientDashboard")


# ============================================================================
#  SCREEN: DOCTOR LOGIN / REGISTER
# ============================================================================
class DoctorLoginScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        add_tech_hero_background(self)
        card = Card(self)
        card.pack(padx=10, pady=10, expand=True)
        eyebrow(card.body, "STEP 2 · DOCTOR SIGN-IN").pack(anchor="w", pady=(0, 10))
        tk.Label(card.body, text="Doctor sign-in", font=F_HEAD, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(card.body,
                 text="Enter your medical council registration number. First-time\nsign-in registers you against the department you select.",
                 font=F_BODY, bg=PAPER_RAISED, fg=INK_SOFT, justify="left").pack(anchor="w", pady=(2, 10))

        self.err = tk.Label(card.body, text="", font=F_SMALL, fg=DANGER, bg=DANGER_PALE, anchor="w")

        self.cert_entry = labeled_entry(card.body, "Medical council reg. number")
        self.name_entry = labeled_entry(card.body, "Full name (Dr. ...)")
        self.dept_combo = labeled_combo(card.body, "Department", DEPTS)

        btnrow = tk.Frame(card.body, bg=PAPER_RAISED)
        btnrow.pack(fill="x", pady=(16, 0))
        make_btn(btnrow, "Sign in / Register", self.login, "primary").pack(fill="x")
        make_btn(btnrow, "Back", lambda: app.show("RoleScreen"), "ghost").pack(fill="x", pady=(8, 0))

    def _show_err(self, msg):
        self.err.pack_forget()
        self.err.config(text=msg)
        self.err.pack(anchor="w", pady=(0, 8))

    def login(self):
        self.err.pack_forget()
        cert = self.cert_entry.get().strip().upper()
        name = self.name_entry.get().strip()
        dept = self.dept_combo.get()
        if not cert:
            return self._show_err("Please enter your registration number.")

        app = self.app
        app.refresh_from_disk()
        app.data.setdefault("doctors", {})
        existing = app.data["doctors"].get(cert)
        if existing:
            name = existing["name"]
            dept = existing["dept"]
        else:
            if not name:
                return self._show_err("Please enter your full name to register.")
            app.data["doctors"][cert] = {"name": name, "dept": dept}
            app.persist()

        app.session.update({"role": "doctor", "cert": cert, "name": name, "dept": dept})
        app.set_session_label()
        app.show("DoctorDashboard")


# ============================================================================
#  SCREEN: SCAN / VERIFY APPOINTMENT  —  the OP-counter "scan to view" kiosk
# ============================================================================
class ScanScreen(tk.Frame):
    """Anyone at the OP counter can scan a patient's appointment QR (or paste
    its decoded text) here, and the matching booking is pulled straight out
    of I-KRET's own records — no separate app or server needed."""
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        add_tech_hero_background(self)
        card = Card(self, padx=22, pady=18)
        card.pack(padx=10, pady=10, expand=True)

        eyebrow(card.body, "SCAN / VERIFY APPOINTMENT").pack(anchor="w", pady=(0, 10))
        tk.Label(card.body, text="Look up a booking", font=F_HEAD, bg=PAPER_RAISED, fg=INK).pack(anchor="w")
        tk.Label(card.body,
                 text="Scan a patient's appointment QR with a webcam, or paste its\ndecoded text below.",
                 font=F_BODY, bg=PAPER_RAISED, fg=INK_SOFT, justify="left").pack(anchor="w", pady=(2, 12))

        self.entry = labeled_entry(card.body, "Scanned / pasted QR text", width=48)

        row = tk.Frame(card.body, bg=PAPER_RAISED)
        row.pack(fill="x", pady=(14, 0))
        make_btn(row, "Look up", self._lookup, "primary").pack(side="left")
        make_btn(row, "Scan with camera", self._scan_camera, "amber").pack(side="left", padx=(10, 0))
        make_btn(row, "Back", lambda: app.show("RoleScreen"), "ghost").pack(side="left", padx=(10, 0))

        self.result_card = Card(card.body, padx=16, pady=14)
        self.result = tk.Label(self.result_card.body, text="Nothing scanned yet.",
                                font=F_BODY, fg=INK_SOFT, bg=PAPER_RAISED, justify="left", wraplength=420)
        self.result.pack(anchor="w")
        self.result_card.pack(fill="x", pady=(16, 0))

    def _lookup(self):
        parsed = parse_appointment_qr(self.entry.get())
        if not parsed:
            self.result.config(fg=DANGER, text="That doesn't look like an I-KRET appointment QR code.")
            return
        self.app.refresh_from_disk()
        appt = find_appointment_by_id(self.app.data, parsed["id"]) or parsed
        self._render(appt)

    def _render(self, appt):
        self.result.config(fg=TEAL_DARK, text=(
            f"Patient:     {appt.get('patient_name', '')}\n"
            f"Token:       {appt.get('token', '')}      Status: {appt.get('status', '')}\n"
            f"Department:  {appt.get('dept', '')}\n"
            f"Doctor:      {appt.get('doctor', '')}\n"
            f"Slot:        {appt.get('slot', '')}      Date: {appt.get('date', '')}"
        ))

    def _scan_camera(self):
        """Live webcam QR scan using OpenCV's built-in decoder (no extra
        zbar/pyzbar dependency needed). Requires: pip install opencv-python."""
        try:
            import cv2
        except ImportError:
            self.result.config(fg=DANGER, text="Camera scanning needs 'opencv-python' "
                                                 "(pip install opencv-python). You can paste the "
                                                 "QR's decoded text above instead.")
            return
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.result.config(fg=DANGER, text="No camera found. Paste the QR's decoded text instead.")
            return
        detector = cv2.QRCodeDetector()
        found_text = None
        try:
            for _ in range(400):
                ok, frame = cap.read()
                if not ok:
                    break
                data, points, _ = detector.detectAndDecode(frame)
                cv2.imshow("I-KRET · point the appointment QR at the camera (Esc to cancel)", frame)
                if data:
                    found_text = data
                    break
                if cv2.waitKey(1) & 0xFF == 27:
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
        if found_text:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, found_text)
            self._lookup()
        else:
            self.result.config(fg=DANGER, text="No QR code detected. Try again or paste the text.")


# ============================================================================
#  SCREEN: PATIENT DASHBOARD
# ============================================================================
class PatientDashboard(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        add_branch_background(self)

        outer = tk.Frame(self, bg=PAPER)
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        header = tk.Frame(outer, bg=PAPER)
        header.pack(fill="x")
        self.title_label = tk.Label(header, text="", font=F_HEAD, bg=PAPER, fg=INK)
        self.title_label.pack(side="left")
        make_btn(header, "Log out", app.sign_out, "ghost").pack(side="right")

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True, pady=(12, 0))

        self.tab_book = tk.Frame(self.notebook, bg=PAPER_RAISED)
        self.tab_appts = tk.Frame(self.notebook, bg=PAPER_RAISED)
        self.tab_presc = tk.Frame(self.notebook, bg=PAPER_RAISED)
        self.tab_labs = tk.Frame(self.notebook, bg=PAPER_RAISED)
        self.tab_assist = tk.Frame(self.notebook, bg=PAPER_RAISED)

        for t in (self.tab_book, self.tab_appts, self.tab_presc, self.tab_labs, self.tab_assist):
            self.notebook.add(t, text=" ")

        self._build_book_tab()
        self._build_appts_tab()
        self._build_presc_tab()
        self._build_labs_tab()
        self._build_assist_tab()

        self.lang = "English"
        self._relabel()
        self._poll()

    # ---- tab builders --------------------------------------------------
    def _build_book_tab(self):
        card = Card(self.tab_book, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        self.book_heading = eyebrow(card.body, "BOOK APPOINTMENT")
        self.book_heading.pack(anchor="w", pady=(0, 10))
        self.dept_label = tk.Label(card.body, text="Department", font=F_SMALL, fg=INK, bg=PAPER_RAISED)
        self.dept_label.pack(anchor="w", pady=(0, 3))
        self.dept_combo = ttk.Combobox(card.body, values=DEPTS, state="readonly", font=F_BODY)
        self.dept_combo.current(0)
        self.dept_combo.pack(fill="x", ipady=3)

        self.slot_label = tk.Label(card.body, text="Preferred time slot", font=F_SMALL, fg=INK, bg=PAPER_RAISED)
        self.slot_label.pack(anchor="w", pady=(10, 3))
        self.slot_combo = ttk.Combobox(card.body, values=TIMESLOTS, state="readonly", font=F_BODY)
        self.slot_combo.current(0)
        self.slot_combo.pack(fill="x", ipady=3)

        self.book_btn = make_btn(card.body, "Confirm booking", self._book, "primary")
        self.book_btn.pack(fill="x", pady=(16, 0))
        self.book_status = tk.Label(card.body, text="", font=F_BODY, fg=TEAL_DARK, bg=PAPER_RAISED, justify="left")
        self.book_status.pack(anchor="w", pady=(10, 0))
        self.qr_frame = tk.Frame(card.body, bg=PAPER_RAISED)
        self.qr_frame.pack(anchor="w", pady=(10, 0))

    def _build_appts_tab(self):
        card = Card(self.tab_appts, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        self.appts_heading = eyebrow(card.body, "MY APPOINTMENTS")
        self.appts_heading.pack(anchor="w", pady=(0, 10))

        body = tk.Frame(card.body, bg=PAPER_RAISED)
        body.pack(fill="both", expand=True)

        cols = ("date", "dept", "doctor", "slot", "token", "status")
        self.appts_tree = ttk.Treeview(body, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (100, 130, 140, 110, 70, 90)):
            self.appts_tree.heading(c, text=c.title())
            self.appts_tree.column(c, width=w, anchor="center")
        self.appts_tree.pack(side="left", fill="both", expand=True)
        self.appts_tree.bind("<<TreeviewSelect>>", self._on_appt_select)

        # side panel: pick a row above and its scan-in QR appears here
        self.appt_qr_panel = tk.Frame(body, bg=PAPER_RAISED, width=200)
        self.appt_qr_panel.pack(side="left", fill="y", padx=(14, 0))
        self.appt_qr_panel.pack_propagate(False)
        self.appt_qr_hint = tk.Label(self.appt_qr_panel,
                                      text="Select an appointment above to view its scan-in QR code.",
                                      font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED,
                                      wraplength=190, justify="left")
        self.appt_qr_hint.pack(anchor="w", pady=(0, 8))
        self.appt_qr_label = tk.Label(self.appt_qr_panel, bg=PAPER_RAISED)
        self.appt_qr_label.pack(anchor="w")

    def _build_presc_tab(self):
        card = Card(self.tab_presc, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        self.presc_heading = eyebrow(card.body, "PRESCRIPTIONS")
        self.presc_heading.pack(anchor="w", pady=(0, 10))
        cols = ("date", "doctor", "medicine", "dosage")
        self.presc_tree = ttk.Treeview(card.body, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (100, 140, 180, 160)):
            self.presc_tree.heading(c, text=c.title())
            self.presc_tree.column(c, width=w, anchor="w")
        self.presc_tree.pack(fill="both", expand=True)

    def _build_labs_tab(self):
        card = Card(self.tab_labs, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        self.labs_heading = eyebrow(card.body, "LAB REPORTS")
        self.labs_heading.pack(anchor="w", pady=(0, 10))
        cols = ("date", "title", "result")
        self.labs_tree = ttk.Treeview(card.body, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (100, 200, 280)):
            self.labs_tree.heading(c, text=c.title())
            self.labs_tree.column(c, width=w, anchor="w")
        self.labs_tree.pack(fill="both", expand=True)

    def _build_assist_tab(self):
        card = Card(self.tab_assist, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        self.assistant = HealthAssistant(card.body, self.app, on_language_change=self._on_lang_change)
        self.assistant.pack(fill="both", expand=True)

    # ---- behaviour -------------------------------------------------
    def _on_lang_change(self, lang):
        self.lang = lang
        self.app.session["lang"] = lang
        self._relabel()

    def _relabel(self):
        lang = self.lang
        s = self.app.session
        self.title_label.config(text=f"{tr(lang, 'welcome')}, {s.get('name', '')}")
        tab_texts = [tr(lang, "book"), tr(lang, "appts"), tr(lang, "presc"),
                     tr(lang, "labs"), tr(lang, "assistant")]
        for i, txt in enumerate(tab_texts):
            self.notebook.tab(i, text=txt)
        self.dept_label.config(text=tr(lang, "dept_label"))
        self.slot_label.config(text=tr(lang, "slot_label"))
        self.book_btn.config(text=tr(lang, "book_btn"))

    def on_show(self):
        self.app.refresh_from_disk()
        self._relabel()
        self._reload_tables()

    def _poll(self):
        if self.winfo_ismapped():
            self.app.refresh_from_disk()
            self._reload_tables()
        self.after(REFRESH_MS, self._poll)

    def _reload_tables(self):
        mobile = self.app.session.get("mobile")
        if not mobile:
            return
        data = self.app.data

        for row in self.appts_tree.get_children():
            self.appts_tree.delete(row)
        for a in data.get("appointments", []):
            if a.get("mobile") == mobile:
                self.appts_tree.insert("", "end", iid=a["id"],
                                        values=(a["date"], a["dept"], a["doctor"],
                                                a["slot"], a["token"], a["status"]))

        for row in self.presc_tree.get_children():
            self.presc_tree.delete(row)
        for p in data.get("prescriptions", {}).get(mobile, []):
            self.presc_tree.insert("", "end", values=(p["date"], p["doctor"], p["medicine"], p["dosage"]))

        for row in self.labs_tree.get_children():
            self.labs_tree.delete(row)
        for l in data.get("lab_reports", {}).get(mobile, []):
            self.labs_tree.insert("", "end", values=(l["date"], l["title"], l["result"]))

    def _on_appt_select(self, event=None):
        sel = self.appts_tree.selection()
        if not sel:
            return
        appt = find_appointment_by_id(self.app.data, sel[0])
        if not appt:
            return
        qr_text = appt.get("qr") or appointment_qr_payload(appt)
        photo = make_qr_photo(qr_text)
        if photo is None:
            self.appt_qr_hint.config(text="Install 'qrcode' + 'pillow' (pip install qrcode pillow) "
                                           "to render this appointment's QR code.")
            self.appt_qr_label.config(image="")
            return
        self.appt_qr_photo = photo  # keep a reference so Tk doesn't garbage-collect it
        self.appt_qr_hint.config(text=f"Token {appt.get('token', '')} · scan this at the OP counter "
                                       "to pull up this booking instantly.")
        self.appt_qr_label.config(image=photo)

    def _book(self):
        app = self.app
        mobile = app.session.get("mobile")
        name = app.session.get("name")
        if not mobile:
            return
        app.refresh_from_disk()
        dept = self.dept_combo.get()
        slot = self.slot_combo.get()
        token = new_token(app.data)
        appt = {
            "id": str(uuid.uuid4())[:8],
            "mobile": mobile,
            "patient_name": name,
            "dept": dept,
            "doctor": DOCTOR_MAP.get(dept, ""),
            "slot": slot,
            "date": today_str(),
            "token": token,
            "urgency": "normal",
            "status": "waiting",
        }
        appt["qr"] = appointment_qr_payload(appt)
        app.data.setdefault("appointments", []).append(appt)
        app.persist()
        self.book_status.config(text=f"{tr(self.lang, 'token_msg')}: {token}  ·  {dept}  ·  {slot}")
        self._show_booking_qr(appt)
        self._reload_tables()

    def _show_booking_qr(self, appt):
        for w in self.qr_frame.winfo_children():
            w.destroy()
        photo = make_qr_photo(appt.get("qr", ""))
        if photo is None:
            tk.Label(self.qr_frame,
                     text="Install 'qrcode' + 'pillow' (pip install qrcode pillow) to show a "
                          "scannable token QR here.",
                     font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED, wraplength=280, justify="left").pack(anchor="w")
            return
        self.book_qr_photo = photo  # keep a reference so Tk doesn't garbage-collect it
        tk.Label(self.qr_frame, text="Show this at the OP counter — scanning it opens your appointment.",
                 font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED, wraplength=280, justify="left").pack(anchor="w", pady=(0, 6))
        tk.Label(self.qr_frame, image=photo, bg=WHITE, bd=1, relief="solid").pack(anchor="w")


# ============================================================================
#  SCREEN: DOCTOR DASHBOARD
# ============================================================================
class DoctorDashboard(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app
        add_branch_background(self)

        outer = tk.Frame(self, bg=PAPER)
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        header = tk.Frame(outer, bg=PAPER)
        header.pack(fill="x")
        self.title_label = tk.Label(header, text="", font=F_HEAD, bg=PAPER, fg=INK)
        self.title_label.pack(side="left")
        make_btn(header, "Log out", app.sign_out, "ghost").pack(side="right")

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True, pady=(12, 0))

        self.tab_queue = tk.Frame(self.notebook, bg=PAPER_RAISED)
        self.tab_presc = tk.Frame(self.notebook, bg=PAPER_RAISED)
        self.tab_labs = tk.Frame(self.notebook, bg=PAPER_RAISED)

        self.notebook.add(self.tab_queue, text="OP Queue")
        self.notebook.add(self.tab_presc, text="Write Prescription")
        self.notebook.add(self.tab_labs, text="Lab Reports")

        self._build_queue_tab()
        self._build_presc_tab()
        self._build_labs_tab()
        self._poll()

    def _build_queue_tab(self):
        card = Card(self.tab_queue, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        eyebrow(card.body, "TODAY'S OP QUEUE · URGENT FIRST").pack(anchor="w", pady=(0, 10))
        cols = ("token", "patient", "slot", "mobile", "urgency", "status")
        self.queue_tree = ttk.Treeview(card.body, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (70, 160, 110, 110, 90, 100)):
            self.queue_tree.heading(c, text=c.title())
            self.queue_tree.column(c, width=w, anchor="center")
        self.queue_tree.pack(fill="both", expand=True)

        btnrow = tk.Frame(card.body, bg=PAPER_RAISED)
        btnrow.pack(fill="x", pady=(10, 0))
        make_btn(btnrow, "Mark urgent", self._mark_urgent, "danger").pack(side="left", padx=(0, 8))
        make_btn(btnrow, "Mark completed", self._mark_completed, "primary").pack(side="left")

    def _build_presc_tab(self):
        card = Card(self.tab_presc, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        eyebrow(card.body, "WRITE PRESCRIPTION").pack(anchor="w", pady=(0, 10))

        self.presc_mobile = labeled_entry(card.body, "Patient mobile number", width=24)

        row = tk.Frame(card.body, bg=PAPER_RAISED)
        row.pack(fill="both", expand=True, pady=(6, 0))
        left = tk.Frame(row, bg=PAPER_RAISED)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))
        right = tk.Frame(row, bg=PAPER_RAISED)
        right.pack(side="left", fill="both", expand=True)

        self.medicine_assistant = MedicineAssistant(left)
        self.medicine_assistant.pack(fill="both", expand=True)

        self.dosage_entry = labeled_entry(right, "Dosage / instructions", width=24)
        make_btn(right, "Save prescription", self._save_prescription, "primary").pack(fill="x", pady=(14, 0))
        self.presc_status = tk.Label(right, text="", font=F_SMALL, fg=TEAL_DARK, bg=PAPER_RAISED, justify="left")
        self.presc_status.pack(anchor="w", pady=(10, 0))

    def _build_labs_tab(self):
        card = Card(self.tab_labs, padx=18, pady=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        eyebrow(card.body, "ADD LAB REPORT").pack(anchor="w", pady=(0, 10))
        self.labs_mobile = labeled_entry(card.body, "Patient mobile number", width=24)
        self.labs_title = labeled_entry(card.body, "Test / report title", width=24)
        self.labs_result = labeled_entry(card.body, "Result summary", width=24)
        make_btn(card.body, "Save lab report", self._save_lab, "primary").pack(fill="x", pady=(14, 0))
        self.labs_status = tk.Label(card.body, text="", font=F_SMALL, fg=TEAL_DARK, bg=PAPER_RAISED)
        self.labs_status.pack(anchor="w", pady=(8, 0))

    def on_show(self):
        self.app.refresh_from_disk()
        dept = self.app.session.get("dept", "")
        self.title_label.config(text=f"Dr. session · {self.app.session.get('name','')} · {dept}")
        self._reload_queue()

    def _poll(self):
        if self.winfo_ismapped():
            self.app.refresh_from_disk()
            self._reload_queue()
        self.after(REFRESH_MS, self._poll)

    def _reload_queue(self):
        dept = self.app.session.get("dept")
        for row in self.queue_tree.get_children():
            self.queue_tree.delete(row)
        today = today_str()
        rows = [a for a in self.app.data.get("appointments", [])
                if a.get("dept") == dept and a.get("date") == today]
        rows.sort(key=lambda a: (0 if a.get("urgency") == "urgent" else 1, a.get("slot", "")))
        for a in rows:
            self.queue_tree.insert("", "end", iid=a["id"],
                                    values=(a["token"], a["patient_name"], a["slot"],
                                            a["mobile"], a["urgency"], a["status"]))

    def _selected_appt_id(self):
        sel = self.queue_tree.selection()
        return sel[0] if sel else None

    def _mark_urgent(self):
        aid = self._selected_appt_id()
        if not aid:
            return
        for a in self.app.data.get("appointments", []):
            if a["id"] == aid:
                a["urgency"] = "urgent"
        self.app.persist()
        self._reload_queue()

    def _mark_completed(self):
        aid = self._selected_appt_id()
        if not aid:
            return
        for a in self.app.data.get("appointments", []):
            if a["id"] == aid:
                a["status"] = "completed"
        self.app.persist()
        self._reload_queue()

    def _save_prescription(self):
        mobile = "".join(ch for ch in self.presc_mobile.get() if ch.isdigit())
        medicine = self.medicine_assistant.get()
        dosage = self.dosage_entry.get().strip()
        if len(mobile) != 10 or not medicine:
            self.presc_status.config(text="Enter a valid mobile number and a medicine name.", fg=DANGER)
            return
        app = self.app
        app.refresh_from_disk()
        entry = {
            "date": today_str(),
            "doctor": app.session.get("name", ""),
            "medicine": medicine,
            "dosage": dosage or "As directed",
        }
        app.data.setdefault("prescriptions", {}).setdefault(mobile, []).append(entry)
        app.persist()
        self.presc_status.config(text=f"Saved: {medicine} for {mobile}.", fg=TEAL_DARK)
        self.medicine_assistant.clear()
        self.dosage_entry.delete(0, tk.END)

    def _save_lab(self):
        mobile = "".join(ch for ch in self.labs_mobile.get() if ch.isdigit())
        title = self.labs_title.get().strip()
        result = self.labs_result.get().strip()
        if len(mobile) != 10 or not title:
            self.labs_status.config(text="Enter a valid mobile number and a report title.", fg=DANGER)
            return
        app = self.app
        app.refresh_from_disk()
        entry = {"date": today_str(), "title": title, "result": result or "Pending"}
        app.data.setdefault("lab_reports", {}).setdefault(mobile, []).append(entry)
        app.persist()
        self.labs_status.config(text=f"Saved lab report '{title}' for {mobile}.", fg=TEAL_DARK)
        self.labs_title.delete(0, tk.END)
        self.labs_result.delete(0, tk.END)


# ============================================================================
#  ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    app = IKretApp()
    app.mainloop()
