import importlib
import json
import os
import unittest


class StreamlitFreeDeployConfigTests(unittest.TestCase):
    def test_default_admin_password_is_configured(self):
        os.environ.pop("EDS_ADMIN_PASSWORD", None)

        import config
        importlib.reload(config)

        self.assertEqual(config.ADMIN_PASSWORD, "Eds_2026@admin")

    def test_env_overrides_support_streamlit_secret_mode(self):
        os.environ["EDS_ADMIN_PASSWORD"] = "streamlit-admin"
        os.environ["EDS_STUDENT_PASSWORD"] = "streamlit-student"
        os.environ["EDS_ADMISSIONS_SHEET_ID"] = "sheet-123"
        os.environ["EDS_GOOGLE_CREDENTIALS_JSON"] = json.dumps({
            "type": "service_account",
            "project_id": "demo-project",
        })

        import config
        importlib.reload(config)

        self.assertEqual(config.ADMIN_PASSWORD, "streamlit-admin")
        self.assertEqual(config.STUDENT_PASSWORD, "streamlit-student")
        self.assertEqual(config.ADMISSIONS_SHEET_ID, "sheet-123")
        self.assertIn("service_account", config.GOOGLE_CREDENTIALS_JSON)


if __name__ == "__main__":
    unittest.main()
