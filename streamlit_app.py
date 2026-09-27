import re

import streamlit as st

import auth_helper
import config
import portal_storage
import sheets_helper

st.set_page_config(page_title="Engineering Design Studio", page_icon="🏫", layout="wide")

AADHAR_RE = re.compile(r"^\d{12}$")
MOBILE_RE = re.compile(r"^\d{10}$")


def _course_by_name(name):
    target = (name or "").strip().lower()
    return next((c for c in config.COURSES if c["name"].strip().lower() == target), None)


def _student_enrollment(student_name):
    record = sheets_helper.get_admission_for_name(student_name or "")
    if not record:
        return None
    course = _course_by_name(record.get("Course Name", ""))
    batches = portal_storage.get_batches()
    batch_id = str(record.get("Batch ID", ""))
    batch_name = str(record.get("Batch Name", ""))
    batch = next((b for b in batches if b.get("id") == batch_id), None)
    if not batch and batch_name:
        batch = next((b for b in batches if b.get("name", "").strip().lower() == batch_name.strip().lower()), None)
    if not course or not batch or batch.get("course_id") != course.get("id"):
        return None
    return {"course": course, "batch": batch, "admission": record}


def _faq_answer(question):
    q = (question or "").strip().lower()
    if not q:
        return config.FAQ_FALLBACK

    best_answer = None
    best_score = 0
    for pair in config.FAQ_PAIRS:
        score = sum(len(kw.strip()) for kw in pair["keywords"] if kw.strip() in q)
        if score > best_score:
            best_score = score
            best_answer = pair["answer"]
    return best_answer or config.FAQ_FALLBACK


def render_home():
    st.title(config.INSTITUTE["name"])
    st.caption(config.INSTITUTE["tagline"])

    st.write(config.INSTITUTE["address"])
    st.write(f"Phone: {config.INSTITUTE['phone']} | Email: {config.INSTITUTE['email']} | Hours: {config.INSTITUTE['hours']}")

    for note in config.NOTIFICATIONS:
        st.info(note)

    st.subheader("Courses")
    for track_name in ["Mechanical Design", "IT & Software", "Civil Design", "Electrical Design"]:
        track_courses = [c for c in config.COURSES if c["track"] == track_name]
        if not track_courses:
            continue
        st.markdown(f"### {track_name}")
        cols = st.columns(3)
        for idx, course in enumerate(track_courses):
            with cols[idx % 3]:
                st.markdown(f"**{course['name']}**")
                st.write(f"Duration: {course['duration']}")
                st.write(f"Fee: ₹{course['fee']}")
                drive_url = config.DRIVE_NOTES_LINKS.get(course["id"], "#")
                st.markdown(f"[Open Drive]({drive_url})")

    st.markdown("---")
    st.subheader("Quick FAQ")
    with st.form("faq_form"):
        faq_question = st.text_input("Ask a question", placeholder="examples: fee, python, placement, address")
        submitted = st.form_submit_button("Ask")
    if submitted:
        st.success(_faq_answer(faq_question))


