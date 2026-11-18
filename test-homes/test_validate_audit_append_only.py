import json
import tempfile
import unittest
from pathlib import Path

from validate_audit_append_only import validate_append_only


class TestAuditAppendOnly(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

        self.previous_path = self.folder / "previous.json"
        self.current_path = self.folder / "current.json"

        self.original_record = {
            "record_id": "TEST-001",
            "reference_home_id": "BEEP-HOME-001",
            "reference_home_version": "1.0.0",
            "decision": "APPROVED",
            "reviewer": "Test Reviewer",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_histories(self, previous_records, current_records):
        self.previous_path.write_text(
            json.dumps({"records": previous_records}, indent=2),
            encoding="utf-8",
        )

        self.current_path.write_text(
            json.dumps({"records": current_records}, indent=2),
            encoding="utf-8",
        )

        return validate_append_only(
            self.previous_path,
            self.current_path,
        )

    def test_unchanged_history_passes(self):
        errors = self.write_histories(
            [self.original_record],
            [self.original_record],
        )
        self.assertEqual(errors, [])

    def test_appending_record_passes(self):
        new_record = {
            **self.original_record,
            "record_id": "TEST-002",
        }

        errors = self.write_histories(
            [self.original_record],
            [self.original_record, new_record],
        )
        self.assertEqual(errors, [])

    def test_modifying_record_fails(self):
        modified = {
            **self.original_record,
            "decision": "REJECTED",
        }

        errors = self.write_histories(
            [self.original_record],
            [modified],
        )
        self.assertTrue(errors)

    def test_deleting_record_fails(self):
        errors = self.write_histories(
            [self.original_record],
            [],
        )
        self.assertTrue(errors)

    def test_reordering_records_fails(self):
        second_record = {
            **self.original_record,
            "record_id": "TEST-002",
        }

        errors = self.write_histories(
            [self.original_record, second_record],
            [second_record, self.original_record],
        )
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
