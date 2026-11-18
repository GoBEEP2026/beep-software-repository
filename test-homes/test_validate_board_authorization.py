import tempfile
import unittest
from pathlib import Path

from validate_board_authorization import validate_board_authorization


class TestBoardAuthorization(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.record_path = (
            Path(self.temp_dir.name) / "approval-record.md"
        )

        self.valid_record = (
            "# B.E.E.P. Test Approval Record\n\n"
            "- Approval Authority: B.E.E.P. Board of Directors\n"
            "- Board Resolution Reference: TEST-RES-001\n"
            "- Board Decision Date: 2026-11-18\n"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def validate_content(self, content):
        self.record_path.write_text(
            content,
            encoding="utf-8",
        )
        return validate_board_authorization(self.record_path)

    def test_valid_board_authorization_passes(self):
        errors = self.validate_content(self.valid_record)
        self.assertEqual(errors, [])

    def test_missing_approval_authority_fails(self):
        content = self.valid_record.replace(
            "- Approval Authority: B.E.E.P. Board of Directors\n",
            "",
        )
        errors = self.validate_content(content)
        self.assertTrue(errors)

    def test_incorrect_approval_authority_fails(self):
        content = self.valid_record.replace(
            "B.E.E.P. Board of Directors",
            "Technical Reviewer",
        )
        errors = self.validate_content(content)
        self.assertTrue(errors)

    def test_missing_board_resolution_fails(self):
        content = self.valid_record.replace(
            "- Board Resolution Reference: TEST-RES-001\n",
            "",
        )
        errors = self.validate_content(content)
        self.assertTrue(errors)

    def test_pending_board_resolution_fails(self):
        content = self.valid_record.replace(
            "TEST-RES-001",
            "Pending",
        )
        errors = self.validate_content(content)
        self.assertTrue(errors)

    def test_missing_board_decision_date_fails(self):
        content = self.valid_record.replace(
            "- Board Decision Date: 2026-11-18\n",
            "",
        )
        errors = self.validate_content(content)
        self.assertTrue(errors)

    def test_invalid_board_decision_date_fails(self):
        content = self.valid_record.replace(
            "2026-11-18",
            "11/18/2026",
        )
        errors = self.validate_content(content)
        self.assertTrue(errors)

    def test_invalid_calendar_date_fails(self):
        content = self.valid_record.replace(
            "2026-11-18",
            "2026-02-30",
        )
        errors = self.validate_content(content)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
