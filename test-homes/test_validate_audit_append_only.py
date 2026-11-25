import json
import tempfile
import unittest
from pathlib import Path

from validate_audit_append_only import (
    validate_append_only,
)

from validate_reference_audit import (
    AUDIT_DESCRIPTION,
    AUDIT_STATUS,
    GOVERNANCE_AUTHORITY,
    LEGACY_SCHEMA_VERSION,
    REPOSITORY_NAME,
    validate_audit_data,
)


class TestAuditAppendOnly(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.folder = Path(self.temp_dir.name)

        self.previous_path = (
            self.folder / "previous.json"
        )

        self.current_path = (
            self.folder / "current.json"
        )

        self.original_record = {
            "record_id": "TEST-001",
            "reference_home_id": "BEEP-HOME-001",
            "reference_home_version": "1.0.0",
            "decision": "APPROVED",
            "reviewer": "Fictional Test Reviewer",
            "approval_authority": GOVERNANCE_AUTHORITY,
            "evidence": "Fictional supporting evidence",
            "pull_request": "TEST-PR-001",
            "board_resolution_reference": "BEEP-RES-TEST-001",
            "decision_date": "2026-01-25",
        }

    def tearDown(self):

        self.temp_dir.cleanup()

    def make_registry(self, records):

        return {
            "audit_schema_version": LEGACY_SCHEMA_VERSION,
            "repository": REPOSITORY_NAME,
            "audit_status": AUDIT_STATUS,
            "description": AUDIT_DESCRIPTION,
            "records": records,
        }

    def write_histories(
        self,
        previous_records,
        current_records,
    ):

        previous = self.make_registry(
            previous_records
        )

        current = self.make_registry(
            current_records
        )

        # Confirm both test fixtures are valid
        # before testing historical protection.

        self.assertEqual(
            validate_audit_data(previous),
            [],
            "Invalid historical audit test fixture",
        )

        self.assertEqual(
            validate_audit_data(current),
            [],
            "Invalid current audit test fixture",
        )

        self.previous_path.write_text(
            json.dumps(previous, indent=2),
            encoding="utf-8",
        )

        self.current_path.write_text(
            json.dumps(current, indent=2),
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

        self.assertEqual(
            errors,
            [
                "Audit record 1 "
                "was modified or reordered"
            ],
        )

    def test_deleting_record_fails(self):

        errors = self.write_histories(
            [self.original_record],
            [],
        )

        self.assertEqual(
            errors,
            [
                "Audit history cannot "
                "remove existing records"
            ],
        )

    def test_reordering_records_fails(self):

        second_record = {
            **self.original_record,
            "record_id": "TEST-002",
        }

        errors = self.write_histories(
            [self.original_record, second_record],
            [second_record, self.original_record],
        )

        self.assertEqual(
            errors,
            [
                "Audit record 1 "
                "was modified or reordered",
                "Audit record 2 "
                "was modified or reordered",
            ],
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
