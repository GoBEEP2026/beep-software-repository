import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_technical_review import (
    calculate_technical_fingerprint,
)

from validate_review_approval_chronology import (
    validate_review_approval_chronology,
    validate_registry_approval_chronology,
)


class TestReviewApprovalChronology(unittest.TestCase):

    def setUp(self):
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp_directory.cleanup
        )

        self.registry_path = (
            Path(self.temp_directory.name)
            / "registry.json"
        )

    def make_home(
        self,
        status="APPROVED",
        review_date="2026-11-24",
        approval_date="2026-11-25",
        home_id="BEEP-HOME-TEST",
        version="1.0.0",
    ):
        home = {
            "test_home_id": home_id,
            "test_home_version": version,
            "status": status,
            "conditioned_floor_area_ft2": 2200,
            "conditioned_volume_ft3": 19800,
            "bedrooms": 3,
            "reference_files": [
                {
                    "filename": "test-home.xml",
                    "sha256": "a" * 64,
                }
            ],
            "test_cycles": [
                "BEEP-TEST-CYCLE-001"
            ],
            "review": {
                "reviewer": "Fictional Test Reviewer",
                "review_record": "BEEP-REV-TEST-001",
                "review_status": "COMPLETED",
                "review_date": review_date,
                "review_findings":
                    "Fictional technical review.",
                "review_recommendation":
                    "RECOMMEND_APPROVAL",
                "conflict_of_interest_disclosure":
                    "Fictional test disclosure.",
                "reviewed_content_sha256": None,
            },
            "approval": {
                "approved_by":
                    "B.E.E.P. Board of Directors",
                "approval_date": approval_date,
                "approval_record":
                    "BEEP-APP-TEST-001",
                "board_resolution_reference":
                    "BEEP-RES-TEST-001",
            },
        }

        home["review"][
            "reviewed_content_sha256"
        ] = calculate_technical_fingerprint(home)

        return home

    def write_registry(self, homes):
        registry = {
            "registry_version": "1.1.0",
            "registry_status": "DEVELOPMENT",
            "reference_homes": homes,
        }

        self.registry_path.write_text(
            json.dumps(registry),
            encoding="utf-8",
        )

    def assert_error(self, errors, expected):
        self.assertTrue(
            any(
                expected in error
                for error in errors
            ),
            errors,
        )

    def test_development_exempt_from_chronology(self):
        home = {
            "status": "DEVELOPMENT"
        }

        self.assertEqual(
            validate_review_approval_chronology(home),
            [],
        )

    def test_under_review_exempt_from_chronology(self):
        home = {
            "status": "UNDER_REVIEW"
        }

        self.assertEqual(
            validate_review_approval_chronology(home),
            [],
        )

    def test_approval_after_review_accepted(self):
        home = self.make_home()

        self.assertEqual(
            validate_review_approval_chronology(home),
            [],
        )

    def test_same_day_approval_accepted(self):
        home = self.make_home(
            approval_date="2026-11-24"
        )

        self.assertEqual(
            validate_review_approval_chronology(home),
            [],
        )

    def test_approval_before_review_rejected(self):
        home = self.make_home(
            approval_date="2026-11-23"
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "cannot precede the technical review date",
        )

    def test_retired_valid_chronology_accepted(self):
        home = self.make_home(
            status="RETIRED"
        )

        self.assertEqual(
            validate_review_approval_chronology(home),
            [],
        )

    def test_retired_invalid_chronology_rejected(self):
        home = self.make_home(
            status="RETIRED",
            approval_date="2026-11-23",
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "cannot precede the technical review date",
        )

    def test_missing_review_rejected(self):
        home = self.make_home()

        del home["review"]

        self.assert_error(
            validate_review_approval_chronology(home),
            "Missing or invalid technical review metadata",
        )

    def test_incomplete_review_rejected(self):
        home = self.make_home()

        home["review"]["review_status"] = (
            "IN_PROGRESS"
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "is not permitted for lifecycle status",
        )

    def test_missing_review_date_rejected(self):
        home = self.make_home(
            review_date=None
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "Invalid technical review date",
        )

    def test_invalid_review_date_rejected(self):
        home = self.make_home(
            review_date="2026-02-30"
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "Invalid technical review date",
        )

    def test_noncanonical_review_date_rejected(self):
        home = self.make_home(
            review_date="11/24/2026"
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "Invalid technical review date",
        )

    def test_missing_approval_metadata_rejected(self):
        home = self.make_home()

        del home["approval"]

        self.assert_error(
            validate_review_approval_chronology(home),
            "Missing or invalid approval metadata",
        )

    def test_missing_approval_date_rejected(self):
        home = self.make_home(
            approval_date=None
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "Missing or invalid Board approval date",
        )

    def test_invalid_approval_date_rejected(self):
        home = self.make_home(
            approval_date="2026-02-30"
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "Missing or invalid Board approval date",
        )

    def test_noncanonical_approval_date_rejected(self):
        home = self.make_home(
            approval_date="11/25/2026"
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "Missing or invalid Board approval date",
        )

    def test_invalid_fingerprint_rejected(self):
        home = self.make_home()

        home["bedrooms"] = 4

        self.assert_error(
            validate_review_approval_chronology(home),
            "does not match the completed review",
        )

    def test_revisions_required_rejected(self):
        home = self.make_home()

        home["review"][
            "review_recommendation"
        ] = "REVISIONS_REQUIRED"

        self.assert_error(
            validate_review_approval_chronology(home),
            "require RECOMMEND_APPROVAL",
        )

    def test_invalid_lifecycle_rejected(self):
        home = self.make_home(
            status="UNKNOWN"
        )

        self.assert_error(
            validate_review_approval_chronology(home),
            "Invalid reference home lifecycle status",
        )

    def test_malformed_home_rejected(self):
        self.assert_error(
            validate_review_approval_chronology(None),
            "Reference home must be a JSON object",
        )

    def test_valid_registry_accepted(self):
        self.write_registry([
            self.make_home()
        ])

        self.assertEqual(
            validate_registry_approval_chronology(
                self.registry_path
            ),
            [],
        )

    def test_multiple_homes_accepted(self):
        first = self.make_home(
            home_id="BEEP-HOME-001"
        )

        second = self.make_home(
            home_id="BEEP-HOME-002"
        )

        self.write_registry([
            first,
            second,
        ])

        self.assertEqual(
            validate_registry_approval_chronology(
                self.registry_path
            ),
            [],
        )

    def test_multiple_versions_accepted(self):
        first = self.make_home(
            version="1.0.0",
            status="RETIRED",
        )

        second = self.make_home(
            version="1.0.1"
        )

        self.write_registry([
            first,
            second,
        ])

        self.assertEqual(
            validate_registry_approval_chronology(
                self.registry_path
            ),
            [],
        )

    def test_multiple_invalid_homes_reported(self):
        first = self.make_home(
            home_id="BEEP-HOME-001",
            approval_date="2026-11-23",
        )

        second = self.make_home(
            home_id="BEEP-HOME-002",
            approval_date="2026-11-22",
        )

        self.write_registry([
            first,
            second,
        ])

        errors = (
            validate_registry_approval_chronology(
                self.registry_path
            )
        )

        self.assert_error(
            errors,
            "BEEP-HOME-001/1.0.0",
        )

        self.assert_error(
            errors,
            "BEEP-HOME-002/1.0.0",
        )

    def test_empty_registry_rejected(self):
        self.write_registry([])

        self.assert_error(
            validate_registry_approval_chronology(
                self.registry_path
            ),
            "at least one reference home",
        )

    def test_missing_registry_rejected(self):
        self.assert_error(
            validate_registry_approval_chronology(
                self.registry_path
            ),
            "Unable to read reference registry",
        )

    def test_invalid_json_rejected(self):
        self.registry_path.write_text(
            "{invalid json",
            encoding="utf-8",
        )

        self.assert_error(
            validate_registry_approval_chronology(
                self.registry_path
            ),
            "Unable to read reference registry",
        )

    def test_invalid_registry_root_rejected(self):
        self.registry_path.write_text(
            "[]",
            encoding="utf-8",
        )

        self.assert_error(
            validate_registry_approval_chronology(
                self.registry_path
            ),
            "Reference registry must be a JSON object",
        )

    def test_missing_reference_homes_rejected(self):
        self.registry_path.write_text(
            "{}",
            encoding="utf-8",
        )

        self.assert_error(
            validate_registry_approval_chronology(
                self.registry_path
            ),
            "at least one reference home",
        )

    def test_original_record_not_modified(self):
        home = self.make_home()

        original = copy.deepcopy(home)

        validate_review_approval_chronology(home)

        self.assertEqual(
            home,
            original,
        )


if __name__ == "__main__":
    unittest.main()
