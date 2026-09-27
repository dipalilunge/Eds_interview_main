import os
import random
import re
import uuid
import zipfile
from datetime import datetime, timezone

from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename
from pypdf import PdfReader

from career_question_bank import QUESTION_BANK

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
RECORDING_DIR = os.path.join(BASE_DIR, "career_recordings")
RESUME_DIR = os.path.join(BASE_DIR, "career_resumes")
os.makedirs(RECORDING_DIR, exist_ok=True)
os.makedirs(RESUME_DIR, exist_ok=True)

career = Blueprint(
    "career",
    __name__,
    url_prefix="/career",
    template_folder="templates",
    static_folder="static/career",
    static_url_path="/static",
)
db = SQLAlchemy()
MOBILE_RE = re.compile(r"^\d{10}$")


def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(80), nullable=False)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(120), default="General")
    difficulty = db.Column(db.String(30), default="Mixed")
    question_type = db.Column(db.String(40), default="Technical")
    marks = db.Column(db.Integer, default=5)
    created_by = db.Column(db.String(30), default="EDS")

    subject = db.relationship("Subject", backref=db.backref("questions", lazy=True))


class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(150), nullable=False)
    year = db.Column(db.String(30), nullable=True)
    college = db.Column(db.String(150), nullable=True)
    contact = db.Column(db.String(30), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), default="active")
    total_score = db.Column(db.Float, nullable=True)

    subject = db.relationship("Subject")


class ResumeProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey("interview.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    extracted_text = db.Column(db.Text, default="")
    keywords = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    interview = db.relationship("Interview", backref=db.backref("resume", uselist=False, cascade="all, delete-orphan"))


class InterviewQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey("interview.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    question_order = db.Column(db.Integer, nullable=False)
    answer_file = db.Column(db.String(500), nullable=True)
    answer_duration = db.Column(db.Float, nullable=True)
    technical_score = db.Column(db.Float, nullable=True)
    communication_score = db.Column(db.Float, nullable=True)
    relevance_score = db.Column(db.Float, nullable=True)
    teacher_comment = db.Column(db.Text, nullable=True)

    interview = db.relationship(
        "Interview",
        backref=db.backref("interview_questions", lazy=True, cascade="all, delete-orphan")
    )
    question = db.relationship("Question")


def seed_data():
    subjects = [
        ("AutoCAD", "Mechanical Design"),
        ("SolidWorks", "Mechanical Design"),
        ("CATIA", "Mechanical Design"),
        ("Creo", "Mechanical Design"),
        ("UG-NX", "Mechanical Design"),
        ("Ansys", "Mechanical Design"),
        ("MasterCAM", "Mechanical Design"),
        ("Product Designing", "Mechanical Design"),
        ("Python", "IT & Software"),
        ("C Programming", "IT & Software"),
        ("Data Science", "IT & Software"),
        ("Generative AI", "IT & Software"),
        ("Data Analytics", "IT & Software"),
        ("Full Stack Python", "IT & Software"),
        ("Web Development", "IT & Software"),
        ("C++", "IT & Software"),
        ("Java", "IT & Software"),
        ("AutoCAD Civil", "Civil Design"),
        ("Revit Architecture", "Civil Design"),
        ("SketchUp", "Civil Design"),
    ]

    subject_map = {s.name: s for s in Subject.query.all()}
    for name, category in subjects:
        if name not in subject_map:
            s = Subject(name=name, category=category)
            db.session.add(s)
            db.session.flush()
            subject_map[name] = s

    sample_questions = {
        "Python": [
            ("What is the difference between a list and a tuple in Python?", "Data Structures", "Basic"),
            ("Explain inheritance in Python with a practical example.", "OOP", "Intermediate"),
            ("What are decorators in Python and why are they useful?", "Functions", "Advanced"),
            ("How would you handle exceptions in a production Python application?", "Exception Handling", "Intermediate"),
            ("Explain the difference between shallow copy and deep copy.", "Objects", "Advanced"),
            ("What is the difference between a generator and a normal function?", "Generators", "Advanced"),
            ("Explain Python virtual environments and why they are used.", "Environment", "Basic"),
            ("How would you optimize a slow Python program?", "Performance", "Advanced"),
            ("Explain *args and **kwargs with examples.", "Functions", "Intermediate"),
            ("What is the difference between == and is in Python?", "Basics", "Basic"),
        ],
        "C Programming": [
            ("What is a pointer in C and where is it used?", "Pointers", "Basic"),
            ("Explain the difference between malloc and calloc.", "Memory", "Intermediate"),
            ("What is a structure in C?", "Structures", "Basic"),
            ("Explain call by value and call by reference.", "Functions", "Intermediate"),
            ("How does dynamic memory allocation work in C?", "Memory", "Advanced"),
        ],
        "C++": [
            ("Explain the four main principles of object-oriented programming.", "OOP", "Basic"),
            ("What is the difference between a class and an object?", "OOP", "Basic"),
            ("Explain function overloading and overriding in C++.", "Polymorphism", "Intermediate"),
            ("What is STL and why is it useful?", "STL", "Intermediate"),
            ("Explain virtual functions and runtime polymorphism.", "OOP", "Advanced"),
        ],
        "Java": [
            ("What is the difference between JDK, JRE and JVM?", "Java Basics", "Basic"),
            ("Explain inheritance in Java.", "OOP", "Basic"),
            ("What is the Java Collections Framework?", "Collections", "Intermediate"),
            ("Explain exception handling in Java.", "Exceptions", "Intermediate"),
            ("What is the difference between an interface and an abstract class?", "OOP", "Advanced"),
        ],
        "SQL": [
            ("What is the difference between WHERE and HAVING?", "Queries", "Basic"),
            ("Explain INNER JOIN, LEFT JOIN and RIGHT JOIN.", "Joins", "Intermediate"),
            ("What is normalization and why is it used?", "Database Design", "Intermediate"),
            ("What is an index and how can it improve query performance?", "Performance", "Advanced"),
        ],
        "AutoCAD": [
            ("What is the difference between model space and paper space?", "Drafting", "Basic"),
            ("Explain layers and their importance in an engineering drawing.", "Layers", "Basic"),
            ("What is dimensioning and why is it important?", "Dimensioning", "Intermediate"),
        ],
        "SolidWorks": [
            ("Explain the difference between a part, assembly and drawing.", "CAD Basics", "Basic"),
            ("What are sketch in SolidWorks?", "Assembly", "Intermediate"),
            ("What is the difference between Fully Defined and Under Defined Sketches?", "Assembly", "Intermediate"),
            ("What are Geometric relations in a sketch?", "Assembly", "Intermediate"),
            ("What is the Extruded Boss/base?", "Part Design", "Intermediate"),
            ("What is the diference between Fillet and Chamfer?", "Assembly", "Intermediate"),
            ("What is the purpose of shell feature?", "Assembly", "Intermediate"),
            ("What is the revolve feature used for?", "Assembly", "Intermediate"),
            ("What is Assembly in SolidWorks?", "Assembly", "Intermediate"),
            ("What ais Mate?", "Assembly", "Intermediate"),
            ("What is Exploded view?", "Assembly", "Intermediate"),
            ("What is a Solid Work Drawing?", "Drafting", "Intermediate"),
            ("What is purpose of section view?", "Assembly", "Intermediate"),
            ("What is the difference between Coincident and center Mate?", "Assembly", "Intermediate"),
            ("What is the difference between Solid Modeling and Surface Modeling, and what is a Flat Pattern in sheet metal?", "Surfacing and sheet metal", "Intermediate"),
            ("Explain the purpose of design intent.", "Part Design", "Advanced"),
        ],
        "CATIA": [
            ("What is Part Design in CATIA?", "Part Design", "Basic"),
            ("Explain the role of sketches in CATIA.", "Sketcher", "Basic"),
            ("What is assembly design?", "Assembly", "Intermediate"),
        ],
    }

    # Add SQL even if it is not currently visible on the supplied screenshot.
    if "SQL" not in subject_map:
        s = Subject(name="SQL", category="IT & Software")
        db.session.add(s)
        db.session.flush()
        subject_map["SQL"] = s

    for subject_name, questions in QUESTION_BANK.items():
        sample_questions.setdefault(subject_name, []).extend(questions)

    for subject_name, questions in sample_questions.items():
        subject = subject_map.get(subject_name)
        if not subject:
            continue
        for text, topic, difficulty in questions:
            if Question.query.filter_by(subject_id=subject.id, text=text).first():
                continue
            db.session.add(Question(
                subject_id=subject.id,
                text=text,
                topic=topic,
                difficulty=difficulty,
                question_type="Technical",
                marks=5,
                created_by="EDS"
            ))

    db.session.commit()


SKILL_ALIASES = {
    "python": "Python", "flask": "Full Stack Python", "django": "Full Stack Python",
    "sql": "SQL", "database": "SQL", "analytics": "Data Analytics", "tableau": "Data Analytics",
    "machine learning": "Data Science", "data science": "Data Science", "pandas": "Data Science",
    "javascript": "Web Development", "html": "Web Development", "css": "Web Development",
    "react": "Web Development", "java": "Java", "c++": "C++", "c programming": "C Programming",
    "autocad": "AutoCAD", "solidworks": "SolidWorks", "catia": "CATIA", "ansys": "Ansys",
    "revit": "Revit Architecture", "sketchup": "SketchUp", "generative ai": "Generative AI",
    "machine design": "Product Designing", "product design": "Product Designing",
}


def extract_resume_text(upload):
    """Extract useful text from common resume formats without adding a dependency."""
    raw = upload.read()
    upload.seek(0)
    name = (upload.filename or "").lower()
    if name.endswith(".docx"):
        try:
            with zipfile.ZipFile(__import__("io").BytesIO(raw)) as archive:
                xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
            return re.sub(r"<[^>]+>", " ", xml)
        except (KeyError, zipfile.BadZipFile):
            return ""
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(__import__("io").BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return raw.decode("latin-1", errors="ignore")
    return raw.decode("utf-8", errors="ignore")


def resume_skills(text):
    lowered = text.lower()
    found = []
    for alias, subject_name in SKILL_ALIASES.items():
        if alias in lowered and subject_name not in found:
            found.append(subject_name)
    return found


def choose_questions(subject_id, skills):
    subject_ids = [subject_id]
    for skill in skills:
        matched = Subject.query.filter_by(name=skill).first()
        if matched and matched.id not in subject_ids:
            subject_ids.append(matched.id)
    questions = Question.query.filter(Question.subject_id.in_(subject_ids)).all()
    random.shuffle(questions)
    return questions[:min(len(questions), 30)]


@career.route("/")
def index():
    subjects = Subject.query.order_by(Subject.category, Subject.name).all()
    grouped = {}
    for s in subjects:
        grouped.setdefault(s.category, []).append(s)
    return render_template("career/index.html", grouped=grouped)


@career.route("/interview/start", methods=["POST"])
def start_interview():
    student_name = request.form.get("student_name", "").strip()
    year = request.form.get("year", "").strip()
    college = request.form.get("college", "").strip()
    contact = request.form.get("contact", "").strip()
    subject_id = request.form.get("subject_id", type=int)

    if not student_name or not year or not college or not subject_id:
        return jsonify({"error": "Name, year, college and subject are required."}), 400
    if not MOBILE_RE.fullmatch(contact):
        return jsonify({"error": "Enter a valid 10-digit contact number."}), 400

    subject = db.session.get(Subject, subject_id)
    if not subject:
        return jsonify({"error": "Subject not found."}), 404

    resume_upload = request.files.get("resume")
    resume_text = ""
    skills = []
    if resume_upload and resume_upload.filename:
        resume_text = extract_resume_text(resume_upload)
        skills = resume_skills(resume_text)

    questions = choose_questions(subject_id, skills)
    if not questions:
        return jsonify({"error": "No questions are available for this subject yet."}), 400

    # Controlled randomization:
    # shuffle all available questions; the frontend advances through them.
    random.shuffle(questions)
    selected = questions[:min(len(questions), 30)]

    interview = Interview(
        student_name=student_name,
        year=year,
        college=college,
        contact=contact,
        subject_id=subject_id,
        status="active"
    )
    db.session.add(interview)
    db.session.flush()

    if resume_upload and resume_upload.filename:
        safe_name = secure_filename(resume_upload.filename) or "resume.txt"
        saved_name = f"{interview.id}_{uuid.uuid4().hex}_{safe_name}"
        with open(os.path.join(RESUME_DIR, saved_name), "wb") as saved_resume:
            saved_resume.write(resume_text.encode("utf-8"))
        db.session.add(ResumeProfile(
            interview_id=interview.id,
            filename=safe_name,
            extracted_text=resume_text[:50000],
            keywords=", ".join(skills),
        ))

    for order, q in enumerate(selected, start=1):
        db.session.add(InterviewQuestion(
            interview_id=interview.id,
            question_id=q.id,
            question_order=order
        ))

    db.session.commit()
    return redirect(url_for("career.interview_room", interview_id=interview.id))


@career.route("/interview/<int:interview_id>")
def interview_room(interview_id):
    interview = db.session.get(Interview, interview_id)
    if not interview:
        return "Interview not found", 404
    questions = InterviewQuestion.query.filter_by(
        interview_id=interview_id
    ).order_by(InterviewQuestion.question_order).all()
    return render_template(
        "career/interview.html",
        interview=interview,
        questions=questions
    )


@career.post("/api/interview/<int:interview_id>/answer")
def upload_answer(interview_id):
    interview = db.session.get(Interview, interview_id)
    if not interview or interview.status != "active":
        return jsonify({"error": "Interview is not active."}), 400

    iq_id = request.form.get("interview_question_id", type=int)
    duration = request.form.get("duration", type=float, default=0)
    video = request.files.get("video")

    iq = db.session.get(InterviewQuestion, iq_id)
    if not iq or iq.interview_id != interview_id:
        return jsonify({"error": "Invalid interview question."}), 400

    if video:
        ext = ".webm"
        filename = secure_filename(f"{interview_id}_{iq_id}_{uuid.uuid4().hex}{ext}")
        path = os.path.join(RECORDING_DIR, filename)
        video.save(path)
        iq.answer_file = os.path.join("recordings", filename).replace("\\", "/")

    iq.answer_duration = duration
    db.session.commit()
    return jsonify({"success": True})


@career.post("/api/interview/<int:interview_id>/complete")
def complete_interview(interview_id):
    interview = db.session.get(Interview, interview_id)
    if not interview:
        return jsonify({"error": "Interview not found."}), 404

    interview.status = "completed"
    interview.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"success": True, "redirect": url_for("career.results", interview_id=interview_id)})


@career.get("/teacher")
@staff_required
def teacher_dashboard():
    interviews = Interview.query.order_by(Interview.started_at.desc()).all()
    return render_template("career/teacher.html", interviews=interviews)


@career.route("/recruiter", methods=["GET", "POST"])
@staff_required
def recruiter_dashboard():
    subjects = Subject.query.order_by(Subject.category, Subject.name).all()
    if request.method == "POST":
        subject_id = request.form.get("subject_id", type=int)
        text = request.form.get("text", "").strip()
        topic = request.form.get("topic", "Recruiter question").strip() or "Recruiter question"
        recruiter = request.form.get("recruiter", "Recruiter").strip() or "Recruiter"
        if subject_id and text and db.session.get(Subject, subject_id):
            db.session.add(Question(
                subject_id=subject_id,
                text=text,
                topic=topic,
                difficulty=request.form.get("difficulty", "Mixed"),
                question_type="Recruiter",
                marks=5,
                created_by=recruiter[:30],
            ))
            db.session.commit()
        return redirect(url_for("career.recruiter_dashboard"))

    position = request.args.get("position", "").strip()
    query = Interview.query.filter_by(status="completed")
    if position:
        query = query.join(Subject).filter(Subject.name.ilike(f"%{position}%"))
    interviews = query.order_by(Interview.completed_at.desc()).all()
    recruiter_questions = Question.query.filter_by(question_type="Recruiter").order_by(Question.id.desc()).all()
    return render_template(
        "career/recruiter.html",
        subjects=subjects,
        interviews=interviews,
        recruiter_questions=recruiter_questions,
        position=position,
    )


@career.get("/teacher/interview/<int:interview_id>")
@staff_required
def teacher_review(interview_id):
    interview = db.session.get(Interview, interview_id)
    if not interview:
        return "Interview not found", 404

    questions = InterviewQuestion.query.filter_by(
        interview_id=interview_id
    ).order_by(InterviewQuestion.question_order).all()

    return render_template("career/review.html", interview=interview, questions=questions)


@career.post("/api/evaluation/<int:iq_id>")
@staff_required
def save_evaluation(iq_id):
    iq = db.session.get(InterviewQuestion, iq_id)
    if not iq:
        return jsonify({"error": "Question not found."}), 404

    data = request.get_json(silent=True) or {}

    iq.technical_score = max(0, min(5, float(data.get("technical_score", 0))))
    iq.communication_score = max(0, min(5, float(data.get("communication_score", 0))))
    iq.relevance_score = max(0, min(5, float(data.get("relevance_score", 0))))
    iq.teacher_comment = data.get("teacher_comment", "").strip()

    db.session.commit()

    all_items = InterviewQuestion.query.filter_by(interview_id=iq.interview_id).all()
    scored = [
        (x.technical_score + x.communication_score + x.relevance_score) / 15 * 100
        for x in all_items
        if x.technical_score is not None
        and x.communication_score is not None
        and x.relevance_score is not None
    ]

    if scored:
        iq.interview.total_score = round(sum(scored) / len(scored), 2)
        db.session.commit()

    return jsonify({"success": True, "overall": iq.interview.total_score})


@career.get("/results/<int:interview_id>")
def results(interview_id):
    interview = db.session.get(Interview, interview_id)
    if not interview:
        return "Interview not found", 404

    questions = InterviewQuestion.query.filter_by(
        interview_id=interview_id
    ).order_by(InterviewQuestion.question_order).all()

    return render_template("career/results.html", interview=interview, questions=questions)


@career.route("/admin/questions", methods=["GET", "POST"])
@staff_required
def question_admin():
    if request.method == "POST":
        subject_id = request.form.get("subject_id", type=int)
        text = request.form.get("text", "").strip()
        topic = request.form.get("topic", "General").strip()
        difficulty = request.form.get("difficulty", "Mixed")

        if subject_id and text:
            db.session.add(Question(
                subject_id=subject_id,
                text=text,
                topic=topic,
                difficulty=difficulty,
                question_type="Technical",
                marks=5,
                created_by="Admin"
            ))
            db.session.commit()
        return redirect(url_for("career.question_admin"))

    subjects = Subject.query.order_by(Subject.category, Subject.name).all()
    questions = Question.query.order_by(Question.id.desc()).all()
    return render_template("career/admin_questions.html", subjects=subjects, questions=questions)


@career.get("/recordings/<path:filename>")
def recording_file(filename):
    return send_from_directory(RECORDING_DIR, filename)


def init_career(app):
    app.config.setdefault(
        "SQLALCHEMY_DATABASE_URI",
        os.environ.get(
            "EDS_CAREER_DATABASE_URL",
            "sqlite:///" + os.path.join(BASE_DIR, "career_interview.db"),
        ),
    )
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("MAX_CONTENT_LENGTH", 500 * 1024 * 1024)
    db.init_app(app)
    app.register_blueprint(career)
    with app.app_context():
        db.create_all()
        interview_columns = {
            column["name"] for column in inspect(db.engine).get_columns("interview")
        }
        for column_name, column_type in (
            ("year", "VARCHAR(30)"),
            ("college", "VARCHAR(150)"),
            ("contact", "VARCHAR(30)"),
        ):
            if column_name not in interview_columns:
                db.session.execute(text(f"ALTER TABLE interview ADD COLUMN {column_name} {column_type}"))
        db.session.commit()
        seed_data()
