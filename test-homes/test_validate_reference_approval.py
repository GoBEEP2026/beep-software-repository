import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import sys

TEST_HOME_DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_HOME_DIRECTORY))


MODULE_PATH = (
    Path(__file__).resolve().parent
    / "validate_reference_approval.py"
)

spec = importlib.util.spec_from_file_location(
    "validate_reference_approval",
    MODULE_PATH
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

validate_reference_approval = module.validate_reference_approval


class TestReferenceApproval(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)
        self.registry_path = (
            self.folder / "reference-home-registry.json"
        )

        self.audit_path = (
            self.folder / "reference-approval-audit.json"
        )

        self.audit = {
            "audit_schema_version": "1.0.0",
            "repository": "BEEP Software Consistency Repository",
            "audit_status": "DEVELOPMENT",
            "records": [],
        }

        self.save_audit()

        self.home = {
            "test_home_id": "BEEP-HOME-001",
            "test_home_version": "1.0.0",
            "status": "DEVELOPMENT",
            "reference_files": [
                {
                    "filename": "sample-home.xml",
                    "sha256": "a" * 64
                }
            ],
            "test_cycles": [],
            "approval": {
                "approved_by": None,
                "approval_date": None,
                "approval_record": None
            }
        }

        self.save_registry()

    def tearDown(self):
        self.temp_dir.cleanup()

    def save_audit(self):
        self.audit_path.write_text(
            json.dumps(self.audit, indent=2),
            encoding="utf-8",
        )

    def save_registry(self):
        registry = {
            "registry_version": "1.1.0",
            "registry_status": "DEVELOPMENT",
            "reference_homes": [self.home]
        }

        self.registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8"
        )

   
    def validate(self):
        self.save_registry()
        self.save_audit()

        return validate_reference_approval(
            self.registry_path,
            audit_path=self.audit_path,
        )


    
    def approve_home(self):
        self.home["status"] = "APPROVED"
        self.home["approval"] = {
            "approved_by": "B.E.E.P. Board of Directors",
            "approval_date": "2026-11-17",
            "approval_record": "BEEP-APPROVAL-001",
            "board_resolution_reference": "TEST-BOARD-RES-001"
        }
        self.home["test_cycles"] = ["2027-Q1"]


    def test_development_home_passes(self):
        self.assertEqual(self.validate(), [])

    def test_under_review_requires_metadata(self):
        self.home["status"] = "UNDER_REVIEW"

        errors = self.validate()

        self.assertTrue(
            any("Missing review metadata" in e for e in errors)
        )

    def test_under_review_valid_metadata(self):
        self.home["status"] = "UNDER_REVIEW"
        self.home["review"] = {
            "reviewer": "Independent Technical Reviewer",
            "review_record": "BEEP-REVIEW-001"
        }

        self.assertEqual(self.validate(), [])

   
    def test_approved_home_without_audit_is_rejected(self):
        self.approve_home()

        errors = self.validate()

        self.assertTrue(
            any(
                "No matching APPROVED audit decision" in error
                for error in errors
            )
        )


    def test_missing_approval_authority_rejected(self):
        self.approve_home()
        self.home["approval"]["approved_by"] = None

        errors = self.validate()

        self.assertTrue(
            any("Missing approval authority" in e for e in errors)
        )

    def test_invalid_approval_date_rejected(self):
        self.approve_home()
        self.home["approval"]["approval_date"] = "INVALID"

        errors = self.validate()

        self.assertTrue(
            any("Invalid approval date" in e for e in errors)
        )

    def test_missing_test_cycle_rejected(self):
        self.approve_home()
        self.home["test_cycles"] = []

        errors = self.validate()

        self.assertTrue(
            any("No assigned test cycles" in e for e in errors)
        )

   
    def test_approved_home_requires_matching_audit(self):
        validate_approval_audit_matches = (
            module.validate_approval_audit_matches
        )

        registry = {

            "reference_homes": [
                {
                    "test_home_id": "BEEP-TEST-001",
                    "test_home_version": "1.0.0",
                    "status": "APPROVED",
                    "approval": {
                        "approved_by": "Test Approval Authority",
                        "approval_date": "2026-11-18",
                        "approval_record": "TEST-001",
                    },
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.json"

            audit_path.write_text(
                json.dumps(
                    {
                        "audit_schema_version": "1.0.0",
                        "audit_status": "DEVELOPMENT",
                        "records": [],
                    }
                ),
                encoding="utf-8",
            )

            errors = validate_approval_audit_matches(
                registry,
                audit_path=audit_path,
            )

        self.assertTrue(
            any(
                "No matching APPROVED audit decision" in error
                for error in errors
            )
        )

    def test_approved_home_accepts_matching_audit(self):
        registry = {
            "reference_homes": [
                {
                    "test_home_id": "BEEP-TEST-001",
                    "test_home_version": "1.0.0",
                    "status": "APPROVED",
                    "approval": {
                        "approved_by": "Test Approval Authority",
                        "approval_date": "2026-11-18",
                        "approval_record": "TEST-001",
                    },
                }
            ]
        }

        audit = {
            "audit_schema_version": "1.0.0",
            "audit_status": "DEVELOPMENT",
            "records": [
                {
                    "record_id": "TEST-001",
                    "reference_home_id": "BEEP-TEST-001",
                    "reference_home_version": "1.0.0",
                    "decision": "APPROVED",
                    "reviewer": "Test Technical Reviewer",
                    "approval_authority": "Test Approval Authority",
                    "evidence": "TEST-EVIDENCE-001",
                    "pull_request": "TEST-PR-001",
                    "decision_date": "2026-11-18",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.json"

            audit_path.write_text(
                json.dumps(audit, indent=2),
                encoding="utf-8",
            )

            errors = module.validate_approval_audit_matches(
                registry,
                audit_path=audit_path,
            )

        self.assertEqual(errors, [])

    
    def test_mismatched_approval_record_id_rejected(self):
        self.approve_home()

        self.audit["records"] = [
            {
                "record_id": "DIFFERENT-APPROVAL-001",
                "reference_home_id": "BEEP-HOME-001",
                "reference_home_version": "1.0.0",
                "decision": "APPROVED",
                "reviewer": "Test Technical Reviewer",
                "approval_authority": "B.E.E.P. Board of Directors",
                "evidence": "TEST-EVIDENCE-001",
                "pull_request": "TEST-PR-001",
                "decision_date": "2026-11-17",
                "board_resolution_reference": "TEST-BOARD-RES-001"
            }
        ]

        errors = self.validate()

        self.assertTrue(
            any(
                "No matching APPROVED audit decision" in error
                for error in errors
            )
        )


        errors = self.validate()

        self.assertTrue(
            any(
                "No matching APPROVED audit decision" in error
                for error in errors
            )
        )

   
    def test_full_validator_accepts_matching_approval(self):
        self.approve_home()

        self.audit["records"] = [
            {
                "record_id": "BEEP-APPROVAL-001",
                "reference_home_id": "BEEP-HOME-001",
                "reference_home_version": "1.0.0",
                "decision": "APPROVED",
                "reviewer": "Test Technical Reviewer",
                "approval_authority": "B.E.E.P. Board of Directors",
                "evidence": "TEST-EVIDENCE-001",
                "pull_request": "TEST-PR-001",
                "decision_date": "2026-11-17",
                "board_resolution_reference": "TEST-BOARD-RES-001"
            }
        ]

        errors = self.validate()

        self.assertEqual(errors, [])


        errors = self.validate()

        self.assertEqual(errors, [])

    def test_matching_audit_with_missing_reviewer_rejected(self):
        self.approve_home()

        self.audit["records"] = [
            {
                "record_id": "BEEP-APPROVAL-001",
                "reference_home_id": "BEEP-HOME-001",
                "reference_home_version": "1.0.0",
                "decision": "APPROVED",
                "approval_authority": "BEEP Technical Committee",
                "evidence": "TEST-EVIDENCE-001",
                "pull_request": "TEST-PR-001",
                "decision_date": "2026-11-17",
            }
        ]

        errors = self.validate()

        self.assertTrue(
            any(
                "Missing reviewer" in error
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
