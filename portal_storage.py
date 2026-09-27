import json
import os
import uuid
from datetime import datetime

from werkzeug.utils import secure_filename

import drive_helper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BATCHES_FILE = os.path.join(BASE_DIR, "batches.json")
WORK_DIR = os.path.join(BASE_DIR, "student_work")
WORK_INDEX_FILE = os.path.join(WORK_DIR, "submissions.json")
CONTENT_DIR = os.path.join(BASE_DIR, "course_content")
CONTENT_INDEX_FILE = os.path.join(CONTENT_DIR, "content.json")
REVIEW_INDEX_FILE = os.path.join(WORK_DIR, "reviews.json")


def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)


def get_batches():
    return _read_json(BATCHES_FILE, [])


def add_batch(course_id, name, start_date, fee):
    batches = get_batches()
    batch = {
        "id": uuid.uuid4().hex[:10],
        "course_id": course_id,
        "name": name,
        "start_date": start_date,
        "fee": fee,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    course_name = next((course["name"] for course in __import__("config").COURSES if course["id"] == course_id), course_id)
    drive_details = drive_helper.ensure_batch_drive_folder(course_id, name, batch["id"], course_name)
    if drive_details.get("success"):
        batch["drive_folder_id"] = drive_details.get("folder_id", "")
        batch["drive_folder_url"] = drive_details.get("webViewLink", "")
        batch["drive_folder_name"] = drive_details.get("name", "")
    batches.append(batch)
    _write_json(BATCHES_FILE, batches)
    return batch


def save_submission(student, course_id, title, uploaded_file):
    filename = secure_filename(uploaded_file.filename or "work")
    extension = os.path.splitext(filename)[1]
    stored_name = f"{uuid.uuid4().hex}{extension}"
    course_id = secure_filename(course_id)
    batch_id = secure_filename(student.get("batch_id", "unassigned"))
    student_folder = secure_filename(student.get("name", "student")) or "student"
    relative_folder = os.path.join(course_id, batch_id, student_folder)
    output_folder = os.path.join(WORK_DIR, relative_folder)
    os.makedirs(output_folder, exist_ok=True)
    relative_path = "/".join((course_id, batch_id, student_folder, stored_name))
    uploaded_file.save(os.path.join(WORK_DIR, *relative_path.split("/")))

    submissions = _read_json(WORK_INDEX_FILE, [])
    submission = {
        "submission_id": uuid.uuid4().hex[:12],
        "student_name": student.get("name", ""),
        "student_email": student.get("email", ""),
        "course_id": course_id,
        "batch_id": student.get("batch_id", ""),
        "batch_name": student.get("batch_name", ""),
        "title": title,
        "filename": filename,
        "stored_name": stored_name,
        "relative_path": relative_path,
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    submissions.append(submission)
    _write_json(WORK_INDEX_FILE, submissions)
    return submission


def get_submissions(student_email=None):
    submissions = _read_json(WORK_INDEX_FILE, [])
    if student_email:
        submissions = [s for s in submissions if s.get("student_email") == student_email]
    return list(reversed(submissions))


def submission_path(stored_name):
    return _safe_file_path(WORK_DIR, stored_name)


def save_content(course_id, batch_id, content_type, title, uploaded_file=None, link=""):
    content_id = uuid.uuid4().hex[:12]
    course_folder = secure_filename(course_id)
    batch_folder = secure_filename(batch_id)
    relative_path = ""
    if uploaded_file and uploaded_file.filename:
        filename = secure_filename(uploaded_file.filename)
        relative_path = "/".join((course_folder, batch_folder, "content", f"{content_id}-{filename}"))
        output_path = os.path.join(CONTENT_DIR, *relative_path.split("/"))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        uploaded_file.save(output_path)
    contents = _read_json(CONTENT_INDEX_FILE, [])
    item = {
        "id": content_id,
        "course_id": course_id,
        "batch_id": batch_id,
        "type": content_type,
        "title": title,
        "link": link,
        "relative_path": relative_path,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    contents.append(item)
    os.makedirs(CONTENT_DIR, exist_ok=True)
    _write_json(CONTENT_INDEX_FILE, contents)
    return item


def get_content(course_id, batch_id):
    return [
        item for item in _read_json(CONTENT_INDEX_FILE, [])
        if item.get("course_id") == course_id and item.get("batch_id") == batch_id
    ]


def get_all_content():
    return list(reversed(_read_json(CONTENT_INDEX_FILE, [])))


def content_path(relative_path):
    return _safe_file_path(CONTENT_DIR, relative_path)


def _safe_file_path(root, relative_path):
    candidate = os.path.abspath(os.path.join(root, *relative_path.replace("\\", "/").split("/")))
    root = os.path.abspath(root)
    return candidate if candidate.startswith(root + os.sep) and os.path.isfile(candidate) else None


def add_review(submission_id, teacher, review, status):
    reviews = _read_json(REVIEW_INDEX_FILE, [])
    entry = {
        "submission_id": submission_id,
        "teacher": teacher,
        "review": review,
        "status": status,
        "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    reviews.append(entry)
    os.makedirs(WORK_DIR, exist_ok=True)
    _write_json(REVIEW_INDEX_FILE, reviews)
    return entry


def get_reviews(submission_id=None):
    reviews = _read_json(REVIEW_INDEX_FILE, [])
    if submission_id:
        reviews = [r for r in reviews if r.get("submission_id") == submission_id]
    return reviews
