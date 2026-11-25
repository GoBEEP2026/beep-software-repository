import json
import tempfile
import unittest
from pathlib import Path

from validate_reference_audit import (
    AUDIT_DESCRIPTION,
    AUDIT_STATUS,
    CURRENT_SCHEMA_VERSION,
    GOVERNANCE_AUTHORITY,
    REPOSITORY_NAME,
    validate_audit,
    validate_live_audit_data,
)


class TestReferenceApprovalAudit(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(self.temp_dir.cleanup)

        self.audit_path = (
            Path(self.temp_dir.name) / "audit.json"
        )

        self.audit = {
            "audit_schema_version": CURRENT_SCHEMA_VERSION,
            "repository": REPOSITORY_NAME,
            "audit_status": AUDIT_STATUS,
            "description": AUDIT_DESCRIPTION,
            "records": [],
        }

        self.assert_valid_fixture()

    def save_audit(self):

        self.audit_path.write_text(
            json.dumps(self.audit, indent=2),
            encoding="utf-8",
        )

    def valid_record(self):

        return {
            "record_id": "TEST-AUDIT-001",
            "reference_home_id": "BEEP-HOME-001",
            "reference_home_version": "1.0.0",
            "decision": "APPROVED",
            "reviewer": "Test Technical Reviewer",
            "approval_authority": GOVERNANCE_AUTHORITY,
            "evidence": "TEST-EVIDENCE-001",
            "pull_request": "TEST-PR-001",
            "decision_date": "2026-11-18",
            "board_resolution_reference": "TEST-BOARD-RES-001",
            "technical_review_record": "BEEP-REVIEW-TEST-001",
            "technical_review_date": "2026-11-15",
            "technical_review_sha256": "a" * 64,
            "reviewed_content_sha256": "b" * 64,
        }

    def assert_valid_fixture(self):

        self.assertEqual(
            validate_live_audit_data(self.audit),
            [],
            "Invalid audit test fixture",
        )

    def add_valid_record(self):

        record = self.valid_record()

        self.audit["records"].append(record)

        self.assert_valid_fixture()

        return record

    def validate(self):

        self.save_audit()

        return validate_audit(self.audit_path)

    def test_empty_development_audit_passes(self):

        self.assertEqual(
            self.validate(),
            [],
        )

    def test_valid_record_passes(self):

        self.add_valid_record()

        self.assertEqual(
            self.validate(),
            [],
        )

    def test_duplicate_record_id_rejected(self):

        record = self.add_valid_record()

        self.audit["records"].append(
            record.copy()
        )

        self.assertEqual(
            self.validate(),
            [
                "Record 2: Duplicate record ID"
            ],
        )

    def test_invalid_decision_rejected(self):

        record = self.add_valid_record()

        record["decision"] = "PENDING"

        self.assertEqual(
            self.validate(),
            [
                "Record 1: Invalid decision"
            ],
        )

    def test_missing_approval_authority_rejected(self):

        record = self.add_valid_record()

        record["approval_authority"] = ""

        self.assertEqual(
            self.validate(),
            [
                "Record 1: Invalid approval authority"
            ],
        )

    def test_invalid_date_rejected(self):

        record = self.add_valid_record()

        record["decision_date"] = "2026-99-99"

        self.assertEqual(
            self.validate(),
            [
                "Record 1: Invalid decision date"
            ],
        )

    def test_missing_board_resolution_rejected(self):

        record = self.add_valid_record()

        del record["board_resolution_reference"]

        self.assertEqual(
            self.validate(),
            [
                "Record 1: Missing board_resolution_reference"
            ],
        )

    def test_empty_board_resolution_rejected(self):

        record = self.add_valid_record()

        record["board_resolution_reference"] = ""

        self.assertEqual(
            self.validate(),
            [
                "Record 1: Missing or invalid "
                "board_resolution_reference"
            ],
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
