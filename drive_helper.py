import io
import os
import re

import config


def extract_drive_folder_id(url):
    """Return the Google Drive folder ID from a standard Drive URL."""
    if not url:
        return ""
    patterns = [
        r"/drive/folders/([A-Za-z0-9_-]+)",
        r"/folders/([A-Za-z0-9_-]+)",
        r"[?&]id=([A-Za-z0-9_-]+)",
        r"/file/d/([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def build_batch_folder_name(course_name, batch_name):
    """Create a readable folder name for a batch under a course folder."""
    course_label = (course_name or "Course").strip()
    batch_label = (batch_name or "Batch").strip()
    if not course_label:
        return batch_label
    if not batch_label:
        return course_label
    return f"{course_label} - {batch_label}"


def get_course_drive_folder_url(course_id):
    return config.DRIVE_NOTES_LINKS.get(course_id, "")


def ensure_batch_drive_folder(course_id, batch_name, batch_id, course_name=None):
    """Create (or reuse) a batch subfolder inside the configured course folder."""
    parent_url = get_course_drive_folder_url(course_id)
    parent_id = extract_drive_folder_id(parent_url)
    if not parent_url or not parent_id:
        return {"success": False, "folder_id": "", "webViewLink": "", "message": "No Drive folder configured for this course."}

    creds_file = os.path.abspath(config.GOOGLE_CREDENTIALS_FILE or "")
    if not os.path.exists(creds_file):
        return {"success": False, "folder_id": "", "webViewLink": "", "message": "Google Drive credentials are not configured."}

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        folder_name = build_batch_folder_name(course_name or course_id, batch_name)
        safe_name = folder_name.replace("'", "\\'")
        query = (
            f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' "
            f"and trashed=false and name = '{safe_name}'"
        )
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id,name,webViewLink)",
            pageSize=10,
        ).execute()
        items = response.get("files") or []
        if items:
            folder = items[0]
            return {
                "success": True,
                "folder_id": folder.get("id", ""),
                "webViewLink": folder.get("webViewLink", ""),
                "name": folder_name,
            }

        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = service.files().create(body=file_metadata, fields="id,name,webViewLink").execute()
        return {
            "success": True,
            "folder_id": folder.get("id", ""),
            "webViewLink": folder.get("webViewLink", ""),
            "name": folder_name,
        }
    except Exception as exc:
        return {
            "success": False,
            "folder_id": "",
            "webViewLink": "",
            "name": build_batch_folder_name(course_name or course_id, batch_name),
            "error": str(exc),
        }


def _save_locally(src_path, filename):
    out_dir = os.path.join(os.path.dirname(__file__), "recordings")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, filename)
    try:
        # prefer moving if same filesystem else copy
        from shutil import copyfile

        copyfile(src_path, dst)
    except Exception:
        try:
            with open(src_path, "rb") as r, open(dst, "wb") as w:
                w.write(r.read())
        except Exception:
            return None
    return dst


def upload_recording(local_path, filename):
    """Upload recording to Google Drive when configured, otherwise save locally.

    Returns a dict with keys: `success` (bool), `path` (local path or drive file id),
    and `error` (optional).
    """
    # If Drive config not set or credentials missing, fall back to local save.
    creds_file = os.path.abspath(config.GOOGLE_CREDENTIALS_FILE or "")
    folder_id = config.DRIVE_INTERVIEW_FOLDER_ID or ""

    if not folder_id or not os.path.exists(creds_file):
        saved = _save_locally(local_path, filename)
        return {"success": bool(saved), "path": saved or local_path}

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        service = build("drive", "v3", credentials=creds, cache_discovery=False)

        media = MediaFileUpload(local_path, mimetype="audio/webm")
        file_metadata = {"name": filename, "parents": [folder_id]}
        f = service.files().create(body=file_metadata, media_body=media, fields="id,name").execute()
        return {"success": True, "path": f.get("id")}
    except Exception as exc:
        # on failure, save locally
        saved = _save_locally(local_path, filename)
        return {"success": False, "path": saved or local_path, "error": str(exc)}
