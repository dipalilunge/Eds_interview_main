import unittest

import app as app_module
from career_interview import Interview, Subject, db


class CareerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_career_page_is_linked_and_serves_its_assets(self):
        home = self.client.get("/")
        career_page = self.client.get("/career/")

        self.assertEqual(home.status_code, 200)
        self.assertIn(b'Career', home.data)
        self.assertEqual(career_page.status_code, 200)
        self.assertNotIn(b'Teacher Dashboard', career_page.data)
        self.assertNotIn(b'Recruiter', career_page.data)
        for field_name in (b'name="year"', b'name="college"', b'name="contact"'):
            self.assertIn(field_name, career_page.data)
            self.assertLess(career_page.data.index(field_name), career_page.data.index(b"60 min"))
        asset = self.client.get("/career/static/style.css")
        self.assertEqual(asset.status_code, 200)
        asset.close()

    def test_staff_routes_require_admin_login(self):
        for path in (
            "/career/teacher",
            "/career/recruiter",
            "/career/admin/questions",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/admin/login", response.headers["Location"])

    def test_interview_form_saves_college_year_and_contact(self):
        with app_module.app.app_context():
            subject = Subject.query.filter_by(name="Python").first()
            subject_id = subject.id

        invalid_response = self.client.post("/career/interview/start", data={
            "student_name": "Career Test Student",
            "subject_id": str(subject_id),
            "year": "3rd Year",
            "college": "Example College",
            "contact": "not-a-number",
        })
        self.assertEqual(invalid_response.status_code, 400)

        response = self.client.post("/career/interview/start", data={
            "student_name": "Career Test Student",
            "subject_id": str(subject_id),
            "year": "3rd Year",
            "college": "Example College",
            "contact": "9876543210",
        })

        self.assertEqual(response.status_code, 302)
        with app_module.app.app_context():
            interview = Interview.query.filter_by(student_name="Career Test Student").order_by(Interview.id.desc()).first()
            self.assertIsNotNone(interview)
            self.assertEqual(interview.year, "3rd Year")
            self.assertEqual(interview.college, "Example College")
            self.assertEqual(interview.contact, "9876543210")
            db.session.delete(interview)
            db.session.commit()

    def test_admin_can_open_career_staff_tools(self):
        with self.client.session_transaction() as user_session:
            user_session["is_admin"] = True

        for path in (
            "/career/teacher",
            "/career/recruiter",
            "/career/admin/questions",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)


if __name__ == "__main__":
    unittest.main()