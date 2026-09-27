import unittest

import drive_helper


class DriveBatchLinksTests(unittest.TestCase):
    def test_extract_drive_folder_id_handles_google_drive_links(self):
        self.assertEqual(
            drive_helper.extract_drive_folder_id("https://drive.google.com/drive/folders/abc123"),
            "abc123",
        )
        self.assertEqual(
            drive_helper.extract_drive_folder_id("https://drive.google.com/open?id=xyz987"),
            "xyz987",
        )

    def test_build_batch_folder_name(self):
        self.assertEqual(
            drive_helper.build_batch_folder_name("AutoCAD", "Batch A"),
            "AutoCAD - Batch A",
        )


if __name__ == "__main__":
    unittest.main()
