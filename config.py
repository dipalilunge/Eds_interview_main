"""
Engineering Design Studio — central configuration.

Edit the values in this file to match your real institute details,
Google Sheet, and Google Drive folders. Nothing here needs code changes
elsewhere — the rest of the app reads from this file.
"""

import json
import os
import secrets
import tempfile


def _read_streamlit_secret_json():
    """Read a Google credentials JSON payload from Streamlit Cloud secrets if present."""
    try:
        import streamlit as st  # type: ignore
    except Exception:
        return None

    try:
        secrets = getattr(st, "secrets", {}) or {}
        for key in ("google_credentials_json", "EDS_GOOGLE_CREDENTIALS_JSON", "google_credentials"):
            value = secrets.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, dict):
                return json.dumps(value)
    except Exception:
        return None
    return None


def _resolve_google_credentials_file():
    """Support runtime credentials from environment/secrets for Streamlit Cloud free hosting."""
    preferred = os.environ.get("EDS_GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
    raw_json = os.environ.get("EDS_GOOGLE_CREDENTIALS_JSON") or _read_streamlit_secret_json()

    if raw_json and not os.path.exists(preferred):
        fd, path = tempfile.mkstemp(prefix="eds-google-creds-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(raw_json)
        return path

    return preferred


# ---------------------------------------------------------------------------
# Basic app / security settings
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("EDS_SECRET_KEY") or secrets.token_urlsafe(32)

# Password admin staff use to reach the admissions dashboard.
ADMIN_PASSWORD = os.environ.get("EDS_ADMIN_PASSWORD", "Eds_2026@admin")

# Password students use to reach the notes/resources page.
STUDENT_PASSWORD = os.environ.get("EDS_STUDENT_PASSWORD", "")

# ---------------------------------------------------------------------------
# Google Sheets integration (admissions data)
# ---------------------------------------------------------------------------
# 1. Create a Google Cloud service account, enable the Sheets + Drive APIs.
# 2. Download its JSON key and save it as google_credentials.json in this
#    folder (keep it out of version control).
# 3. Share your admissions Google Sheet with the service account's email
#    address (Editor access).
# 4. Put the Sheet's ID (from its URL) below.
GOOGLE_CREDENTIALS_FILE = _resolve_google_credentials_file()
GOOGLE_CREDENTIALS_JSON = os.environ.get("EDS_GOOGLE_CREDENTIALS_JSON") or _read_streamlit_secret_json() or ""
ADMISSIONS_SHEET_ID = os.environ.get(
    "EDS_ADMISSIONS_SHEET_ID",
    "",
)
ADMISSIONS_WORKSHEET_NAME = os.environ.get("EDS_ADMISSIONS_WORKSHEET", "Admissions")

# If the sheet isn't configured yet, admissions are saved locally to this
# CSV file instead, so the form still works during setup/demo.
LOCAL_ADMISSIONS_FALLBACK = "admissions_local.csv"

# ---------------------------------------------------------------------------
# Google Drive integration (course notes)
# ---------------------------------------------------------------------------
# Create one Drive folder per course, set sharing to "Anyone with the link
# — Viewer", and paste the folder link below against the matching course id.
DRIVE_NOTES_LINKS = {
    "python": "https://drive.google.com/drive/folders/1N1rxBf_DQuQXfFQxweU3cRoHU-g42S73",
    "sql": "https://drive.google.com/drive/folders/16AhZkVy4F4360Rc7Q4FTsfcdssw5N4jc",
    "cpp": "https://drive.google.com/drive/folders/1c7_kIYGTxFv4leskldqOq9BAkH0YdiWt",
    "java": "https://drive.google.com/drive/folders/1SJY96Ov4wsJCIxwebZY-FTWVxZt15b6o",
    "data-science": "https://drive.google.com/drive/folders/1UkXPPWVpvGz2Hgo1Nm_avnJqUNxPoz1g",
    "data-analytics": "https://drive.google.com/drive/folders/1x_UXVS8sYO8m4KnZmScR-CikxJM7U3AG",
    "ai": "https://drive.google.com/drive/folders/1UsGaBNtP4V8kPb5UtGHohQV2p_Nweyiv",
    "catia": "https://drive.google.com/drive/folders/1OjXQrIi9CgAoLZH62lDNoq9gLggqe3aM",
    "creo": "https://drive.google.com/drive/folders/1-Ch7KuJ4wGhRLhOtfTSJ29l_RpSnAV_X",
    "solidworks": "https://drive.google.com/drive/folders/1tuWqYKHobwhOb7wMO8NHPiFO7qTjP5G2",
    "autocad": "https://drive.google.com/drive/folders/1nbHUUgxhL_f8drEryB5FFupwBxU4XnI7",
    "ug-nx": "https://drive.google.com/drive/folders/1zKcSM2Pvo2Eu7v2WXs78eXwlcSQagmBB",
    "ansys": "https://drive.google.com/drive/folders/1P1EhvJczqdYbqfnpCku9Prh6fZsdHvRc",
    "mastercam": "https://drive.google.com/drive/folders/1dT9J92l9mSJl4dW_uqSPfHzOQhLorPvk",
    "product-designing": "https://drive.google.com/drive/folders/1rZVC_iXBjFJnhzlQiyQ0bWKs6csd7ed8",
    "c-programming": "https://drive.google.com/drive/folders/1LcTSxcSh3G-CwhRwX1NxeCzwgj3G8Cp8",
    "generative-ai": "https://drive.google.com/drive/folders/1UsGaBNtP4V8kPb5UtGHohQV2p_Nweyiv",
    "full-stack-python": "https://drive.google.com/drive/folders/1O1uMC-MOhFsUgr9S7j3BQ49OJXP6FyhH",
    "web-development": "https://drive.google.com/drive/folders/1hhwMM48ZlOqowHof9eTpO5z7HRZh-j81",
    "autocad-civil": "https://drive.google.com/drive/folders/1p5vHFM63iYTLQm3j2sk-V-oUt7-PXFBy",
    "revit-architecture": "https://drive.google.com/drive/folders/1Pl0Wp1TpYgil4jLYZl-eZYz04r2mgh1N",
    "sketch-up": "https://drive.google.com/drive/folders/1s9IAnYyeOpId8ybCFjUh-lrKUnfWMlRd",
    "v-ray": "https://drive.google.com/drive/folders/1lRasPQGLZLuP6F7R7vZFUxY5UjtvkL1A",
    "electrical-cad": "https://drive.google.com/drive/folders/1-FFxX_k4nj0H8A28s1Q2X3LNGCjLRfHe",
    "plc-programming": "https://drive.google.com/drive/folders/1A-9ql8HkYMrdrjZSxhXyFlrTMdNoK7QQ",
}

# Optional: folder ID in Google Drive where interview recordings will be uploaded.
# Set via EDS_DRIVE_INTERVIEW_FOLDER_ID or leave empty to save recordings locally.
DRIVE_INTERVIEW_FOLDER_ID = os.environ.get("EDS_DRIVE_INTERVIEW_FOLDER_ID", "")

# ---------------------------------------------------------------------------
# Institute info shown on the homepage
# ---------------------------------------------------------------------------
INSTITUTE = {
    "name": "Engineering Design Studio",
    "tagline": "Where blueprints become careers.",
    "address": "Second Floor, Sharda Complex, Metro Station, Beside Bharat Petrolpump, Near Bansi Nagar, S R P Camp, Digdoh, Nagpur, Maharashtra 440036",
    "phone": "+91 8793712986",
    "email": "eds000@gmail.com",
    "hours": "Mon – Sun, 8:00 AM – 9:30 PM",
    "map_query": "second floor, sharda complex, metro station, beside Bharat Petrolpump, near bansi nagar, Bansi Nagar, S R P Camp, Nagpur, Digdoh, Maharashtra 440036",
}

NOTIFICATIONS = [
    "Admissions are open for the new Mechanical, IT, Civil and Electrical courses.",
    "SolidWorks weekend batch now open for working professionals.",
    "Early admission discount of ₹1,500 valid through this month.",
]

# id must match the keys used in DRIVE_NOTES_LINKS above.
COURSES = [
    {
        "id": "autocad",
        "name": "AutoCAD",
        "track": "Mechanical Design",
        "duration": "2 months",
        "fee": 5500,
        "summary": "2D drafting, dimensioning and layout standards for engineering drawings.",
    },
    {
        "id": "solidworks",
        "name": "SolidWorks",
        "track": "Mechanical Design",
        "duration": "2 months",
        "fee": 6500,
        "summary": "Part design, assemblies, simulation basics and 2D drawing generation.",
    },
    {
        "id": "catia",
        "name": "CATIA",
        "track": "Mechanical Design",
        "duration": "2 months",
        "fee": 7500,
        "summary": "3D part and assembly modelling, surfacing and engineering drafting.",
    },
    {
        "id": "creo",
        "name": "Creo",
        "track": "Mechanical Design",
        "duration": "2 months",
        "fee": 7500,
        "summary": "Parametric modelling, assemblies and sheet-metal design workflows.",
    },
    {
        "id": "ug-nx",
        "name": "UG-NX",
        "track": "Mechanical Design",
        "duration": "2 months",
        "fee": 9500,
        "summary": "Advanced 3D CAD modelling, assemblies and manufacturing design workflows.",
    },
    {
        "id": "ansys",
        "name": "Ansys",
        "track": "Mechanical Design",
        "duration": "2 months",
        "fee": 9500,
        "summary": "Engineering simulation, analysis setup and interpretation of design results.",
    },
    {
        "id": "mastercam",
        "name": "MasterCAM",
        "track": "Mechanical Design",
        "duration": "2 months",
        "fee": 8000,
        "summary": "CAM programming, toolpaths and CNC manufacturing preparation.",
    },
    {
        "id": "product-designing",
        "name": "Product Designing",
        "track": "Mechanical Design",
        "duration": "4 months",
        "fee": 45000,
        "summary": "End-to-end product development, engineering design, prototyping and presentation.",
    },
    {
        "id": "python",
        "name": "Python",
        "track": "IT & Software",
        "duration": "2 months",
        "fee": 8500,
        "summary": "Programming fundamentals, OOP, automation and practical application building.",
    },
    {
        "id": "c-programming",
        "name": "C Programming",
        "track": "IT & Software",
        "duration": "2 months",
        "fee": 8000,
        "summary": "Structured programming, memory, functions and problem solving in C.",
    },
    {
        "id": "data-science",
        "name": "Data Science",
        "track": "IT & Software",
        "duration": "4 months",
        "fee": 45000,
        "summary": "Statistics, data preparation, machine learning and end-to-end projects.",
    },
    {
        "id": "generative-ai",
        "name": "Generative AI",
        "track": "IT & Software",
        "duration": "3 months",
        "fee": 45000,
        "summary": "Generative models, prompt engineering and practical AI application development.",
    },
    {
        "id": "data-analytics",
        "name": "Data Analytics",
        "track": "IT & Software",
        "duration": "3 months",
        "fee": 45000,
        "summary": "Data preparation, reporting, dashboards and business-focused analytics workflows.",
    },
    {
        "id": "full-stack-python",
        "name": "Full Stack Python",
        "track": "IT & Software",
        "duration": "5 months",
        "fee": 40000,
        "summary": "Frontend, backend, databases and deployment with Python web technologies.",
    },
    {
        "id": "web-development",
        "name": "Web Development",
        "track": "IT & Software",
        "duration": "3 months",
        "fee": 20000,
        "summary": "Modern frontend and backend development for responsive web applications.",
    },
    {
        "id": "cpp",
        "name": "C++",
        "track": "IT & Software",
        "duration": "3 months",
        "fee": 15000,
        "summary": "Object-oriented programming, STL and practical C++ problem solving.",
    },
    {
        "id": "java",
        "name": "Java",
        "track": "IT & Software",
        "duration": "3 months",
        "fee": 15000,
        "summary": "Core Java, OOP, collections and application development fundamentals.",
    },
    {
        "id": "autocad-civil",
        "name": "AutoCAD Civil",
        "track": "Civil Design",
        "duration": "2 months",
        "fee": 5500,
        "summary": "Civil drafting, plans, sections and construction documentation.",
    },
    {
        "id": "revit-architecture",
        "name": "Revit Architecture",
        "track": "Civil Design",
        "duration": "2 months",
        "fee": 7500,
        "summary": "Building information modelling and architectural documentation.",
    },
    {
        "id": "sketch-up",
        "name": "SketchUp",
        "track": "Civil Design",
        "duration": "2 months",
        "fee": 7500,
        "summary": "Fast 3D architectural modelling and design visualization.",
    },
    {
        "id": "v-ray",
        "name": "V-Ray",
        "track": "Civil Design",
        "duration": "2 months",
        "fee": 7500,
        "summary": "Architectural rendering, materials, lighting and visualization.",
    },
    {
        "id": "electrical-cad",
        "name": "Electrical CAD",
        "track": "Electrical Design",
        "duration": "2 months",
        "fee": 5500,
        "summary": "Electrical schematics, layouts and engineering documentation.",
    },
    {
        "id": "plc-programming",
        "name": "PLC Programming",
        "track": "Electrical Design",
        "duration": "2 months",
        "fee": 7500,
        "summary": "Industrial automation, ladder logic and PLC control systems.",
    },
]

# Static FAQ assistant — simple keyword -> answer pairs, no external API.
FAQ_PAIRS = [
    {
        "keywords": ["fee", "fees", "cost", "price"],
        "answer": "Course fees vary by course and are shown in the Courses section. Ask about a specific course for its current fee.",
    },
    {
        "keywords": ["python"],
        "answer": "Python runs for 2 months and costs ₹8,500. It covers programming fundamentals, OOP and practical application building.",
    },
    {
        "keywords": ["java"],
        "answer": "Java runs for 3 months and costs ₹15,000, covering core Java, OOP and application development fundamentals.",
    },
    {
        "keywords": ["c++", "cpp"],
        "answer": "C++ Programming runs for 2 months and costs ₹8,000, covering systems programming, memory management and STL.",
    },
    {
        "keywords": ["data science"],
        "answer": "Data Science runs for 4 months and costs ₹45,000, covering statistics, data preparation and machine learning projects.",
    },
    {
        "keywords": ["data analytics", "analytics"],
        "answer": "Data Analytics runs for 3 months and costs ₹45,000, covering data preparation, reporting and dashboards.",
    },
    {
        "keywords": ["generative ai", " ai ", "ai"],
        "answer": "Generative AI runs for 3 months and costs ₹45,000, covering generative models, prompt engineering and practical AI applications.",
    },
    {
        "keywords": ["catia"],
        "answer": "CATIA runs for 2 months and costs ₹7,500, covering 3D modelling, surfacing and drafting.",
    },
    {
        "keywords": ["creo", "pro-e", "proe"],
        "answer": "Creo (Pro-E) runs for 2 months and costs ₹12,000, covering parametric modelling and assemblies.",
    },
    {
        "keywords": ["solidworks", "solid work"],
        "answer": "SolidWorks runs for 2 months and costs ₹6,500, covering part design, assemblies and simulation basics.",
    },
    {
        "keywords": ["autocad", "auto cad"],
        "answer": "AutoCAD runs for 2 months and costs ₹5,500, covering 2D drafting and dimensioning standards.",
    },
    {
        "keywords": ["placement", "job", "career", "hire"],
        "answer": "We started this year and are currently focused on building strong technical training and practical student projects.",
    },
    {
        "keywords": ["address", "location", "where"],
        "answer": "We're located at Second Floor, Sharda Complex (near Metro Station), beside Bharat Petrolpump, Bansi Nagar, S R P Camp, Digdoh, Nagpur — PIN 440036. See the map on the Contact section for directions.",
    },
    {
        "keywords": ["contact", "phone", "number", "email"],
        "answer": "Call us at +91 98765 43210 or email info@engineeringdesignstudio.in. We're open Mon–Sat, 9:30 AM – 7:00 PM.",
    },
    {
        "keywords": ["timing", "hours", "open"],
        "answer": "We're open Monday to Saturday, 9:30 AM to 7:00 PM.",
    },
    {
        "keywords": ["admission", "enroll", "enrol", "join", "register"],
        "answer": "Visit us in person or call +91 98765 43210 to start your admission. Our team will guide you through course selection and paperwork.",
    },
    {
        "keywords": ["notes", "material", "resources"],
        "answer": "Enrolled students can access course notes on the Student page using the password shared by their instructor.",
    },
]
FAQ_FALLBACK = "I don't have an answer for that yet — please call us at +91 98765 43210 or email info@engineeringdesignstudio.in and our team will help directly."
