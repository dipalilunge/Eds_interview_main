"""
Thin wrapper around gspread for writing admission records to Google Sheets.

If credentials or a sheet ID aren't configured yet, every function falls
back to appending rows to a local CSV file (config.LOCAL_ADMISSIONS_FALLBACK)
so the admin form keeps working during setup and demos.
"""

import csv
import os
from datetime import datetime

import config

FIELDNAMES = [
    "Timestamp",
    "Student Name",
    "Course Name",
    "Course Fees",
    "Aadhar Number",
    "College Name",
    "Mobile Number",
    "Address",
    "Placement Details",
    "Payment Method",
    "Transaction ID",
    "Batch Name",
    "Batch ID",
]

_sheet_cache = None
_sheets_available = None


def _try_connect():
    """Attempt to open the configured Google Sheet. Returns worksheet or None."""
    global _sheet_cache, _sheets_available
    if _sheet_cache is not None:
        return _sheet_cache
    if _sheets_available is False:
        return None

    creds_path = config.GOOGLE_CREDENTIALS_FILE or ""
    if not config.ADMISSIONS_SHEET_ID or (not creds_path or not os.path.exists(creds_path)):
        _sheets_available = False
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            config.GOOGLE_CREDENTIALS_FILE, scopes=scopes
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(config.ADMISSIONS_SHEET_ID)
        try:
            worksheet = spreadsheet.worksheet(config.ADMISSIONS_WORKSHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=config.ADMISSIONS_WORKSHEET_NAME, rows=1000, cols=len(FIELDNAMES)
            )
            worksheet.append_row(FIELDNAMES)

        # Make sure header row exists.
        if worksheet.row_values(1) != FIELDNAMES:
            worksheet.update("A1", [FIELDNAMES])

        _sheet_cache = worksheet
        _sheets_available = True
        return worksheet
    except Exception as exc:  # noqa: BLE001 - surface any auth/setup issue as a fallback
        print(f"[sheets_helper] Falling back to local CSV — Google Sheets unavailable: {exc}")
        _sheets_available = False
        return None


def is_using_google_sheets() -> bool:
    return _try_connect() is not None


def _local_csv_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), config.LOCAL_ADMISSIONS_FALLBACK)


def _append_local(row: dict):
    path = _local_csv_path()
    write_header = not os.path.exists(path)
    if not write_header:
        with open(path, newline="", encoding="utf-8") as f:
            existing_rows = list(csv.DictReader(f))
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(existing_rows)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def add_admission(record: dict):
    """
    record keys: student_name, course_name, course_fees, aadhar_number,
    college_name, mobile_number, address, placement_details
    """
    row = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Student Name": record.get("student_name", ""),
        "Course Name": record.get("course_name", ""),
        "Course Fees": record.get("course_fees", ""),
        "Aadhar Number": record.get("aadhar_number", ""),
        "College Name": record.get("college_name", ""),
        "Mobile Number": record.get("mobile_number", ""),
        "Address": record.get("address", ""),
        "Placement Details": record.get("placement_details", ""),
        "Payment Method": record.get("payment_method", "Cash"),
        "Transaction ID": record.get("transaction_id", ""),
        "Batch Name": record.get("batch_name", ""),
        "Batch ID": record.get("batch_id", ""),
    }

    worksheet = _try_connect()
    if worksheet is not None:
        worksheet.append_row([row[f] for f in FIELDNAMES])
    else:
        _append_local(row)

    return row


def get_recent_admissions(limit: int = 20):
    """Return the most recent admissions (newest first) from whichever store is active."""
    worksheet = _try_connect()
    if worksheet is not None:
        records = worksheet.get_all_records()
        return list(reversed(records))[:limit]

    path = _local_csv_path()
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return list(reversed(rows))[:limit]


def is_name_admitted(name: str) -> bool:
    """Return True if `name` (case-insensitive) appears in the admissions records."""
    if not name:
        return False
    worksheet = _try_connect()
    target = name.strip().lower()
    if worksheet is not None:
        records = worksheet.get_all_records()
        for r in records:
            if str(r.get("Student Name", "")).strip().lower() == target:
                return True
        return False

    # local CSV fallback
    path = _local_csv_path()
    if not os.path.exists(path):
        return False
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if str(row.get("Student Name", "")).strip().lower() == target:
                return True
    return False


def get_admission_for_name(name: str):
    """Return the latest admission record for a student name."""
    if not name:
        return None
    target = name.strip().lower()
    worksheet = _try_connect()
    if worksheet is not None:
        records = list(reversed(worksheet.get_all_records()))
    else:
        path = _local_csv_path()
        if not os.path.exists(path):
            return None
        with open(path, newline="", encoding="utf-8") as f:
            records = list(reversed(list(csv.DictReader(f))))
    return next(
        (r for r in records if str(r.get("Student Name", "")).strip().lower() == target),
        None,
    )
