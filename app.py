import os
import re
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file

import config
import sheets_helper
import auth_helper
import ai_helper
from interview_engine import engine as interview_engine
from speech_service import speech_service

from werkzeug.utils import secure_filename
import tempfile
import time
import json

import drive_helper
import portal_storage
from career_interview import init_career

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
init_career(app)

AADHAR_RE = re.compile(r"^\d{12}$")
MOBILE_RE = re.compile(r"^\d{10}$")


def courses_by_id():
    return {c["id"]: c for c in config.COURSES}


def student_enrollment(student):
    admission = sheets_helper.get_admission_for_name(student.get("name", ""))
    if not admission:
        return None
    course = next(
        (c for c in config.COURSES if c["name"].strip().lower() == str(admission.get("Course Name", "")).strip().lower()),
        None,
    )
    batches = portal_storage.get_batches()
    batch_id = str(admission.get("Batch ID", ""))
    batch_name = str(admission.get("Batch Name", ""))
    batch = next((b for b in batches if b.get("id") == batch_id), None)
    if not batch and batch_name:
        batch = next((b for b in batches if b.get("name", "").strip().lower() == batch_name.strip().lower()), None)
    if not course or not batch or batch.get("course_id") != course.get("id"):
        return None
    return {"course": course, "batch": batch, "admission": admission}


# ---------------------------------------------------------------------------
# Public site
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    mech_courses = [c for c in config.COURSES if c["track"] == "Mechanical Design"]
    it_courses = [c for c in config.COURSES if c["track"] == "IT & Software"]
    civil_courses = [c for c in config.COURSES if c["track"] == "Civil Design"]
    electrical_courses = [c for c in config.COURSES if c["track"] == "Electrical Design"]
    return render_template(
        "index.html",
        institute=config.INSTITUTE,
        notifications=config.NOTIFICATIONS,
        it_courses=it_courses,
        mech_courses=mech_courses,
        civil_courses=civil_courses,
        electrical_courses=electrical_courses,
    )


@app.route("/api/faq", methods=["POST"])
def faq():
    question = (request.json or {}).get("question", "").lower().strip()
    if not question:
        return jsonify({"answer": config.FAQ_FALLBACK})

    best_answer = None
    best_score = 0
    for pair in config.FAQ_PAIRS:
        # Weight by the length of matched keywords so specific phrases
        # ("data science") outrank generic ones ("fee") when both match.
        score = sum(len(kw.strip()) for kw in pair["keywords"] if kw.strip() in question)
        if score > best_score:
            best_score = score
            best_answer = pair["answer"]

    return jsonify({"answer": best_answer or config.FAQ_FALLBACK})


