import unittest

from flask import session

import app as app_module


class InterviewFlowTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.client.testing = True

    def test_interview_start_sets_questions_in_session(self):
        response = self.client.post(
            '/interview',
            data={'course_name': 'Python Programming', 'level': 'junior', 'count': '3'},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            interview = sess['interview']
        self.assertIn('questions', interview)
        self.assertGreaterEqual(len(interview['questions']), 1)
        self.assertEqual(interview['course_name'], 'Python Programming')


if __name__ == '__main__':
    unittest.main()
