import unittest
from unittest.mock import Mock, patch

import gemini_service


class GeminiServiceTests(unittest.TestCase):
    def test_call_gemini_reads_generate_content_payload(self):
        service = gemini_service.GeminiService.__new__(gemini_service.GeminiService)
        service.api_key = "test-key"
        service.model = "models/gemini-2.5-flash"
        service.base_url = "https://generativelanguage.googleapis.com/v1beta"

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": '[{"id": 1, "type": "technical", "question": "Explain REST"}]'}]
                    }
                }
            ]
        }

        with patch("gemini_service.requests.post", return_value=response):
            text = service._call_gemini("hello")

        self.assertEqual(text, '[{"id": 1, "type": "technical", "question": "Explain REST"}]')


if __name__ == "__main__":
    unittest.main()