# ---------------------------------------------------------------------------
# Admin — admissions handling, backed by Google Sheets
# ---------------------------------------------------------------------------
def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if config.ADMIN_PASSWORD and request.form.get("password") == config.ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        if not config.ADMIN_PASSWORD:
            flash("Admin login is not configured. Set EDS_ADMIN_PASSWORD in the environment.", "error")
            return render_template("admin_login.html", institute=config.INSTITUTE)
        flash("Incorrect password.", "error")
    return render_template("admin_login.html", institute=config.INSTITUTE)


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_dashboard():
    cbi = courses_by_id()

    if request.method == "POST":
        if request.form.get("action") == "create_batch":
            course_id = request.form.get("batch_course_id", "")
            batch_name = request.form.get("batch_name", "").strip()
            start_date = request.form.get("start_date", "").strip()
            batch_fee = request.form.get("batch_fee", "").strip()
            course = cbi.get(course_id)
            try:
                batch_fee_value = int(batch_fee)
            except ValueError:
                batch_fee_value = 0
            if not course or not batch_name or not start_date or batch_fee_value < 0:
                flash("Course, batch name, start date and a valid fee are required.", "error")
            else:
                portal_storage.add_batch(course_id, batch_name, start_date, batch_fee_value)
                flash(f"Batch created for {course['name']}.", "success")
            return redirect(url_for("admin_dashboard"))

        if request.form.get("action") == "upload_content":
            batch_id = request.form.get("content_batch_id", "")
            content_type = request.form.get("content_type", "notes")
            title = request.form.get("content_title", "").strip()
            link = request.form.get("content_link", "").strip()
            uploaded_file = request.files.get("content_file")
            batch = next((b for b in portal_storage.get_batches() if b.get("id") == batch_id), None)
            if not batch or content_type not in {"notes", "assessment"} or not title or (not link and not uploaded_file):
                flash("Select a batch, content type, title and file or link.", "error")
            else:
                portal_storage.save_content(batch["course_id"], batch_id, content_type, title, uploaded_file, link)
                flash("Course content uploaded for this batch.", "success")
            return redirect(url_for("admin_dashboard"))

        if request.form.get("action") == "review_submission":
            submission_id = request.form.get("submission_id", "")
            review = request.form.get("teacher_review", "").strip()
            status = request.form.get("review_status", "Reviewed")
            teacher = request.form.get("teacher_name", "Teacher").strip() or "Teacher"
            if submission_id and review:
                portal_storage.add_review(submission_id, teacher, review, status)
                flash("Teacher review saved.", "success")
            else:
                flash("A review is required.", "error")
            return redirect(url_for("admin_dashboard"))

        errors = []
        student_name = request.form.get("student_name", "").strip()
        course_id = request.form.get("course_id", "")
        aadhar_number = request.form.get("aadhar_number", "").strip()
        college_name = request.form.get("college_name", "").strip()
        mobile_number = request.form.get("mobile_number", "").strip()
        address = request.form.get("address", "").strip()
        placement_details = request.form.get("placement_details", "").strip()
        batch_id = request.form.get("batch_id", "")
        course_fee = request.form.get("course_fee", "").strip()
        course_fee_value = 0
        payment_method = request.form.get("payment_method", "Cash").strip()
        transaction_id = request.form.get("transaction_id", "").strip()

        course = cbi.get(course_id)
        selected_batch = next((b for b in portal_storage.get_batches() if b["id"] == batch_id), None)
        if not student_name:
            errors.append("Student name is required.")
        if not course:
            errors.append("Please select a valid course.")
        if batch_id and not selected_batch:
            errors.append("Please select a valid batch.")
        if not AADHAR_RE.match(aadhar_number):
            errors.append("Aadhar number must be exactly 12 digits.")
        if not MOBILE_RE.match(mobile_number):
            errors.append("Mobile number must be exactly 10 digits.")
        if not college_name:
            errors.append("College name is required.")
        if not address:
            errors.append("Address is required.")
        try:
            course_fee_value = int(course_fee)
            if course_fee_value < 0:
                raise ValueError
        except ValueError:
            errors.append("Course fee must be a valid non-negative number.")
        # If payment is not cash, require a transaction id
        if payment_method.lower() != "cash" and not transaction_id:
            errors.append("Transaction ID is required for non-cash payments.")

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            sheets_helper.add_admission(
                {
                    "student_name": student_name,
                    "course_name": course["name"] if course else "",
                    "course_fees": course_fee_value,
                    "batch_id": batch_id,
                    "batch_name": selected_batch["name"] if selected_batch else "",
                    "aadhar_number": aadhar_number,
                    "college_name": college_name,
                    "mobile_number": mobile_number,
                    "address": address,
                    "placement_details": placement_details,
                    "payment_method": payment_method,
                    "transaction_id": transaction_id,
                }
            )
            flash(f"Admission saved for {student_name}.", "success")
            return redirect(url_for("admin_dashboard"))

    recent = sheets_helper.get_recent_admissions(limit=25)
    submissions = portal_storage.get_submissions()
    for submission in submissions:
        submission["reviews"] = portal_storage.get_reviews(submission.get("submission_id"))
    return render_template(
        "admin_dashboard.html",
        institute=config.INSTITUTE,
        courses=config.COURSES,
        batches=portal_storage.get_batches(),
        submissions=submissions,
        content=portal_storage.get_all_content(),
        recent=recent,
        using_sheets=sheets_helper.is_using_google_sheets(),
    )


# ---------------------------------------------------------------------------
# Student — course notes, backed by Google Drive folder links
# ---------------------------------------------------------------------------
@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        email = (request.form.get("email", "") or "").strip().lower()
        password = request.form.get("password", "")
        if auth_helper.authenticate(email, password):
            user = auth_helper.get_user(email)
            if not user:
                flash("Account not found.", "error")
            else:
                user_name = str(user.get("name", ""))
                if not sheets_helper.is_name_admitted(user_name):
                    flash("Your name is not found in admissions — contact the institute.", "error")
                else:
                    session["student_email"] = email
                    return redirect(url_for("student_portal"))
        flash("Incorrect email or password.", "error")
    return render_template("student_login.html", institute=config.INSTITUTE)


@app.route("/student/logout")
def student_logout():
    session.pop("student_email", None)
    return redirect(url_for("student_login"))


