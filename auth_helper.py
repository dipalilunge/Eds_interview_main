import os
import json
from werkzeug.security import generate_password_hash, check_password_hash


USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")


def _read_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_users(data):
    directory = os.path.dirname(USERS_FILE)
    temporary_file = USERS_FILE + ".tmp"
    with open(temporary_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temporary_file, USERS_FILE)


def user_exists(email: str) -> bool:
    users = _read_users()
    return email.lower() in users


def add_user(email: str, name: str, password: str) -> None:
    users = _read_users()
    users[email.lower()] = {
        "email": email.lower(),
        "name": name,
        "pw_hash": generate_password_hash(password),
    }
    _write_users(users)


def authenticate(email: str, password: str) -> bool:
    users = _read_users()
    user = users.get(email.lower())
    if not user:
        return False
    return check_password_hash(user.get("pw_hash", ""), password)


def get_user(email: str):
    users = _read_users()
    return users.get(email.lower())