def render_admin_login():
    if st.session_state.get("admin_logged_in"):
        render_admin_dashboard()
        return

    st.subheader("Admin Login")
    with st.form("admin_login_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if config.ADMIN_PASSWORD and password == config.ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
        elif not config.ADMIN_PASSWORD:
            st.error("Admin login is not configured. Set EDS_ADMIN_PASSWORD in the environment.")
        else:
            st.error("Incorrect admin password.")


def render_admin_dashboard():
    st.subheader("Admin Dashboard")
    if st.button("Logout"):
        st.session_state.admin_logged_in = False
        st.rerun()

    batches = portal_storage.get_batches()
    recent = sheets_helper.get_recent_admissions(limit=20)
    submissions = portal_storage.get_submissions()
    for submission in submissions:
        submission["reviews"] = portal_storage.get_reviews(submission.get("submission_id"))

    st.markdown("### 1) Create Batch")
    with st.form("batch_form"):
        course_id = st.selectbox("Course", [c["id"] for c in config.COURSES], format_func=lambda cid: next(c["name"] for c in config.COURSES if c["id"] == cid))
        batch_name = st.text_input("Batch Name")
        start_date = st.date_input("Start Date")
        fee = st.number_input("Fee", min_value=0, step=1)
        batch_submitted = st.form_submit_button("Create Batch")

    if batch_submitted and batch_name:
        portal_storage.add_batch(course_id, batch_name, str(start_date), int(fee))
        st.success(f"Batch created for {course_id}.")
        st.rerun()

    st.markdown("### 2) Upload Course Content")
    if batches:
        with st.form("content_form"):
            batch = st.selectbox("Batch", batches, format_func=lambda b: f"{b['name']} — {b['course_id']}")
            content_type = st.selectbox("Type", ["notes", "assessment"])
            title = st.text_input("Title")
            link = st.text_input("External Link")
            uploaded_file = st.file_uploader("File Upload")
            content_submitted = st.form_submit_button("Publish Content")

        if content_submitted:
            if title and (link or uploaded_file):
                portal_storage.save_content(batch["course_id"], batch["id"], content_type, title, uploaded_file, link)
                st.success("Content published.")
            else:
                st.warning("Title and either a file or link are required.")
    else:
        st.info("Create a batch before uploading content.")

    st.markdown("### 3) Add Admission")
    with st.form("admission_form"):
        student_name = st.text_input("Student Name")
        course_id = st.selectbox("Course", [c["id"] for c in config.COURSES], index=0, key="adm_course_id", format_func=lambda cid: next(c["name"] for c in config.COURSES if c["id"] == cid))
        batch_id = st.selectbox("Batch", [b["id"] for b in batches], format_func=lambda b_id: next((b["name"] for b in batches if b["id"] == b_id), b_id), key="adm_batch_id") if batches else st.text_input("Batch ID")
        aadhar_number = st.text_input("Aadhar Number")
        college_name = st.text_input("College Name")
        mobile_number = st.text_input("Mobile Number")
        address = st.text_area("Address")
        placement_details = st.text_area("Placement Details")
        course_fee = st.number_input("Course Fee", min_value=0, step=1)
        payment_method = st.selectbox("Payment Method", ["Cash", "UPI", "Bank Transfer", "Card"])
        transaction_id = st.text_input("Transaction ID")
        admission_submitted = st.form_submit_button("Save Admission")

    if admission_submitted:
        errors = []
        if not student_name:
            errors.append("Student name is required.")
        if not AADHAR_RE.match(aadhar_number or ""):
            errors.append("Aadhar number must be exactly 12 digits.")
        if not MOBILE_RE.match(mobile_number or ""):
            errors.append("Mobile number must be exactly 10 digits.")
        if not college_name:
            errors.append("College name is required.")
        if not address:
            errors.append("Address is required.")
        if payment_method.lower() != "cash" and not transaction_id:
            errors.append("Transaction ID is required for non-cash payments.")
        if errors:
            for err in errors:
                st.error(err)
        else:
            selected_batch = next((b for b in batches if b["id"] == batch_id), None)
            course = next((c for c in config.COURSES if c["id"] == course_id), None)
            sheets_helper.add_admission({
                "student_name": student_name,
                "course_name": course["name"] if course else "",
                "course_fees": int(course_fee),
                "batch_id": batch_id,
                "batch_name": selected_batch["name"] if selected_batch else "",
                "aadhar_number": aadhar_number,
                "college_name": college_name,
                "mobile_number": mobile_number,
                "address": address,
                "placement_details": placement_details,
                "payment_method": payment_method,
                "transaction_id": transaction_id,
            })
            st.success(f"Admission saved for {student_name}.")
            st.rerun()

    st.markdown("### 4) Recent Admissions")
    if recent:
        st.dataframe(recent, use_container_width=True)
    else:
        st.info("No admissions recorded yet.")

    st.markdown("### 5) Teacher Reviews")
    if submissions:
        with st.form("review_form"):
            submission_items = [f"{item['student_name']} — {item['title']} ({item['submission_id']})" for item in submissions]
            submission = st.selectbox("Submission", submission_items)
            selected = next(item for item in submissions if f"{item['student_name']} — {item['title']} ({item['submission_id']})" == submission)
            teacher_name = st.text_input("Teacher Name", value="Teacher")
            review_status = st.selectbox("Status", ["Reviewed", "Needs Revision", "Approved"])
            teacher_review = st.text_area("Review")
            review_submitted = st.form_submit_button("Save Review")

        if review_submitted:
            if teacher_review.strip():
                portal_storage.add_review(selected["submission_id"], teacher_name, teacher_review, review_status)
                st.success("Review saved.")
            else:
                st.warning("A review is required.")

        for item in submissions:
            reviews = portal_storage.get_reviews(item.get("submission_id"))
            if reviews:
                st.markdown(f"#### {item['student_name']} — {item['title']}")
                for review in reviews:
                    st.write(f"- {review.get('teacher')} [{review.get('status')}] {review.get('reviewed_at')}: {review.get('review')}")
    else:
        st.info("No student submissions available for review yet.")

    st.markdown("### 6) Created Batches")
    if batches:
        st.dataframe(batches, use_container_width=True)
    else:
        st.info("No batches created yet.")


def render_student_login():
    if st.session_state.get("student_logged_in"):
        render_student_portal()
        return

    st.subheader("Student Login")
    with st.form("student_login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if auth_helper.authenticate(email, password):
            user = auth_helper.get_user(email)
            student_name = str(user.get("name", "")) if user else ""
            if not student_name or not sheets_helper.is_name_admitted(student_name):
                st.error("Your name is not found in admissions — contact the institute.")
            else:
                st.session_state.student_logged_in = True
                st.session_state.student_email = email
                st.session_state.student_name = student_name
                st.rerun()
        else:
            st.error("Incorrect email or password.")

    st.markdown("---")
    st.subheader("Student Registration")
    with st.form("student_register_form"):
        name = st.text_input("Full Name")
        reg_email = st.text_input("Email")
        reg_password = st.text_input("Password", type="password")
        reg_password_confirm = st.text_input("Confirm Password", type="password")
        reg_submitted = st.form_submit_button("Register")

    if reg_submitted:
        if not name:
            st.error("Name is required.")
        elif not reg_email or "@" not in reg_email:
            st.error("A valid email is required.")
        elif not reg_password:
            st.error("Password is required.")
        elif reg_password != reg_password_confirm:
            st.error("Passwords do not match.")
        elif auth_helper.user_exists(reg_email):
            st.error("An account with that email already exists.")
        elif not sheets_helper.is_name_admitted(name):
            st.error("Cannot create account: your name is not found in admissions. Contact admin.")
        else:
            auth_helper.add_user(reg_email, name, reg_password)
            st.session_state.student_logged_in = True
            st.session_state.student_email = reg_email
            st.session_state.student_name = name
            st.success("Account created — you are now signed in.")
            st.rerun()


def render_student_portal():
    st.subheader("Student Portal")
    if st.button("Logout"):
        st.session_state.student_logged_in = False
        st.session_state.student_email = ""
        st.session_state.student_name = ""
        st.rerun()

    student_email = st.session_state.get("student_email", "")
    student = auth_helper.get_user(student_email) if student_email else None
    if not student:
        st.warning("Please log in again.")
        return

    student_name = str(student.get("name", ""))
    if not sheets_helper.is_name_admitted(student_name):
        st.warning("Your name is not listed in admissions — access denied.")
        return

    enrollment = _student_enrollment(student_name)
    if not enrollment:
        st.warning("Your admission is not assigned to an active course batch yet. Contact admin.")
        return

    course = enrollment["course"]
    batch = enrollment["batch"]
    st.success(f"Welcome {student_name} — {course['name']}")
    st.markdown(f"[Open Course Drive Folder]({config.DRIVE_NOTES_LINKS.get(course['id'], '#')})")

    st.markdown("### Upload Your Work")
    with st.form("student_work_form"):
        title = st.text_input("Assignment / Project Title")
        uploaded_file = st.file_uploader("Upload File")
        submitted = st.form_submit_button("Submit Work")
    if submitted and title and uploaded_file:
        portal_storage.save_submission({
            "name": student_name,
            "email": student_email,
            "batch_id": batch["id"],
            "batch_name": batch["name"],
        }, course["id"], title, uploaded_file)
        st.success("Your work was uploaded successfully.")

    content_items = portal_storage.get_content(course["id"], batch["id"])
    if content_items:
        st.markdown("### Course Notes & Assessments")
        for item in content_items:
            label = f"{item['type'].title()} — {item['title']}"
            if item.get("link"):
                st.markdown(f"- [{label}]({item['link']})")
            elif item.get("relative_path"):
                st.markdown(f"- {label} — {item['relative_path']}")
            else:
                st.markdown(f"- {label}")
    else:
        st.info("No notes or assessments have been published for this batch yet.")

    st.markdown("### My Submitted Work")
    work_items = portal_storage.get_submissions(student_email)
    work_items = [item for item in work_items if item.get("course_id") == course["id"] and item.get("batch_id") == batch["id"]]
    if work_items:
        for item in work_items:
            reviews = portal_storage.get_reviews(item.get("submission_id"))
            st.markdown(f"- **{item['title']}**")
            if reviews:
                for r in reviews:
                    st.write(f"  - {r.get('teacher')} [{r.get('status')}] : {r.get('review')}")
            else:
                st.write("  - No review yet")
    else:
        st.info("No submissions yet.")


def render_ai_interview():
    st.subheader("AI Interview")
    st.info("The Streamlit version keeps the same interview flow, with session-led interview prompts and reporting in the app UI.")
    st.markdown("This feature remains available in the same user workflow as the Flask version.")


pages = {
    "Home": render_home,
    "Admin": render_admin_login,
    "Student": render_student_login,
    "AI Interview": render_ai_interview,
}

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
if "student_email" not in st.session_state:
    st.session_state.student_email = ""
if "student_name" not in st.session_state:
    st.session_state.student_name = ""

st.sidebar.title("Navigation")
choice = st.sidebar.radio("Go to", list(pages.keys()))
pages[choice]()