@app.route("/student")
def student_portal():
    if not session.get("student_email"):
        return redirect(url_for("student_login"))
    student_email = session.get("student_email")
    student = auth_helper.get_user(student_email) if isinstance(student_email, str) else None
    if not student:
        session.pop("student_email", None)
        return redirect(url_for("student_login"))
    if not sheets_helper.is_name_admitted(student.get("name", "")):
        session.pop("student_email", None)
        flash("Your name is not listed in admissions — access denied.", "error")
        return redirect(url_for("student_login"))
    enrollment = student_enrollment(student)
    if not enrollment:
        flash("Your admission is not assigned to an active course batch yet. Contact admin.", "error")
        return render_template("student.html", institute=config.INSTITUTE, courses=[], student=student, enrollment=None, submissions=[])
    student = {**student, "batch_id": enrollment["batch"]["id"], "batch_name": enrollment["batch"]["name"]}
    course = {**enrollment["course"], "drive_link": config.DRIVE_NOTES_LINKS.get(enrollment["course"]["id"], "#")}
    submissions = [
        submission for submission in portal_storage.get_submissions(student.get("email"))
        if submission.get("course_id") == course["id"] and submission.get("batch_id") == student["batch_id"]
    ]
    for submission in submissions:
        submission["reviews"] = portal_storage.get_reviews(submission.get("submission_id"))
    return render_template(
        "student.html",
        institute=config.INSTITUTE,
        courses=[course],
        student=student,
        enrollment=enrollment,
        content=portal_storage.get_content(course["id"], student["batch_id"]),
        submissions=submissions,
    )


@app.route("/student/work", methods=["POST"])
def student_work():
    if not session.get("student_email"):
        return redirect(url_for("student_login"))
    student = auth_helper.get_user(session["student_email"])
    enrollment = student_enrollment(student) if student else None
    uploaded_file = request.files.get("work_file")
    course_id = request.form.get("course_id", "")
    title = request.form.get("title", "").strip()
    if not student or not enrollment or course_id != enrollment["course"]["id"] or not title or not uploaded_file or not uploaded_file.filename:
        flash("You can upload work only for your enrolled course and batch.", "error")
    else:
        scoped_student = {**student, "batch_id": enrollment["batch"]["id"], "batch_name": enrollment["batch"]["name"]}
        portal_storage.save_submission(scoped_student, course_id, title, uploaded_file)
        flash("Your work was uploaded successfully.", "success")
    return redirect(url_for("student_portal"))


@app.route("/admin/work/<path:stored_name>")
@admin_required
def admin_work_download(stored_name):
    path = portal_storage.submission_path(stored_name)
    if not path:
        return "File not found", 404
    return send_file(path, as_attachment=True)


@app.route("/student/content/<path:relative_path>")
def student_content_download(relative_path):
    student_email = session.get("student_email")
    student = auth_helper.get_user(student_email) if isinstance(student_email, str) else None
    enrollment = student_enrollment(student) if student else None
    allowed = portal_storage.get_content(enrollment["course"]["id"], enrollment["batch"]["id"]) if enrollment else []
    if not any(item.get("relative_path") == relative_path for item in allowed):
        return "Access denied", 403
    path = portal_storage.content_path(relative_path)
    return send_file(path, as_attachment=True) if path else ("File not found", 404)


@app.route("/student/submission/<submission_id>/<path:relative_path>")
def student_submission_download(submission_id, relative_path):
    student_email = session.get("student_email")
    submissions = portal_storage.get_submissions(student_email) if isinstance(student_email, str) else []
    submission = next((s for s in submissions if s.get("submission_id") == submission_id), None)
    student = auth_helper.get_user(student_email) if isinstance(student_email, str) else None
    enrollment = student_enrollment(student) if student else None
    if (
        not submission
        or not enrollment
        or submission.get("course_id") != enrollment["course"]["id"]
        or submission.get("batch_id") != enrollment["batch"]["id"]
        or submission.get("relative_path") != relative_path
    ):
        return "Access denied", 403
    path = portal_storage.submission_path(relative_path)
    return send_file(path, as_attachment=True) if path else ("File not found", 404)


# ---------------------- AI Interview Platform -----------------------------
@app.route("/ai/interview", methods=["GET", "POST"])
def ai_interview():
    # Legacy entry — redirect to consolidated `/interview` flow.
    return redirect(url_for("interview"))


# New consolidated interview entry point
@app.route('/interview/select', endpoint='ai_live_select')
def ai_live_select():
    return render_template('ai_live_select.html', institute=config.INSTITUTE, courses=config.COURSES)


