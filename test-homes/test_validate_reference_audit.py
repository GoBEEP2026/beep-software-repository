import json
import tempfile
import unittest
from pathlib import Path

from validate_reference_audit import validate_audit


class TestReferenceApprovalAudit(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.audit_path = (
            Path(self.temp_dir.name) / "audit.json"
        )

        self.audit = {
            "audit_schema_version": "1.0.0",
            "repository": "BEEP Software Consistency Repository",
            "audit_status": "DEVELOPMENT",
            "records": []
        }

    def save_audit(self):
        self.audit_path.write_text(
            json.dumps(self.audit, indent=2),
            encoding="utf-8"
        )

    
    def valid_record(self):
        return {
            "record_id": "TEST-AUDIT-001",
            "reference_home_id": "BEEP-HOME-001",
            "reference_home_version": "1.0.0",
            "decision": "APPROVED",
            "reviewer": "Test Technical Reviewer",
            "approval_authority": "Test Approval Authority",
            "evidence": "TEST-EVIDENCE-001",
            "pull_request": "TEST-PR-001",
            "decision_date": "2026-11-18",
            "board_resolution_reference": "TEST-BOARD-RES-001"
        }


    def test_empty_development_audit_passes(self):
        self.save_audit()

        self.assertEqual(
            validate_audit(self.audit_path),
            []
        )

    def test_valid_record_passes(self):
        self.audit["records"].append(
            self.valid_record()
        )

        self.save_audit()

        self.assertEqual(
            validate_audit(self.audit_path),
            []
        )

    def test_duplicate_record_id_rejected(self):
        record = self.valid_record()

        self.audit["records"] = [
            record,
            record.copy()
        ]

        self.save_audit()

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any("Duplicate record ID" in e for e in errors)
        )

    def test_invalid_decision_rejected(self):
        record = self.valid_record()
        record["decision"] = "PENDING"

        self.audit["records"].append(record)
        self.save_audit()

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any("Invalid decision" in e for e in errors)
        )

    def test_missing_approval_authority_rejected(self):
        record = self.valid_record()
        record["approval_authority"] = ""

        self.audit["records"].append(record)
        self.save_audit()

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any("Missing approval_authority" in e for e in errors)
        )

    def test_invalid_date_rejected(self):
        record = self.valid_record()
        record["decision_date"] = "2026-99-99"

        self.audit["records"].append(record)
        self.save_audit()

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any("Invalid decision date" in e for e in errors)
        )

    def test_missing_board_resolution_rejected(self):
        record = self.valid_record()
        del record["board_resolution_reference"]

        self.audit["records"].append(record)
        self.save_audit()

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any(
                "Missing board_resolution_reference" in e
                for e in errors
            )
        )

    def test_empty_board_resolution_rejected(self):
        record = self.valid_record()
        record["board_resolution_reference"] = ""

        self.audit["records"].append(record)
        self.save_audit()

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any(
                "Missing board_resolution_reference" in e
                for e in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
