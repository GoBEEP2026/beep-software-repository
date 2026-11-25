import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import sys


TEST_HOME_DIRECTORY = Path(__file__).resolve().parent

sys.path.insert(0, str(TEST_HOME_DIRECTORY))


from validate_reference_audit import (
    AUDIT_DESCRIPTION,
    AUDIT_STATUS,
    CURRENT_SCHEMA_VERSION,
    GOVERNANCE_AUTHORITY,
    REPOSITORY_NAME,
    validate_live_audit_data,
)


MODULE_PATH = (
    TEST_HOME_DIRECTORY
    / "validate_reference_approval.py"
)

spec = importlib.util.spec_from_file_location(
    "validate_reference_approval",
    MODULE_PATH,
)

module = importlib.util.module_from_spec(spec)

spec.loader.exec_module(module)

validate_reference_approval = (
    module.validate_reference_approval
)


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

        self.audit = self.make_audit_registry()

        self.home = {
            "test_home_id": "BEEP-HOME-001",
            "test_home_version": "1.0.0",
            "status": "DEVELOPMENT",
            "reference_files": [
                {
                    "filename": "sample-home.xml",
                    "sha256": "a" * 64,
                }
            ],
            "test_cycles": [],
            "approval": {
                "approved_by": None,
                "approval_date": None,
                "approval_record": None,
            },
        }

        self.save_audit()

        self.save_registry()

    def tearDown(self):

        self.temp_dir.cleanup()

    def make_audit_registry(self, records=None):

        return {
            "audit_schema_version": CURRENT_SCHEMA_VERSION,
            "repository": REPOSITORY_NAME,
            "audit_status": AUDIT_STATUS,
            "description": AUDIT_DESCRIPTION,
            "records": [] if records is None else records,
        }

    def make_approval_record(
        self,
        record_id="BEEP-APPROVAL-001",
        home_id="BEEP-HOME-001",
        decision_date="2026-11-17",
        resolution="TEST-BOARD-RES-001",
    ):

        return {
            "record_id": record_id,
            "reference_home_id": home_id,
            "reference_home_version": "1.0.0",
            "decision": "APPROVED",
            "reviewer": "Test Technical Reviewer",
            "approval_authority": GOVERNANCE_AUTHORITY,
            "evidence": "TEST-EVIDENCE-001",
            "pull_request": "TEST-PR-001",
            "decision_date": decision_date,
            "board_resolution_reference": resolution,
            "technical_review_record": "BEEP-REVIEW-TEST-001",
            "technical_review_date": "2026-11-15",
            "technical_review_sha256": "b" * 64,
            "reviewed_content_sha256": "c" * 64,
        }

    def assert_valid_audit(self):

        self.assertEqual(
            validate_live_audit_data(self.audit),
            [],
            "Invalid audit test fixture",
        )

    def save_audit(self):

        self.audit_path.write_text(
            json.dumps(self.audit, indent=2),
            encoding="utf-8",
        )

    def save_registry(self):

        registry = {
            "registry_version": "1.1.0",
            "registry_status": "DEVELOPMENT",
            "reference_homes": [self.home],
        }

        self.registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8",
        )

    def validate(self, require_valid_audit=True):

        if require_valid_audit:

            self.assert_valid_audit()

        self.save_registry()

        self.save_audit()

        return validate_reference_approval(
            self.registry_path,
            audit_path=self.audit_path,
        )

    def approve_home(self):

        self.home["status"] = "APPROVED"

        self.home["approval"] = {
            "approved_by": GOVERNANCE_AUTHORITY,
            "approval_date": "2026-11-17",
            "approval_record": "BEEP-APPROVAL-001",
            "board_resolution_reference": "TEST-BOARD-RES-001",
        }

        self.home["test_cycles"] = ["2027-Q1"]

    def assert_error_contains(self, errors, expected):

        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected {expected!r}; got {errors}",
        )

    def test_development_home_passes(self):

        self.assertEqual(
            self.validate(),
            [],
        )

    def test_under_review_requires_metadata(self):

        self.home["status"] = "UNDER_REVIEW"

        errors = self.validate()

        self.assert_error_contains(
            errors,
            "Missing review metadata",
        )

    def test_under_review_valid_metadata(self):

        self.home["status"] = "UNDER_REVIEW"

        self.home["review"] = {
            "reviewer": "Independent Technical Reviewer",
            "review_record": "BEEP-REVIEW-001",
        }

        self.assertEqual(
            self.validate(),
            [],
        )

    def test_approved_home_without_audit_is_rejected(self):

        self.approve_home()

        errors = self.validate()

        self.assert_error_contains(
            errors,
            "No matching APPROVED audit decision",
        )

    def test_missing_approval_authority_rejected(self):

        self.approve_home()

        self.audit["records"] = [
            self.make_approval_record()
        ]

        self.home["approval"]["approved_by"] = None

        errors = self.validate()

        self.assert_error_contains(
            errors,
            "Missing approval authority",
        )

    def test_invalid_approval_date_rejected(self):

        self.approve_home()

        self.audit["records"] = [
            self.make_approval_record()
        ]

        self.home["approval"]["approval_date"] = "INVALID"

        errors = self.validate()

        self.assert_error_contains(
            errors,
            "Invalid approval date",
        )

    def test_missing_test_cycle_rejected(self):

        self.approve_home()

        self.audit["records"] = [
            self.make_approval_record()
        ]

        self.home["test_cycles"] = []

        errors = self.validate()

        self.assert_error_contains(
            errors,
            "No assigned test cycles",
        )

    def test_approved_home_requires_matching_audit(self):

        registry = {
            "reference_homes": [
                {
                    "test_home_id": "BEEP-TEST-001",
                    "test_home_version": "1.0.0",
                    "status": "APPROVED",
                    "approval": {
                        "approved_by": GOVERNANCE_AUTHORITY,
                        "approval_date": "2026-11-18",
                        "approval_record": "TEST-001",
                        "board_resolution_reference": "TEST-BOARD-RES-001",
                    },
                }
            ]
        }

        self.audit = self.make_audit_registry()

        self.assert_valid_audit()

        self.save_audit()

        errors = module.validate_approval_audit_matches(
            registry,
            audit_path=self.audit_path,
        )

        self.assert_error_contains(
            errors,
            "No matching APPROVED audit decision",
        )

    def test_approved_home_accepts_matching_audit(self):

        registry = {
            "reference_homes": [
                {
                    "test_home_id": "BEEP-TEST-001",
                    "test_home_version": "1.0.0",
                    "status": "APPROVED",
                    "approval": {
                        "approved_by": GOVERNANCE_AUTHORITY,
                        "approval_date": "2026-11-18",
                        "approval_record": "TEST-001",
                        "board_resolution_reference": "TEST-BOARD-RES-001",
                    },
                }
            ]
        }

        self.audit = self.make_audit_registry(
            [
                self.make_approval_record(
                    record_id="TEST-001",
                    home_id="BEEP-TEST-001",
                    decision_date="2026-11-18",
                )
            ]
        )

        self.assert_valid_audit()

        self.save_audit()

        errors = module.validate_approval_audit_matches(
            registry,
            audit_path=self.audit_path,
        )

        self.assertEqual(
            errors,
            [],
        )

    def test_mismatched_approval_record_id_rejected(self):

        self.approve_home()

        self.audit["records"] = [
            self.make_approval_record(
                record_id="DIFFERENT-APPROVAL-001"
            )
        ]

        errors = self.validate()

        self.assert_error_contains(
            errors,
            "No matching APPROVED audit decision",
        )

    def test_full_validator_accepts_matching_approval(self):

        self.approve_home()

        self.audit["records"] = [
            self.make_approval_record()
        ]

        self.assertEqual(
            self.validate(),
            [],
        )

    def test_matching_audit_with_missing_reviewer_rejected(self):

        self.approve_home()

        record = self.make_approval_record()

        self.audit["records"] = [record]

        self.assert_valid_audit()

        del record["reviewer"]

        self.assertEqual(
            validate_live_audit_data(self.audit),
            ["Record 1: Missing reviewer"],
        )

        errors = self.validate(
            require_valid_audit=False
        )

        self.assert_error_contains(
            errors,
            "Missing reviewer",
        )

    def test_mismatched_board_resolution_rejected(self):

        self.approve_home()

        self.audit["records"] = [
            self.make_approval_record(
                resolution="TEST-BOARD-RES-999"
            )
        ]

        errors = self.validate()

        self.assert_error_contains(
            errors,
            "No matching APPROVED audit decision",
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