@app.route('/interview', methods=['GET', 'POST'])
def interview():
    if request.method == 'POST':
        # optional resume upload and interview params
        course_name = request.form.get('course_name') or request.form.get('role') or 'candidate'
        role = request.form.get('role') or 'candidate'
        level = request.form.get('level', 'junior')
        count = int(request.form.get('count', 5))

        resume_text = ''
        if 'resume' in request.files:
            f = request.files['resume']
            if f and f.filename:
                filename = secure_filename(f.filename)
                fd, path = tempfile.mkstemp(suffix='-'+filename)
                with os.fdopen(fd, 'wb') as out:
                    out.write(f.read())
                # try to extract text from common resume formats
                try:
                    from pypdf import PdfReader
                    try:
                        reader = PdfReader(path)
                        pages = [p.extract_text() or '' for p in reader.pages]
                        resume_text = '\n'.join(pages)
                    except Exception:
                        resume_text = ''
                except Exception:
                    try:
                        from docx import Document
                        doc = Document(path)
                        resume_text = '\n'.join(p.text for p in doc.paragraphs)
                    except Exception:
                        try:
                            with open(path, 'r', encoding='utf-8') as t:
                                resume_text = t.read()
                        except Exception:
                            resume_text = ''

        # create interview session using engine (uses Gemini)
        engine_session = interview_engine.create_session(role=role, level=level, count=count, resume_text=resume_text)
        # initialize speech session
        try:
            speech_service.create_session(engine_session.session_id)
        except Exception:
            pass

        questions_for_frontend = [q.get('question') if isinstance(q, dict) else q for q in engine_session.questions]

        session['interview'] = {
            'session_id': engine_session.session_id,
            'role': role,
            'course_name': course_name,
            'level': level,
            'questions': questions_for_frontend,
            'started_at': int(time.time()),
            'duration_seconds': 3600,
        }
        return redirect(url_for('interview_room'))

    # show simple start page (reuse live select UI)
    return render_template('ai_live_select.html', institute=config.INSTITUTE, courses=config.COURSES)


@app.route('/interview/room')
def interview_room():
    it = session.get('interview')
    if not it:
        return redirect(url_for('interview'))
    # Ensure started_at is set
    if not it.get('started_at'):
        it['started_at'] = int(time.time())
        session['interview'] = it
    return render_template('ai_live_room.html', institute=config.INSTITUTE, interview=it)


@app.route('/interview/finish', methods=['POST'])
def interview_finish():
    # Accept either JSON body or multipart with 'payload' (json) and 'audio' file
    audio_file = None
    payload = None
    if request.content_type and request.content_type.startswith('multipart/'):
        # multipart form
        if 'payload' in request.files:
            try:
                payload = json.loads(request.files['payload'].read())
            except Exception:
                payload = {}
        else:
            try:
                payload = json.loads(request.form.get('payload') or '{}')
            except Exception:
                payload = {}

        audio_file = request.files.get('audio')
    else:
        payload = request.get_json() or {}

    questions = payload.get('questions', [])
    answers = payload.get('answers', [])

    interview_session = session.get('interview') or {}
    session_id = interview_session.get('session_id')

    report = None

    # If audio was uploaded, save and attempt Drive upload
    if audio_file and audio_file.filename:
        filename = secure_filename(audio_file.filename)
        fd, path = tempfile.mkstemp(suffix='-'+filename)
        with os.fdopen(fd, 'wb') as out:
            out.write(audio_file.read())
        try:
            uploaded = drive_helper.upload_recording(path, filename)
        except Exception:
            uploaded = {"success": False, "path": path}
        # store a transcript entry pointing to the recording path/id
        try:
            speech_service.add_transcript(session_id or 'local', 'recording_saved', str(uploaded.get('path')))
        except Exception:
            pass

    if session_id:
        for ans in answers:
            try:
                speech_service.add_transcript(session_id, 'candidate', ans)
            except Exception:
                pass
            interview_engine.submit_answer(session_id, ans)

        report = interview_engine.generate_report(session_id)
        interview_engine.delete_session(session_id)
        try:
            speech_service.delete_session(session_id)
        except Exception:
            pass
    else:
        report = ai_helper.evaluate_answers(questions, answers)

    if not report:
        report = [
            {
                "question": "Interview report unavailable",
                "answer": "",
                "score": 0,
                "feedback": "The interview service did not return a report. Please try again.",
            }
        ]

    session.pop('interview', None)
    return render_template('ai_report.html', institute=config.INSTITUTE, report=report)


@app.route("/student/register", methods=["GET", "POST"])
def student_register():
    if request.method == "POST":
        name = (request.form.get("name", "") or "").strip()
        email = (request.form.get("email", "") or "").strip().lower()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        errors = []
        if not name:
            errors.append("Name is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if not password:
            errors.append("Password is required.")
        if password != password_confirm:
            errors.append("Passwords do not match.")
        if auth_helper.user_exists(email):
            errors.append("An account with that email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            # Only allow registration if the student's name exists in admissions
            if not sheets_helper.is_name_admitted(name):
                flash("Cannot create account: your name is not found in admissions. Contact admin.", "error")
                return render_template("student_register.html", institute=config.INSTITUTE)
            auth_helper.add_user(email, name, password)
            session["student_email"] = email
            flash("Account created — you are now signed in.", "success")
            return redirect(url_for("student_portal"))

    return render_template("student_register.html", institute=config.INSTITUTE)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
