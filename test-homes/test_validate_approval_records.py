import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parent
    / "validate_approval_records.py"
)

spec = importlib.util.spec_from_file_location(
    "validate_approval_records",
    MODULE_PATH
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

validate_approval_records = module.validate_approval_records


class TestApprovalRecords(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

        self.registry_path = (
            self.folder / "reference-home-registry.json"
        )

        self.approvals_directory = self.folder / "approvals"

        self.home = {
            "test_home_id": "BEEP-HOME-001",
            "test_home_version": "1.0.0",
            "status": "APPROVED",
            "approval": {
                "approved_by": "Test Approval Authority",
                "approval_date": "2026-11-17",
                "approval_record": "TEST-APPROVAL-001"
            }
        }

        self.record_path = (
            self.approvals_directory
            / "BEEP-HOME-001"
            / "1.0.0"
            / "approval-record.md"
        )

        self.record_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.record_path.write_text(
            self.valid_record(),
            encoding="utf-8"
        )

        self.save_registry()

    def tearDown(self):
        self.temp_dir.cleanup()

    def valid_record(self):
        return (
            "# B.E.E.P. Approval Record\n\n"
            "Reference Home ID: BEEP-HOME-001\n"
            "Reference Home Version: 1.0.0\n"
            "Approval Record ID: TEST-APPROVAL-001\n"
            "Approval Status: APPROVED\n"
        )

    def save_registry(self):
        registry = {
            "registry_version": "1.1.0",
            "registry_status": "APPROVED",
            "reference_homes": [self.home]
        }

        self.registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8"
        )

    def validate(self):
        self.save_registry()

        return validate_approval_records(
            registry_path=self.registry_path,
            approvals_directory=self.approvals_directory
        )

    def test_valid_approval_document(self):
        self.assertEqual(self.validate(), [])

    def test_missing_approval_document_rejected(self):
        self.record_path.unlink()

        errors = self.validate()

        self.assertTrue(
            any("Missing approval document" in e for e in errors)
        )

    def test_mismatched_approval_record_id_rejected(self):
        self.home["approval"]["approval_record"] = (
            "DIFFERENT-APPROVAL-ID"
        )

        errors = self.validate()

        self.assertTrue(
            any("mismatched Approval Record ID" in e for e in errors)
        )

    def test_mismatched_reference_home_version_rejected(self):
        self.home["test_home_version"] = "2.0.0"

        errors = self.validate()

        self.assertTrue(
            any("Missing approval document" in e for e in errors)
        )

    def test_not_approved_document_rejected(self):
        self.record_path.write_text(
            self.valid_record().replace(
                "Approval Status: APPROVED",
                "Approval Status: NOT APPROVED"
            ),
            encoding="utf-8"
        )

        errors = self.validate()

        self.assertTrue(
            any("marked NOT APPROVED" in e for e in errors)
        )

    def test_missing_approval_decision_rejected(self):
        self.record_path.write_text(
            self.valid_record().replace(
                "Approval Status: APPROVED\n",
                ""
            ),
            encoding="utf-8"
        )

        errors = self.validate()

        self.assertTrue(
            any(
                "must explicitly state APPROVED" in e
                for e in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
