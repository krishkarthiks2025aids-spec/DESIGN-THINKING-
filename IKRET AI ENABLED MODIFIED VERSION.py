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
1. Every screen now has a colourful, gradient/bokeh background — the splash
   screens use a vivid indigo/violet/rose/amber/sky hero gradient
   (add_tech_hero_background) and the working dashboards use a soft
   mint/peach/blush/lilac pastel wash (add_branch_background), so the whole
   app feels bright and alive instead of flat paper.
2. Patients can now upload (or update) a real photo of themselves — at
   verification and again at booking time — which is stored locally under
   ~/.ikret_desktop/photos/. If a patient skips this, a colourful generated
   "initials avatar" is used instead so there's always a face on the ticket.
3. Booking a slot now produces a movie-ticket-style "I-KRET Ticket" pass
   (see TicketCard) showing the patient's photo, appointment details, a
   scannable QR code, and the Booking ID underneath — just like a cinema
   e-ticket. It pops up automatically after booking and can be reopened any
   time from "My Appointments" or the OP-counter Scan/Verify screen.
4. A "Medicine Assistant" sits next to the doctor's prescription field.
   As the doctor types, it live-filters MEDICINES by the letters typed
   and lists matches; clicking a suggestion drops it straight into the
   field.
5. A "Health Assistant" tab on the patient dashboard asks the patient's
   preferred language and their area, then live-suggests the nearest
   government hospital (name + address + distance), refreshing itself
   every few seconds the way a live locator would.
6. The patient dashboard's own text (tab names, headings, buttons) is
   re-rendered in the patient's chosen language using the existing
   TRANSLATIONS / tr() language packs.
7. An "AI Symptom Assistant" now sits at the top of the Book Appointment
   tab. The patient types a plain description of how they're feeling (e.g.
   "I have fever and a running nose since yesterday") and, as they type,
   the assistant matches it against a built-in symptom database (fever,
   cold, cough, stomach ache, headache, joint pain, chest pain, and more —
   see SYMPTOM_DB), shows the likely condition(s) with their typical
   symptoms, and automatically fills in the Department dropdown for them.
   If the description matches something urgent (e.g. chest pain,
   breathlessness, severe bleeding), the booking is auto-flagged "urgent"
   so it jumps to the top of the doctor's OP queue, which now also shows a
   "Reason" column with the AI-detected condition(s).
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import json
import os
import random
import datetime
import uuid
import hashlib
import shutil

# QR code support -- optional. If 'qrcode' isn't installed, the app still
# runs fine; QR panels just show a note telling you what to pip install.
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    import psycopg2 as psycopg
    PG_AVAILABLE = True
except ImportError:
    PG_AVAILABLE = False

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

import threading

# Voice assistant support -- optional. If these packages aren't installed,
# the app still runs fine: the assistant just falls back to typed text in
# place of speech, and silently skips spoken replies.
#   pip install SpeechRecognition pyaudio pyttsx3
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction import DictVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

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

# ---- extra vivid accents (used for tiles, tags, buttons, gradients) -------
ROSE         = "#E14D7A"
ROSE_DARK    = "#A6335A"
ROSE_PALE    = "#FBD8E4"
SKY          = "#2E8FE0"
SKY_DARK     = "#1F63A3"
SKY_PALE     = "#D6E9FB"
VIOLET       = "#8B5CF6"
VIOLET_DARK  = "#5B34AE"
VIOLET_PALE  = "#E9D8FD"

# ---- movie-ticket theme (used by the booking/QR "ticket" card) ------------
TICKET_BG    = "#15111F"
TICKET_BG2   = "#241B3A"
TICKET_LINE  = "#3B2E5C"
TICKET_TEXT  = "#F5F1FF"
TICKET_SUB   = "#B3A7D6"
TICKET_ACCENT = VIOLET

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

