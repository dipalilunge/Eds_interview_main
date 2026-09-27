# Engineering Design Studio — web app

A Flask + HTML/CSS site for the institute, with:

- **Homepage** — notifications ticker, courses (IT/software + mechanical CAD tracks), placement stats, address/contact with an embedded map, and a static keyword-based FAQ assistant (no external AI API — just a chat widget answering from `config.FAQ_PAIRS`).
- **Admin dashboard** (`/admin`) — password-protected form to record admissions (student name, course, fee, Aadhar number, college, mobile, address, placement details), written straight to a Google Sheet. Falls back to a local CSV automatically if Sheets isn't configured yet, so it's usable immediately.
- **Student portal** (`/student`) — password-protected page listing every course with a button that opens that course's Google Drive notes folder in a new tab.
- **Career practice** (`/career/`) — subject-based mock interviews with optional resume skill matching, camera and microphone recording, and interview results.
- Career evaluation, recruiter tools, and question-bank management are available only to administrators from `/admin`; these staff pages redirect other visitors to admin login.

## 1. Run it locally

```bash
cd eds_app
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`.

Set an admin password with `EDS_ADMIN_PASSWORD` before using the admin dashboard. Student access uses registered student accounts; do not share or commit passwords.

Without any Google setup, admin submissions save to `admissions_local.csv` in the project folder, and student notes links show `#` placeholders. Everything else works out of the box.

## 2. Connect Google Sheets (admissions)

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project (or reuse one) and enable the **Google Sheets API** and **Google Drive API**.
2. Create a **Service Account**, then create a JSON key for it and download it.
3. Save that file as `google_credentials.json` inside the `eds_app` folder (same level as `app.py`). Keep it private — never commit it to a public repo.
4. Create a Google Sheet for admissions. Share it with the service account's email address (found inside the JSON file, looks like `xxxx@xxxx.iam.gserviceaccount.com`) with **Editor** access.
5. Copy the Sheet ID from its URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_PART_IS_THE_ID`**`/edit`
6. Open `config.py` and set:
   ```python
   ADMISSIONS_SHEET_ID = "paste-the-id-here"
   ```
7. Restart the app. The admin dashboard header will show "Synced to Google Sheets" once it connects successfully; if credentials are missing or wrong it silently falls back to the local CSV and prints a note in the terminal.

## 3. Connect Google Drive (course notes)

1. Create one Drive folder per course (Python, SQL, C++, Java, Data Science, Data Analytics, AI, CATIA, Creo, SolidWorks, AutoCAD).
2. Set each folder's sharing to **"Anyone with the link — Viewer"** (or share individually with students, if you'd rather keep them private).
3. Copy each folder's link and paste it into `config.py` inside `DRIVE_NOTES_LINKS`, matching the course `id` keys already listed there.

## 4. Configure passwords and secret key

Set these as environment variables before running in anything other than a local demo:

```bash
export EDS_SECRET_KEY="a-long-random-string"
export EDS_ADMIN_PASSWORD="something-only-staff-know"
export EDS_STUDENT_PASSWORD="something-shared-with-enrolled-students"
```

The application generates a temporary random session key if `EDS_SECRET_KEY` is unset, which invalidates sessions after a restart. Set all three environment variables for stable use. Admin login stays disabled until `EDS_ADMIN_PASSWORD` is configured.

## 5. Edit institute details, courses and FAQ answers

All editable content — address, phone, email, hours, course list, fees, placement stats, notification banner text, and FAQ answers — lives in `config.py`. No template or Python logic needs to change to update any of it.

## 6. Deploying

For real use, run behind a production WSGI server (e.g. `gunicorn app:app`) rather than `python app.py`, put it behind HTTPS, and set the environment variables from step 4. Consider giving each course batch its own student password if you want tighter access control.

### Deploy on Render

1. Push this folder to GitHub and create a new **Blueprint** in Render, selecting the repository. Render will read `render.yaml` and create the web service.
2. In the service environment, enter values for `EDS_ADMIN_PASSWORD`, `EDS_STUDENT_PASSWORD`, and `EDS_ADMISSIONS_SHEET_ID`.
3. Set `EDS_GOOGLE_CREDENTIALS_JSON` to the complete contents of the Google service-account JSON key. Do not commit the key file.
4. Deploy. Render provides the `PORT` value automatically, and the configured Gunicorn command binds to it.

The default Render filesystem is ephemeral. Google Sheets remains the admissions source, but locally stored users, batches, course uploads, interview recordings, and fallback CSV data can disappear on redeploy. Use a Render persistent disk or move that storage to a database/object store before relying on it for production records.

Career interview metadata is stored in `career_interview.db`; uploaded resumes and recordings are stored in `career_resumes/` and `career_recordings/`. Set `EDS_CAREER_DATABASE_URL` to use another SQLAlchemy database URL. These local files also require persistent storage in production.

## Project structure

```
eds_app/
  app.py                  Flask routes
  config.py                All editable content & settings
  sheets_helper.py         Google Sheets read/write with local CSV fallback
  requirements.txt
  templates/
    base.html
    index.html             Homepage
    admin_login.html
    admin_dashboard.html
    student_login.html
    student.html
    partials/gear.svg
  static/
    css/style.css
    js/main.js
    js/faq.js
    images/logo.jpg
```