# ============================================================================
#  SYMPTOM ASSISTANT DATA  —  illness -> keywords / department / urgency
#  Used by the "AI Symptom Assistant" (see SymptomAssistant class below) to
#  read a patient's free-text description of how they're feeling and
#  automatically fill in the Department (and flag urgency) on the booking
#  form, the same way a triage nurse would listen and route a patient.
# ============================================================================
SYMPTOM_DB = {
    "Fever": {
        "keywords": ["fever", "high temperature", "temperature", "chills", "shivering", "hot body"],
        "symptoms": ["raised body temperature", "chills", "sweating", "weakness"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Common Cold": {
        "keywords": ["cold", "runny nose", "blocked nose", "sneezing", "nasal congestion", "stuffy nose"],
        "symptoms": ["runny/blocked nose", "sneezing", "mild headache", "watery eyes"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Cough": {
        "keywords": ["cough", "coughing", "dry cough", "throat irritation"],
        "symptoms": ["dry or wet cough", "throat irritation", "mild chest discomfort"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Sore Throat": {
        "keywords": ["sore throat", "throat pain", "throat ache", "difficulty swallowing"],
        "symptoms": ["throat pain", "scratchy throat", "pain while swallowing"],
        "dept": "ENT", "urgency": "normal",
    },
    "Stomach Ache": {
        "keywords": ["stomach ache", "stomach pain", "abdominal pain", "tummy pain", "indigestion",
                     "acidity", "gas trouble", "bloating"],
        "symptoms": ["abdominal pain", "bloating", "acidity/indigestion"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Vomiting": {
        "keywords": ["vomiting", "throwing up", "nausea", "feeling sick"],
        "symptoms": ["nausea", "repeated vomiting", "loss of appetite"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Diarrhea": {
        "keywords": ["diarrhea", "diarrhoea", "loose motions", "loose stools", "watery stools"],
        "symptoms": ["loose/watery stools", "stomach cramps", "dehydration"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Headache": {
        "keywords": ["headache", "migraine", "head pain", "head ache"],
        "symptoms": ["throbbing head pain", "sensitivity to light", "nausea"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Body Ache / Weakness": {
        "keywords": ["body ache", "body pain", "weakness", "tiredness", "fatigue", "no energy"],
        "symptoms": ["muscle/body pain", "fatigue", "general weakness"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Skin Rash / Allergy": {
        "keywords": ["rash", "skin allergy", "itching", "itchy skin", "hives", "skin irritation"],
        "symptoms": ["red/itchy patches", "swelling", "irritation"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Ear Pain": {
        "keywords": ["ear pain", "ear ache", "ear infection", "hearing problem", "ear discharge"],
        "symptoms": ["ear pain", "reduced hearing", "ear discharge"],
        "dept": "ENT", "urgency": "normal",
    },
    "Nose / Sinus Problem": {
        "keywords": ["sinus", "sinusitis", "nose block", "smell loss"],
        "symptoms": ["facial pressure", "blocked nose", "reduced smell"],
        "dept": "ENT", "urgency": "normal",
    },
    "Joint / Back Pain": {
        "keywords": ["joint pain", "back pain", "knee pain", "shoulder pain", "arthritis", "bone pain"],
        "symptoms": ["joint stiffness", "swelling", "pain on movement"],
        "dept": "Orthopaedics", "urgency": "normal",
    },
    "Injury / Fracture": {
        "keywords": ["fracture", "sprain", "fell down", "injury", "swelling after fall", "accident"],
        "symptoms": ["swelling", "difficulty moving limb", "bruising"],
        "dept": "Orthopaedics", "urgency": "urgent",
    },
    "Pregnancy Checkup": {
        "keywords": ["pregnant", "pregnancy", "antenatal", "expecting baby"],
        "symptoms": ["routine antenatal checkup"],
        "dept": "Gynaecology", "urgency": "normal",
    },
    "Menstrual Problem": {
        "keywords": ["periods", "menstrual", "menstruation", "irregular periods"],
        "symptoms": ["irregular/painful periods", "heavy bleeding"],
        "dept": "Gynaecology", "urgency": "normal",
    },
    "Child Fever / Vaccination": {
        "keywords": ["my child", "my baby", "my son", "my daughter", "kid fever", "vaccination", "immunisation"],
        "symptoms": ["child fever", "vaccination due", "growth concerns"],
        "dept": "Paediatrics", "urgency": "normal",
    },
    "High Blood Pressure": {
        "keywords": ["bp", "blood pressure", "hypertension"],
        "symptoms": ["headache", "dizziness", "elevated BP reading"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Diabetes Checkup": {
        "keywords": ["diabetes", "sugar level", "blood sugar"],
        "symptoms": ["excess thirst", "frequent urination", "fatigue"],
        "dept": "General Medicine", "urgency": "normal",
    },
    "Chest Pain": {
        "keywords": ["chest pain", "chest tightness", "chest discomfort"],
        "symptoms": ["chest pain/tightness", "shortness of breath", "sweating"],
        "dept": "General Medicine", "urgency": "urgent",
    },
    "Breathlessness": {
        "keywords": ["breathless", "difficulty breathing", "shortness of breath", "cant breathe", "can't breathe"],
        "symptoms": ["shortness of breath", "wheezing", "chest tightness"],
        "dept": "General Medicine", "urgency": "urgent",
    },
    "Severe Bleeding": {
        "keywords": ["heavy bleeding", "severe bleeding", "blood loss", "wound bleeding"],
        "symptoms": ["uncontrolled bleeding", "dizziness", "pale skin"],
        "dept": "General Medicine", "urgency": "urgent",
    },
}


def analyze_symptoms(text):
    """Very small, deterministic keyword-matching 'AI' (no external calls,
    works fully offline). Scans the patient's free-text description against
    SYMPTOM_DB and returns a list of (illness_name, score, matched_keywords,
    info) tuples sorted by best match first."""
    if not text:
        return []
    text_low = text.lower()
    scored = []
    for name, info in SYMPTOM_DB.items():
        matched = [kw for kw in info["keywords"] if kw in text_low]
        if matched:
            scored.append((name, len(matched), matched, info))
    scored.sort(key=lambda t: -t[1])
    return scored


def suggest_department_and_urgency(text):
    """Roll the matched illnesses up into a single suggested department and
    an overall urgency flag ('urgent' wins over 'normal'), the same way a
    triage desk would decide where to send a patient."""
    scored = analyze_symptoms(text)
    if not scored:
        return None, "normal", []
    dept_votes = {}
    urgency = "normal"
    for name, score, matched, info in scored:
        dept_votes[info["dept"]] = dept_votes.get(info["dept"], 0) + score
        if info["urgency"] == "urgent":
            urgency = "urgent"
    best_dept = max(dept_votes, key=dept_votes.get)
    names = [n for n, _, _, _ in scored]
    return best_dept, urgency, names


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
PHOTOS_DIR = os.path.join(APP_DIR, "photos")
PHOTO_FILETYPES = [("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"), ("All files", "*.*")]


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
#  PATIENT PHOTO  —  upload a real photo, or fall back to a generated,
#  colourful initials avatar, so every booking ticket always has a face on it
# ============================================================================
def ensure_photos_dir():
    os.makedirs(PHOTOS_DIR, exist_ok=True)


def save_patient_photo(mobile, src_path):
    """Copy an uploaded photo into I-KRET's own storage so it survives even
    if the user's original file is later moved or deleted. Returns the new,
    permanent path (or None if the copy failed)."""
    if not src_path or not os.path.exists(src_path):
        return None
    ensure_photos_dir()
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"):
        ext = ".jpg"
    dest = os.path.join(PHOTOS_DIR, f"{mobile}{ext}")
    try:
        shutil.copyfile(src_path, dest)
        return dest
    except Exception:
        return None


_AVATAR_GRADIENTS = [
    ((233, 77, 122), (139, 92, 246)),   # rose -> violet
    ((46, 143, 224), (14, 107, 92)),    # sky -> teal
    ((228, 162, 52), (225, 77, 122)),   # amber -> rose
    ((139, 92, 246), (46, 143, 224)),   # violet -> sky
    ((14, 107, 92), (228, 162, 52)),    # teal -> amber
]


def make_initials_avatar(name, size=140):
    """Generate a bright, colourful gradient avatar carrying the patient's
    initials, used whenever no real photo has been uploaded yet."""
    name = (name or "Patient").strip()
    parts = [p for p in name.split() if p]
    initials = ((parts[0][0] if parts else "P") + (parts[1][0] if len(parts) > 1 else "")).upper()
    idx = sum(ord(c) for c in name) % len(_AVATAR_GRADIENTS)
    c1, c2 = _AVATAR_GRADIENTS[idx]

    img = Image.new("RGB", (size, size), c1)
    px = img.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img)
    font = None
    for candidate in ("arialbd.ttf", "DejaVuSans-Bold.ttf", "Verdana.ttf"):
        try:
            font = ImageFont.truetype(candidate, size // 2)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    try:
        bbox = draw.textbbox((0, 0), initials, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
                   initials, fill="white", font=font)
    except Exception:
        draw.text((size * 0.25, size * 0.3), initials, fill="white", font=font)
    return img


def load_patient_photo_image(photo_path, name, size=140):
    """Load an uploaded patient photo, centre-cropped to a square, or fall
    back to a generated colourful initials avatar. Always returns a PIL
    Image ready to be wrapped in ImageTk.PhotoImage by the caller."""
    if photo_path and os.path.exists(photo_path):
        try:
            img = Image.open(photo_path).convert("RGB")
            w, h = img.size
            side = min(w, h)
            img = img.crop(((w - side) // 2, (h - side) // 2,
                             (w - side) // 2 + side, (h - side) // 2 + side))
            img = img.resize((size, size), Image.LANCZOS)
            return img
        except Exception:
            pass
    return make_initials_avatar(name, size)


def choose_photo_file(parent):
    """Open a file picker for a patient photo. Returns a path or None."""
    return filedialog.askopenfilename(parent=parent, title="Choose patient photo",
                                       filetypes=PHOTO_FILETYPES) or None


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
    """A soft, colourful pastel wash (mint -> peach -> blush -> lilac) with
    gentle floating bokeh circles behind a screen's content. Replaces the old
    flat-paper watermark so every dashboard, not just the splash screens,
    carries real colour. Called from every screen's __init__."""
    STOPS = [(214, 240, 231), (255, 241, 214), (255, 224, 222), (231, 221, 250)]
    canvas = tk.Canvas(frame, highlightthickness=0, bd=0)
    canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
    canvas.lower("all")  # keep it behind whatever gets packed/placed on top

    def lerp(a, b, t):
        return int(a + (b - a) * t)

    def color_at(t):
        n = len(STOPS) - 1
        seg = min(int(t * n), n - 1)
        local_t = (t * n) - seg
        c0, c1 = STOPS[seg], STOPS[seg + 1]
        return tuple(lerp(c0[k], c1[k], local_t) for k in range(3))

    bokeh_rng = random.Random(20260101)  # stable so bubbles don't jump on resize
    bokeh_spots = [(bokeh_rng.random(), bokeh_rng.random(), bokeh_rng.randint(28, 85),
                    bokeh_rng.choice([TEAL_PALE, AMBER_PALE, ROSE_PALE, VIOLET_PALE, SKY_PALE]))
                   for _ in range(14)]

    def redraw(event=None):
        canvas.delete("all")
        w = frame.winfo_width() or 980
        h = frame.winfo_height() or 680
        canvas.configure(width=w, height=h)
        steps = 100
        for i in range(steps):
            t = i / steps
            r, g, b = color_at(t)
            color = f"#{r:02x}{g:02x}{b:02x}"
            y0, y1 = int(h * i / steps), int(h * (i + 1) / steps) + 1
            canvas.create_rectangle(0, y0, w, y1, fill=color, outline=color)
        for fx, fy, rad, fillc in bokeh_spots:
            cx, cy = int(fx * w), int(fy * h)
            canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                fill=fillc, outline="", stipple="gray25")
        canvas.create_text(w - 14, h - 12, anchor="se", text=subtitle, font=F_SMALL, fill=INK_SOFT)
        canvas.lower("all")

    frame.bind("<Configure>", redraw)
    frame.after(50, redraw)
    return canvas


def add_tech_hero_background(frame, corner_text="I-KRET · SMART OP BOOKING"):
    """A deep indigo-to-violet gradient with soft glow rings, matching the
    'Doctor Appointment Booking App' marketing banner (dark purple backdrop,
    phone mockups glowing softly in front of it). Used on the home / role
    picker, login, and scan/verify screens, so the app opens on a bold
    splash before settling into the calmer paper-registry look used in the
    working dashboards."""
    TOP = (24, 15, 56)       # near-black indigo
    BOTTOM = (54, 34, 110)   # deep violet-purple
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

        # soft halo rings, standing in for the glowing phone-mockup motif
        cx, cy = int(w * 0.5), int(h * 0.66)
        for rad, ring_color, ring_w in [(190, "#3B2E7A", 10), (140, "#4B3B96", 8), (95, "#7A5FD1", 6)]:
            canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                outline=ring_color, width=ring_w)
        canvas.create_oval(cx - 34, cy - 34, cx + 34, cy + 34, fill="#B79CFF", outline="")

        # extra floating colour glows (rose / amber / sky) so the splash
        # screens feel bright and multicoloured, not just monochrome violet
        for gx, gy, rad, col in [
            (int(w * 0.14), int(h * 0.22), 60, ROSE),
            (int(w * 0.88), int(h * 0.18), 46, AMBER),
            (int(w * 0.90), int(h * 0.78), 55, SKY),
            (int(w * 0.10), int(h * 0.82), 40, "#3DD6B4"),
        ]:
            canvas.create_oval(gx - rad, gy - rad, gx + rad, gy + rad,
                                outline=col, width=3, stipple="gray50")

        # faint circuit-dot texture for a 'tech' feel
        for gx in range(0, w, 52):
            for gy in range(0, h, 52):
                canvas.create_oval(gx, gy, gx + 2, gy + 2, fill="#352A70", outline="")

        canvas.create_text(w - 16, 16, anchor="ne", text=corner_text,
                            font=F_EYEBROW, fill="#CBB8FF")
        canvas.lower("all")

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
        "rose":    (ROSE, WHITE, ROSE_DARK),
        "sky":     (SKY, WHITE, SKY_DARK),
        "violet":  (VIOLET, WHITE, VIOLET_DARK),
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


class TicketCard(tk.Frame):
    """A movie-ticket-style booking pass: I-KRET branding, the patient's own
    photo (or a colourful generated avatar), appointment details, a
    scannable QR code, and the Booking ID underneath it — mirroring the
    familiar 'District by Zomato' style ticket the app is modelled on."""
    def __init__(self, parent, appt, photo_path=None, width=300):
        super().__init__(parent, bg=TICKET_BG, highlightbackground=TICKET_ACCENT,
                          highlightthickness=2, bd=0, width=width)

        head = tk.Frame(self, bg=TICKET_BG2, height=54)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Label(head, text="I-KRET", font=("Segoe UI", 16, "bold"),
                 bg=TICKET_BG2, fg=TICKET_TEXT).pack(pady=(8, 0))
        tk.Label(head, text="GOVT. OP APPOINTMENT PASS", font=F_EYEBROW,
                 bg=TICKET_BG2, fg=TICKET_ACCENT).pack()

        body = tk.Frame(self, bg=TICKET_BG)
        body.pack(fill="x", padx=18, pady=(16, 4))

        top = tk.Frame(body, bg=TICKET_BG)
        top.pack(fill="x")
        pil_img = load_patient_photo_image(photo_path, appt.get("patient_name", ""), size=72)
        self._photo_ref = ImageTk.PhotoImage(pil_img)
        tk.Label(top, image=self._photo_ref, bg=TICKET_BG,
                 highlightbackground=TICKET_ACCENT, highlightthickness=2).pack(side="left")

        info = tk.Frame(top, bg=TICKET_BG)
        info.pack(side="left", padx=(14, 0), fill="x", expand=True)
        tk.Label(info, text=appt.get("patient_name", "Patient"), font=("Segoe UI", 13, "bold"),
                 bg=TICKET_BG, fg=TICKET_TEXT, anchor="w").pack(fill="x")
        tk.Label(info, text=f"{appt.get('dept', '')}", font=F_SMALL,
                 bg=TICKET_BG, fg=TICKET_SUB, anchor="w").pack(fill="x", pady=(3, 0))
        tk.Label(info, text=f"{appt.get('date', '')}  ·  {appt.get('slot', '')}", font=F_SMALL,
                 bg=TICKET_BG, fg=TICKET_SUB, anchor="w").pack(fill="x")

        tk.Frame(body, bg=TICKET_LINE, height=1).pack(fill="x", pady=(14, 12))

        tk.Label(body, text="Scan this QR code at the OP counter", font=F_SMALL,
                 bg=TICKET_BG, fg=TICKET_SUB).pack()

        qr_photo = make_qr_photo(appt.get("qr") or appointment_qr_payload(appt),
                                  box_size=6, border=2)
        qr_wrap = tk.Frame(body, bg=WHITE, padx=10, pady=10)
        qr_wrap.pack(pady=(10, 10))
        if qr_photo is not None:
            self._qr_ref = qr_photo
            tk.Label(qr_wrap, image=qr_photo, bg=WHITE).pack()
        else:
            tk.Label(qr_wrap, text="Install 'qrcode' + 'pillow'\n(pip install qrcode pillow)\nto render a QR here.",
                     bg=WHITE, fg=INK_SOFT, font=F_SMALL, justify="center").pack()

        tk.Label(body, text=appt.get("doctor", ""), font=("Segoe UI", 11, "bold"),
                 bg=TICKET_BG, fg=TICKET_TEXT).pack()
        tk.Label(body, text=f"Token {appt.get('token', '')}", font=F_SMALL,
                 bg=TICKET_BG, fg=TICKET_SUB).pack(pady=(2, 4))

        dash = tk.Canvas(self, height=8, bg=TICKET_BG, highlightthickness=0)
        dash.pack(fill="x", padx=8, pady=(6, 6))

        def draw_dash(event=None):
            dash.delete("all")
            w = dash.winfo_width() or width
            x = 0
            while x < w:
                dash.create_line(x, 4, x + 8, 4, fill=TICKET_SUB, width=2)
                x += 15
        dash.bind("<Configure>", draw_dash)
        dash.after(30, draw_dash)

        foot = tk.Frame(self, bg=TICKET_BG)
        foot.pack(fill="x", padx=18, pady=(0, 18))
        tk.Label(foot, text=f"Booking ID: {appt.get('id', '')}", font=F_MONO_B,
                 bg=TICKET_BG, fg=TICKET_TEXT).pack(pady=(2, 2))
        tk.Label(foot, text="#SeeYouAtTheOPCounter", font=F_SMALL,
                 bg=TICKET_BG, fg=TICKET_ACCENT).pack()


def open_ticket_window(root, appt, photo_path=None):
    """Pop the full TicketCard up in its own small window — used right after
    a booking is confirmed, and whenever a patient wants to re-view a
    previous appointment's pass."""
    win = tk.Toplevel(root)
    win.title(f"I-KRET Ticket · Token {appt.get('token', '')}")
    win.configure(bg=TICKET_BG)
    win.resizable(False, False)
    ticket = TicketCard(win, appt, photo_path)
    ticket.pack(padx=16, pady=16)
    win.transient(root)
    return win


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
#  SYMPTOM ASSISTANT  —  patient describes their problem in plain words and
#  the AI assistant live-matches it against SYMPTOM_DB, then auto-fills the
#  booking form's Department (and flags urgency) for them.
# ============================================================================
class SymptomAssistant(tk.Frame):
    """A free-text box + 'Analyze with AI' button. As the patient types a
    description of how they're feeling (e.g. 'I have fever and cold since
    2 days'), this widget matches it against SYMPTOM_DB, shows the likely
    condition(s) with their typical symptoms, and calls back with a
    suggested department + urgency so the booking form can auto-fill
    itself -- no need for the patient to know which department to pick."""
    def __init__(self, parent, on_result=None):
        super().__init__(parent, bg=PAPER_RAISED)
        self.on_result = on_result
        self._after_id = None
        self.last_dept = None
        self.last_urgency = "normal"
        self.last_conditions = []

        eyebrow(self, "AI SYMPTOM ASSISTANT · AUTO-FILLS YOUR BOOKING").pack(anchor="w", pady=(0, 4))
        tk.Label(self, text="Describe how you're feeling, in your own words",
                 font=F_SMALL, fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(4, 3))
        tk.Label(self, text='e.g. "I have fever and a running nose since yesterday"',
                 font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED).pack(anchor="w", pady=(0, 4))

        self.text = tk.Text(self, height=3, font=F_BODY, wrap="word", relief="solid", bd=1,
                             highlightthickness=1, highlightbackground=LINE, highlightcolor=TEAL)
        self.text.pack(fill="x")
        self.text.bind("<KeyRelease>", self._on_key)

        make_btn(self, "Analyze with AI", self._analyze_now, "amber").pack(anchor="w", pady=(8, 4))

        self.result_wrap = tk.Frame(self, bg=PAPER_RAISED)
        self.result_wrap.pack(fill="x", pady=(4, 0))
        self.status = tk.Label(
            self, text="Type your symptoms above — I'll suggest the right department automatically.",
            font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED, wraplength=380, justify="left")
        self.status.pack(anchor="w", pady=(6, 0))

    def _on_key(self, event=None):
        # Debounce: wait for a short pause in typing before auto-analyzing,
        # so the AI doesn't re-run on every single keystroke.
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(700, self._analyze_now)

    def _analyze_now(self):
        text = self.text.get("1.0", "end").strip()
        for w in self.result_wrap.winfo_children():
            w.destroy()

        if not text:
            self.status.config(
                text="Type your symptoms above — I'll suggest the right department automatically.",
                fg=INK_SOFT)
            self.last_dept, self.last_urgency, self.last_conditions = None, "normal", []
            if self.on_result:
                self.on_result(None, "normal", [], "")
            return

        scored = analyze_symptoms(text)
        if not scored:
            self.status.config(
                text="Couldn't match a specific condition — General Medicine is suggested by default.",
                fg=INK_SOFT)
            self.last_dept, self.last_urgency, self.last_conditions = "General Medicine", "normal", []
            if self.on_result:
                self.on_result("General Medicine", "normal", [], text)
            return

        best_dept, urgency, names = suggest_department_and_urgency(text)
        self.last_dept, self.last_urgency, self.last_conditions = best_dept, urgency, names

        for name, score, matched, info in scored[:4]:
            card = tk.Frame(self.result_wrap, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
            card.pack(fill="x", pady=3)
            inner = tk.Frame(card, bg=WHITE)
            inner.pack(fill="x", padx=10, pady=6)
            head_row = tk.Frame(inner, bg=WHITE)
            head_row.pack(fill="x")
            tk.Label(head_row, text=name, font=F_HEAD2, bg=WHITE, fg=INK).pack(side="left")
            if info["urgency"] == "urgent":
                tag_label(head_row, "URGENT", "urgent").pack(side="right")
            else:
                tag_label(head_row, info["dept"], "normal").pack(side="right")
            tk.Label(inner, text="Typical symptoms: " + ", ".join(info["symptoms"]), font=F_SMALL,
                     bg=WHITE, fg=INK_SOFT, wraplength=360, justify="left").pack(anchor="w", pady=(3, 0))

        msg = f"Suggested department: {best_dept}"
        if urgency == "urgent":
            msg += "  ·  This looks urgent — please mention this at the OP counter."
        msg += f"\nDetected: {', '.join(names)}"
        self.status.config(text=msg, fg=(DANGER if urgency == "urgent" else TEAL_DARK))

        if self.on_result:
            self.on_result(best_dept, urgency, names, text)

    def get_description(self):
        return self.text.get("1.0", "end").strip()

    def clear(self):
        self.text.delete("1.0", "end")
        for w in self.result_wrap.winfo_children():
            w.destroy()
        self.status.config(text="Type your symptoms above — I'll suggest the right department automatically.",
                            fg=INK_SOFT)
        self.last_dept, self.last_urgency, self.last_conditions = None, "normal", []


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
#  SPEAKER  —  tiny text-to-speech wrapper, used by the voice assistant
#  Runs pyttsx3 on a background thread so it never freezes the Tkinter UI.
#  If pyttsx3 isn't installed, say() just does nothing (assistant still
#  replies with on-screen text, so the app is fully usable either way).
# ============================================================================
class Speaker:
    def __init__(self):
        self.engine = None
        if TTS_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 178)
            except Exception:
                self.engine = None
        self._lock = threading.Lock()

    def say(self, text):
        if not text or self.engine is None:
            return

        def _run():
            with self._lock:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception:
                    pass

        threading.Thread(target=_run, daemon=True).start()


SPEAKER = Speaker()


# ============================================================================
#  VOICE ASSISTANT  —  a floating helper present on EVERY screen of the app
#  (role selection, login, patient dashboard, doctor dashboard, scan/verify).
#  Click the round mic bubble in the bottom-right corner to open it. Type a
#  request, or tap "Listen" to speak it (needs: pip install SpeechRecognition
#  pyaudio) -- either way the assistant carries the action out on screen for
#  you: booking an appointment (auto-filling the AI symptom box AND
#  confirming the booking, no extra taps), opening a tab, finding a nearby
#  hospital, logging out, or answering a general question about I-KRET.
# ============================================================================
class VoiceAssistant(tk.Frame):
    COLLAPSED = 60
    EXPANDED_W = 360
    EXPANDED_H = 440

    def __init__(self, app):
        super().__init__(app, bg=PAPER, highlightthickness=0, bd=0)
        self.app = app
        self.expanded = False
        self._greeted = False

        # ---- collapsed bubble (always visible) ----
        self.bubble = tk.Label(self, text="🎙", font=("Segoe UI", 22), bg=AMBER, fg=INK,
                                cursor="hand2", highlightbackground=AMBER_DARK, highlightthickness=2)
        self.bubble.pack(fill="both", expand=True)
        self.bubble.bind("<Button-1>", lambda e: self.toggle())

        # ---- expanded chat panel (built now, shown only when opened) ----
        self.panel = tk.Frame(self, bg=PAPER_RAISED, highlightbackground=TEAL, highlightthickness=1)

        head = tk.Frame(self.panel, bg=TEAL, height=42)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Label(head, text="🎙  I-KRET Assistant", font=F_HEAD2, bg=TEAL, fg=WHITE).pack(side="left", padx=10)
        close_btn = tk.Label(head, text="✕", font=F_HEAD2, bg=TEAL, fg=WHITE, cursor="hand2")
        close_btn.pack(side="right", padx=12)
        close_btn.bind("<Button-1>", lambda e: self.toggle())

        self.chat = ScrolledText(self.panel, height=14, font=F_SMALL, wrap="word",
                                  bg=WHITE, fg=INK, relief="flat", state="disabled", padx=8, pady=6)
        self.chat.pack(fill="both", expand=True, padx=8, pady=8)

        self.hint = tk.Label(self.panel,
                              text="Try: \"I have fever, book an appointment\" · \"show my appointments\" · \"log out\"",
                              font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED, wraplength=330, justify="left")
        self.hint.pack(fill="x", padx=8)

        entry_row = tk.Frame(self.panel, bg=PAPER_RAISED)
        entry_row.pack(fill="x", padx=8, pady=8)
        self.entry = tk.Entry(entry_row, font=F_BODY, relief="solid", bd=1,
                               highlightthickness=1, highlightbackground=LINE, highlightcolor=TEAL)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", self._send)
        make_btn(entry_row, "🎤 Listen", self._listen_once, "amber").pack(side="left", padx=(6, 0))
        make_btn(entry_row, "Send", self._send, "primary").pack(side="left", padx=(6, 0))

        self.place(relx=1.0, rely=1.0, x=-22, y=-22, anchor="se",
                   width=self.COLLAPSED, height=self.COLLAPSED)

    # ---- open / close ---------------------------------------------------
    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.bubble.pack_forget()
            self.panel.pack(fill="both", expand=True)
            self.place_configure(width=self.EXPANDED_W, height=self.EXPANDED_H)
            if not self._greeted:
                self._reply("Hi, I'm your I-KRET Assistant. I can book an appointment for you "
                             "straight from your symptoms, open any tab, find a nearby government "
                             "hospital, or log you out. What do you need?")
                self._greeted = True
            self.entry.focus_set()
        else:
            self.panel.pack_forget()
            self.bubble.pack(fill="both", expand=True)
            self.place_configure(width=self.COLLAPSED, height=self.COLLAPSED)

    def raise_to_top(self):
        self.lift()

    # ---- input handling ---------------------------------------------------
    def _send(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self._log("You", text)
        self._handle_command(text)

    def _listen_once(self):
        if not SR_AVAILABLE:
            self._reply("Voice input needs two extra packages -- run "
                         "'pip install SpeechRecognition pyaudio' and restart the app. "
                         "You can type your request here in the meantime.", speak=False)
            return
        threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                self.after(0, lambda: self._log("Assistant", "Listening..."))
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=8)
            heard = recognizer.recognize_google(audio)
        except Exception:
            self.after(0, lambda: self._reply(
                "Sorry, I couldn't hear that clearly. Please try again, or type your request."))
            return
        self.after(0, lambda: self._on_heard(heard))

    def _on_heard(self, text):
        self._log("You (voice)", text)
        self._handle_command(text)

    # ---- chat log -----------------------------------------------------
    def _log(self, who, text):
        self.chat.config(state="normal")
        self.chat.insert("end", f"{who}: {text}\n\n")
        self.chat.see("end")
        self.chat.config(state="disabled")

    def _reply(self, text, speak=True):
        self._log("Assistant", text)
        if speak:
            SPEAKER.say(text)

    # ---- intent engine ---------------------------------------------------
    def _handle_command(self, text):
        low = text.lower().strip()

        if any(p in low for p in ("log out", "logout", "sign out")):
            self.app.sign_out()
            self._reply("You're logged out. See you again soon.")
            return

        if any(p in low for p in ("patient login", "i am a patient", "i'm a patient",
                                   "continue as patient", "book as patient")):
            self.app.show("PatientLoginScreen")
            self._reply("Opening patient login.")
            return

        if any(p in low for p in ("doctor login", "i am a doctor", "i'm a doctor", "continue as doctor")):
            self.app.show("DoctorLoginScreen")
            self._reply("Opening doctor login.")
            return

        if "scan" in low or "verify a booking" in low or "verify ticket" in low:
            self.app.show("ScanScreen")
            self._reply("Opening the scan and verify screen.")
            return

        role = self.app.session.get("role")

        if role == "patient":
            pd = self.app.frames["PatientDashboard"]

            if any(p in low for p in ("my appointment", "show appointment", "appointments")):
                self.app.show("PatientDashboard")
                pd.notebook.select(pd.tab_appts)
                self._reply("Here are your appointments.")
                return

            if "prescription" in low:
                self.app.show("PatientDashboard")
                pd.notebook.select(pd.tab_presc)
                self._reply("Here are your prescriptions.")
                return

            if any(p in low for p in ("lab report", "lab test", "lab result")):
                self.app.show("PatientDashboard")
                pd.notebook.select(pd.tab_labs)
                self._reply("Here are your lab reports.")
                return

            if any(p in low for p in ("nearest hospital", "nearby hospital", "find hospital",
                                       "government hospital", "health assistant")):
                self.app.show("PatientDashboard")
                pd.notebook.select(pd.tab_assist)
                area = self._extract_after(low, ("in ", "near ", "at "))
                if area:
                    pd.assistant.loc_entry.delete(0, tk.END)
                    pd.assistant.loc_entry.insert(0, area.title())
                    pd.assistant._find_hospitals()
                    self._reply(f"Searching government hospitals near {area.title()}.")
                else:
                    self._reply("Sure -- which area or city should I search near?")
                return

            book_triggers = ("book appointment", "book an appointment", "book a slot",
                              "need an appointment", "i have ", "i am feeling", "i'm feeling",
                              "feeling ", "symptom", "not feeling well", "unwell")
            if any(p in low for p in book_triggers):
                self.app.show("PatientDashboard")
                pd.notebook.select(pd.tab_book)
                symptom_text = self._extract_symptom_text(text)
                self._book_via_voice(pd, symptom_text)
                return

            if any(p in low for p in ("help", "what can you do")):
                self._reply("I can book an appointment straight from your symptoms, show your "
                             "appointments, prescriptions or lab reports, find the nearest "
                             "government hospital, or log you out. For example, say "
                             "'I have fever and cold, book an appointment'.")
                return
        else:
            if any(p in low for p in ("book appointment", "book an appointment", "i have ",
                                       "feeling", "symptom")):
                self._reply("Please log in as a patient first, then tell me your symptoms and "
                             "I'll book the appointment for you.")
                return

        faq = self._faq_answer(low)
        if faq:
            self._reply(faq)
            return

        self._reply("I didn't quite catch an action for that. Try things like "
                     "'book an appointment, I have a headache', 'show my appointments', "
                     "or 'find hospital near <your area>'.")

    def _extract_symptom_text(self, text):
        low = text.lower()
        leads = ("book an appointment for", "book appointment for", "book a slot for",
                 "i need an appointment for", "book an appointment", "book appointment",
                 "book a slot", "for ")
        for lead in leads:
            if lead in low:
                idx = low.find(lead)
                remainder = text[idx + len(lead):].strip(" ,.:-")
                if remainder:
                    return remainder
        return text.strip()

    def _extract_after(self, low, markers):
        for m in markers:
            if m in low:
                return low.split(m, 1)[1].strip(" ?.")
        return None

    def _faq_answer(self, low):
        faqs = [
            (("what is i-kret", "about ikret", "about i-kret"),
             "I-KRET is a government OP appointment and records system that lets you book "
             "hospital appointments, view prescriptions and lab reports, and find nearby "
             "government hospitals."),
            (("how do i book", "how to book"),
             "Just tell me your symptoms, like 'I have fever and cold', and I'll pick the "
             "right department and book your slot for you automatically."),
            (("view ticket", "my ticket", "view my ticket", "view the ticket"),
             "Open 'My Appointments', select a booking, then tap 'View full ticket' to see "
             "your photo, QR code and booking ID."),
            (("who are you", "your name"),
             "I'm the I-KRET Assistant, here to help you book appointments and find your way "
             "around the app by voice or text."),
        ]
        for keys, ans in faqs:
            if any(k in low for k in keys):
                return ans
        return None

    def _book_via_voice(self, pd, symptom_text):
        """Fill the AI symptom box, run the analysis, and -- once a department
        has been detected -- confirm the booking right away, so a spoken (or
        typed) symptom turns straight into a booked OP slot with no extra
        taps, the way asking a real reception assistant would."""
        pd.symptom_assistant.text.delete("1.0", "end")
        pd.symptom_assistant.text.insert("1.0", symptom_text)
        pd.symptom_assistant._analyze_now()

        dept = pd.symptom_assistant.last_dept
        if not dept:
            self._reply("I couldn't identify a condition from that. Could you describe your "
                         "symptoms a little more -- for example, 'fever and body pain since "
                         "yesterday'?")
            return

        pd.dept_combo.set(dept)
        pd.current_urgency = pd.symptom_assistant.last_urgency
        pd.current_symptoms_text = symptom_text
        pd.current_conditions = pd.symptom_assistant.last_conditions
        pd._book()

        appt_msg = pd.book_status.cget("text").replace("\n", ", ")
        urgent_note = (" This looks urgent -- please mention it at the OP counter."
                        if pd.symptom_assistant.last_urgency == "urgent" else "")
        self._reply(f"Done -- your appointment is booked. {appt_msg}.{urgent_note}")


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

        # Floating voice assistant -- created last (and re-lifted on every
        # screen change below) so its mic bubble floats above every screen:
        # role selection, login, patient dashboard, doctor dashboard, scan.
        self.voice_assistant = VoiceAssistant(self)

        self.show("RoleScreen")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- navigation -------------------------------------------------
    def show(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()
        if hasattr(self, "voice_assistant"):
            self.voice_assistant.raise_to_top()

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
        for text, sub, cmd, accent in [
            ("🧑  Patient", "Book & manage OP visits", lambda: app.show("PatientLoginScreen"), ROSE),
            ("🩺  Doctor", "Manage OP queue & records", lambda: app.show("DoctorLoginScreen"), SKY),
            ("🔍  Scan / Verify", "Scan a QR to view a booking", lambda: app.show("ScanScreen"), VIOLET),
        ]:
            tile = tk.Frame(row, bg=WHITE, highlightbackground=LINE, highlightthickness=1, width=210, height=140)
            tile.pack(side="left", padx=10)
            tile.pack_propagate(False)
            tk.Frame(tile, bg=accent, height=5).pack(fill="x", side="top")
            tk.Label(tile, text=text, font=("Segoe UI", 16, "bold"), bg=WHITE, fg=INK).pack(pady=(24, 6))
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

        tk.Label(card.body, text="Your photo (for your booking ticket)", font=F_SMALL,
                 fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(10, 3))
        photo_row = tk.Frame(card.body, bg=PAPER_RAISED)
        photo_row.pack(fill="x")
        self.selected_photo_path = None
        self._preview_ref = ImageTk.PhotoImage(make_initials_avatar("?", size=64))
        self.photo_preview = tk.Label(photo_row, image=self._preview_ref, bg=PAPER_RAISED,
                                       highlightbackground=LINE, highlightthickness=1)
        self.photo_preview.pack(side="left")
        photo_btns = tk.Frame(photo_row, bg=PAPER_RAISED)
        photo_btns.pack(side="left", padx=(12, 0))
        make_btn(photo_btns, "Upload photo", self._pick_photo, "rose").pack(anchor="w")
        tk.Label(photo_btns, text="Optional — a colourful avatar is used if skipped.",
                 font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED, wraplength=180,
                 justify="left").pack(anchor="w", pady=(6, 0))

        btnrow = tk.Frame(card.body, bg=PAPER_RAISED)
        btnrow.pack(fill="x", pady=(16, 0))
        make_btn(btnrow, "Verify & continue", self.verify, "primary").pack(fill="x")
        make_btn(btnrow, "Back", lambda: app.show("RoleScreen"), "ghost").pack(fill="x", pady=(8, 0))

    def _pick_photo(self):
        path = choose_photo_file(self)
        if not path:
            return
        self.selected_photo_path = path
        img = load_patient_photo_image(path, self.name_entry.get() or "?", size=64)
        self._preview_ref = ImageTk.PhotoImage(img)
        self.photo_preview.config(image=self._preview_ref)

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
        existing = app.data["patients"].get(mobile, {})
        photo_path = existing.get("photo")
        if self.selected_photo_path:
            saved = save_patient_photo(mobile, self.selected_photo_path)
            if saved:
                photo_path = saved
        record = {"name": name, "aadhaar_last4": aadhaar[-4:]}
        if photo_path:
            record["photo"] = photo_path
        app.data["patients"][mobile] = record
        app.persist()
        app.session.update({"role": "patient", "mobile": mobile, "name": name, "lang": "English"})
        app.set_session_label()
        # reset the upload widget for the next patient who uses this kiosk
        self.selected_photo_path = None
        self._preview_ref = ImageTk.PhotoImage(make_initials_avatar("?", size=64))
        self.photo_preview.config(image=self._preview_ref)
        self.aadhaar_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.mobile_entry.delete(0, tk.END)
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
            f"Booking ID:  {appt.get('id', '')}\n"
            f"Patient:     {appt.get('patient_name', '')}\n"
            f"Token:       {appt.get('token', '')}      Status: {appt.get('status', '')}\n"
            f"Department:  {appt.get('dept', '')}\n"
            f"Doctor:      {appt.get('doctor', '')}\n"
            f"Slot:        {appt.get('slot', '')}      Date: {appt.get('date', '')}"
        ))
        if hasattr(self, "_view_ticket_btn"):
            self._view_ticket_btn.destroy()
        photo_path = self.app.data.get("patients", {}).get(appt.get("mobile"), {}).get("photo") \
            or appt.get("photo")
        self._view_ticket_btn = make_btn(self.result_card.body, "View ticket (photo + QR + booking ID)",
                                          lambda: open_ticket_window(self.app, appt, photo_path), "violet")
        self._view_ticket_btn.pack(anchor="w", pady=(10, 0))

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

        # AI symptom assistant: patient types what's wrong, AI auto-fills
        # the department (and flags urgency) below as soon as it recognises
        # a condition -- no manual selection needed.
        self.current_urgency = "normal"
        self.current_symptoms_text = ""
        self.current_conditions = []
        self.symptom_assistant = SymptomAssistant(card.body, on_result=self._on_symptom_result)
        self.symptom_assistant.pack(fill="x", pady=(0, 8))
        make_btn(card.body, "⚡ Auto-Book with AI (fills & confirms instantly)",
                 self._auto_book, "amber").pack(fill="x", pady=(0, 16))
        tk.Frame(card.body, bg=LINE, height=1).pack(fill="x", pady=(0, 14))

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

        tk.Label(card.body, text="Photo for this booking's ticket", font=F_SMALL,
                 fg=INK, bg=PAPER_RAISED).pack(anchor="w", pady=(10, 3))
        photo_row = tk.Frame(card.body, bg=PAPER_RAISED)
        photo_row.pack(fill="x")
        self.book_photo_path = None  # overrides the patient's stored photo for just this booking
        self._book_preview_ref = ImageTk.PhotoImage(make_initials_avatar("?", size=56))
        self.book_photo_preview = tk.Label(photo_row, image=self._book_preview_ref, bg=PAPER_RAISED,
                                            highlightbackground=LINE, highlightthickness=1)
        self.book_photo_preview.pack(side="left")
        make_btn(photo_row, "Change photo", self._pick_book_photo, "rose").pack(side="left", padx=(12, 0))

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

        # side panel: pick a row above and a mini preview + "view ticket" appears here
        self.appt_qr_panel = tk.Frame(body, bg=PAPER_RAISED, width=220)
        self.appt_qr_panel.pack(side="left", fill="y", padx=(14, 0))
        self.appt_qr_panel.pack_propagate(False)
        self.appt_qr_hint = tk.Label(self.appt_qr_panel,
                                      text="Select an appointment above to view its ticket.",
                                      font=F_SMALL, fg=INK_SOFT, bg=PAPER_RAISED,
                                      wraplength=210, justify="left")
        self.appt_qr_hint.pack(anchor="w", pady=(0, 8))
        self.appt_qr_label = tk.Label(self.appt_qr_panel, bg=PAPER_RAISED)
        self.appt_qr_label.pack(anchor="w")
        self._selected_appt = None
        self.view_ticket_btn = make_btn(self.appt_qr_panel, "View full ticket",
                                         self._view_selected_ticket, "violet")
        self.view_ticket_btn.pack(anchor="w", pady=(10, 0), fill="x")

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
    def _on_symptom_result(self, dept, urgency, conditions, description):
        """Called live by SymptomAssistant as the patient types. Auto-fills
        the Department dropdown and remembers the urgency/description so
        they get saved with the booking -- this is the 'automatic text
        filling based on the user's description' the AI assistant provides."""
        self.current_urgency = urgency or "normal"
        self.current_symptoms_text = description or ""
        self.current_conditions = conditions or []
        if dept and dept in DEPTS:
            self.dept_combo.set(dept)

    def _auto_book(self):
        """One tap: run the AI analysis on whatever's typed in the symptom
        box, auto-fill the department, and confirm the booking immediately
        -- no need to separately press 'Confirm booking' below."""
        self.symptom_assistant._analyze_now()
        dept = self.symptom_assistant.last_dept
        if not dept:
            messagebox.showinfo(
                "Describe your symptoms",
                "Please describe how you're feeling in the box above first, "
                "so I can detect the right department.")
            return
        self.dept_combo.set(dept)
        self.current_urgency = self.symptom_assistant.last_urgency
        self.current_symptoms_text = self.symptom_assistant.get_description()
        self.current_conditions = self.symptom_assistant.last_conditions
        self._book()

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
        self.book_photo_path = None
        self._refresh_book_photo_preview()
        self.symptom_assistant.clear()
        self.current_urgency = "normal"
        self.current_symptoms_text = ""
        self.current_conditions = []

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

    def _patient_photo_path(self):
        mobile = self.app.session.get("mobile")
        return self.app.data.get("patients", {}).get(mobile, {}).get("photo")

    def _pick_book_photo(self):
        path = choose_photo_file(self)
        if not path:
            return
        self.book_photo_path = path
        img = load_patient_photo_image(path, self.app.session.get("name", "?"), size=56)
        self._book_preview_ref = ImageTk.PhotoImage(img)
        self.book_photo_preview.config(image=self._book_preview_ref)

    def _refresh_book_photo_preview(self):
        path = self.book_photo_path or self._patient_photo_path()
        img = load_patient_photo_image(path, self.app.session.get("name", "?"), size=56)
        self._book_preview_ref = ImageTk.PhotoImage(img)
        self.book_photo_preview.config(image=self._book_preview_ref)

    def _on_appt_select(self, event=None):
        sel = self.appts_tree.selection()
        if not sel:
            return
        appt = find_appointment_by_id(self.app.data, sel[0])
        if not appt:
            return
        self._selected_appt = appt
        photo_path = self.app.data.get("patients", {}).get(appt.get("mobile"), {}).get("photo") \
            or appt.get("photo")
        thumb = load_patient_photo_image(photo_path, appt.get("patient_name", ""), size=64)
        self._appt_thumb_ref = ImageTk.PhotoImage(thumb)
        self.appt_qr_label.config(image=self._appt_thumb_ref)
        self.appt_qr_hint.config(
            text=f"{appt.get('patient_name', '')}\nToken {appt.get('token', '')} · "
                 f"Booking ID {appt.get('id', '')}\nTap below for the full ticket "
                 f"(photo + QR + booking ID)."
        )

    def _view_selected_ticket(self):
        if not self._selected_appt:
            messagebox.showinfo("No appointment selected", "Select an appointment above first.")
            return
        appt = self._selected_appt
        photo_path = self.app.data.get("patients", {}).get(appt.get("mobile"), {}).get("photo") \
            or appt.get("photo")
        open_ticket_window(self.app, appt, photo_path)

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

        # resolve the photo for this booking's ticket: a freshly chosen photo
        # for just this booking, else the photo already on file for the
        # patient, else a generated colourful avatar (handled inside TicketCard)
        photo_path = self.app.data.get("patients", {}).get(mobile, {}).get("photo")
        if self.book_photo_path:
            saved = save_patient_photo(mobile, self.book_photo_path)
            if saved:
                photo_path = saved
                app.data.setdefault("patients", {}).setdefault(mobile, {"name": name})
                app.data["patients"][mobile]["photo"] = saved

        appt = {
            "id": str(uuid.uuid4())[:8],
            "mobile": mobile,
            "patient_name": name,
            "dept": dept,
            "doctor": DOCTOR_MAP.get(dept, ""),
            "slot": slot,
            "date": today_str(),
            "token": token,
            "urgency": self.current_urgency or "normal",
            "status": "waiting",
            "photo": photo_path,
            "symptoms": self.current_symptoms_text or "",
            "ai_conditions": self.current_conditions or [],
        }
        appt["qr"] = appointment_qr_payload(appt)
        app.data.setdefault("appointments", []).append(appt)
        app.persist()
        self.book_status.config(
            text=f"{tr(self.lang, 'token_msg')}: {token}  ·  {dept}  ·  {slot}\n"
                 f"Booking ID: {appt['id']}"
        )
        self._show_booking_qr(appt, photo_path)
        self.book_photo_path = None
        self.symptom_assistant.clear()
        self.current_urgency = "normal"
        self.current_symptoms_text = ""
        self.current_conditions = []
        self._reload_tables()
        open_ticket_window(app, appt, photo_path)

    def _show_booking_qr(self, appt, photo_path=None):
        """Inline mini-preview under the booking form: thumbnail + booking ID
        + a button to reopen the full movie-ticket-style pass."""
        for w in self.qr_frame.winfo_children():
            w.destroy()
        row = tk.Frame(self.qr_frame, bg=PAPER_RAISED)
        row.pack(anchor="w")
        thumb = load_patient_photo_image(photo_path, appt.get("patient_name", ""), size=56)
        self._booked_thumb_ref = ImageTk.PhotoImage(thumb)
        tk.Label(row, image=self._booked_thumb_ref, bg=PAPER_RAISED,
                 highlightbackground=LINE, highlightthickness=1).pack(side="left")
        info = tk.Frame(row, bg=PAPER_RAISED)
        info.pack(side="left", padx=(10, 0))
        tk.Label(info, text=f"Booking ID: {appt.get('id', '')}", font=F_MONO_B,
                 fg=TEAL_DARK, bg=PAPER_RAISED).pack(anchor="w")
        tk.Label(info, text=f"Token: {appt.get('token', '')}", font=F_MONO,
                 fg=INK_SOFT, bg=PAPER_RAISED).pack(anchor="w")
        make_btn(self.qr_frame, "Open full ticket (photo + QR)",
                 lambda: open_ticket_window(self.app, appt, photo_path), "violet").pack(anchor="w", pady=(8, 0))


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
        cols = ("token", "patient", "slot", "mobile", "urgency", "status", "reason")
        self.queue_tree = ttk.Treeview(card.body, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (70, 150, 100, 100, 80, 90, 220)):
            self.queue_tree.heading(c, text=c.title())
            self.queue_tree.column(c, width=w, anchor="center" if c != "reason" else "w")
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
            conditions = a.get("ai_conditions") or []
            reason = ", ".join(conditions) if conditions else (a.get("symptoms", "")[:40])
            self.queue_tree.insert("", "end", iid=a["id"],
                                    values=(a["token"], a["patient_name"], a["slot"],
                                            a["mobile"], a["urgency"], a["status"], reason))

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
