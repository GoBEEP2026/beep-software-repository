import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_technical_review import (
    calculate_technical_fingerprint,
)

from validate_technical_review_registry import (
    load_review_registry,
    validate_current_review_registry,
    validate_historical_review_registry,
)


class TestTechnicalReviewRegistry(unittest.TestCase):

    def setUp(self):
        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp_directory.cleanup
        )

        self.directory = Path(
            self.temp_directory.name
        )

        self.previous_path = (
            self.directory / "previous.json"
        )

        self.current_path = (
            self.directory / "current.json"
        )

    def make_home(
        self,
        home_id="BEEP-HOME-TEST",
        version="1.0.0",
        lifecycle="DEVELOPMENT",
        review_status="NOT_STARTED",
        recommendation="RECOMMEND_APPROVAL",
    ):
        home = {
            "test_home_id": home_id,
            "test_home_version": version,
            "status": lifecycle,
            "conditioned_floor_area_ft2": 2200,
            "conditioned_volume_ft3": 19800,
            "bedrooms": 3,
            "wall_insulation_r_value": 15,
            "reference_files": [
                {
                    "filename": "test-home.xml",
                    "sha256": "a" * 64,
                }
            ],
            "test_cycles": [],
            "approval": {
                "approved_by": None,
            },
            "review": {
                "reviewer": None,
                "review_record": None,
                "review_status": review_status,
                "review_date": None,
                "review_findings": None,
                "review_recommendation": None,
                "conflict_of_interest_disclosure": None,
                "reviewed_content_sha256": None,
            },
        }

        review = home["review"]

        if review_status in (
            "IN_PROGRESS",
            "COMPLETED",
        ):
            review.update({
                "reviewer": "Test Reviewer",
                "review_record": "BEEP-REV-TEST-001",
                "conflict_of_interest_disclosure":
                    "No conflicts identified.",
            })

        if review_status == "COMPLETED":
            review.update({
                "review_date": "2026-11-24",
                "review_findings":
                    "Technical review completed.",
                "review_recommendation":
                    recommendation,
                "reviewed_content_sha256":
                    calculate_technical_fingerprint(home),
            })

        return home

    def write_registry(self, path, homes):
        registry = {
            "registry_version": "1.1.0",
            "registry_status": "DEVELOPMENT",
            "reference_homes": homes,
        }

        path.write_text(
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

    def compare(self, previous, current):
        self.write_registry(
            self.previous_path,
            previous,
        )

        self.write_registry(
            self.current_path,
            current,
        )

        return validate_historical_review_registry(
            self.previous_path,
            self.current_path,
        )

    def test_valid_registry_loading(self):
        home = self.make_home()

        self.write_registry(
            self.current_path,
            [home],
        )

        homes, errors = load_review_registry(
            self.current_path,
            "Current",
        )

        self.assertEqual(errors, [])

        self.assertEqual(
            homes[("BEEP-HOME-TEST", "1.0.0")],
            home,
        )

    def test_missing_registry_rejected(self):
        homes, errors = load_review_registry(
            self.current_path,
            "Current",
        )

        self.assertEqual(homes, {})

        self.assert_error(
            errors,
            "Unable to read Current registry",
        )

    def test_invalid_json_rejected(self):
        self.current_path.write_text(
            "{invalid json",
            encoding="utf-8",
        )

        homes, errors = load_review_registry(
            self.current_path,
            "Current",
        )

        self.assertEqual(homes, {})

        self.assert_error(
            errors,
            "Unable to read Current registry",
        )

    def test_invalid_registry_root_rejected(self):
        self.current_path.write_text(
            "[]",
            encoding="utf-8",
        )

        homes, errors = load_review_registry(
            self.current_path,
            "Current",
        )

        self.assert_error(
            errors,
            "registry must be a JSON object",
        )

    def test_missing_reference_homes_rejected(self):
        self.current_path.write_text(
            "{}",
            encoding="utf-8",
        )

        homes, errors = load_review_registry(
            self.current_path,
            "Current",
        )

        self.assert_error(
            errors,
            "reference_homes array",
        )

    def test_malformed_home_rejected(self):
        self.write_registry(
            self.current_path,
            [None],
        )

        homes, errors = load_review_registry(
            self.current_path,
            "Current",
        )

        self.assert_error(
            errors,
            "malformed reference home",
        )

    def test_missing_home_identity_rejected(self):
        home = self.make_home()

        del home["test_home_id"]

        self.write_registry(
            self.current_path,
            [home],
        )

        homes, errors = load_review_registry(
            self.current_path,
            "Current",
        )

        self.assert_error(
            errors,
            "missing or invalid home identity",
        )

    def test_duplicate_home_version_rejected(self):
        home = self.make_home()

        self.write_registry(
            self.current_path,
            [home, copy.deepcopy(home)],
        )

        homes, errors = load_review_registry(
            self.current_path,
            "Current",
        )

        self.assert_error(
            errors,
            "duplicate reference home version",
        )

    def test_valid_current_registry(self):
        self.write_registry(
            self.current_path,
            [self.make_home()],
        )

        self.assertEqual(
            validate_current_review_registry(
                self.current_path
            ),
            [],
        )

    def test_empty_current_registry_rejected(self):
        self.write_registry(
            self.current_path,
            [],
        )

        self.assert_error(
            validate_current_review_registry(
                self.current_path
            ),
            "at least one reference home",
        )

    def test_multiple_reference_homes_accepted(self):
        first = self.make_home(
            home_id="BEEP-HOME-001"
        )

        second = self.make_home(
            home_id="BEEP-HOME-002"
        )

        self.write_registry(
            self.current_path,
            [first, second],
        )

        self.assertEqual(
            validate_current_review_registry(
                self.current_path
            ),
            [],
        )

    def test_multiple_home_versions_accepted(self):
        first = self.make_home(
            version="1.0.0"
        )

        second = self.make_home(
            version="1.0.1"
        )

        self.write_registry(
            self.current_path,
            [first, second],
        )

        self.assertEqual(
            validate_current_review_registry(
                self.current_path
            ),
            [],
        )

    def test_missing_current_review_rejected(self):
        home = self.make_home()

        del home["review"]

        self.write_registry(
            self.current_path,
            [home],
        )

        self.assert_error(
            validate_current_review_registry(
                self.current_path
            ),
            "Missing or invalid technical review metadata",
        )

    def test_current_fingerprint_mismatch_rejected(self):
        home = self.make_home(
            lifecycle="UNDER_REVIEW",
            review_status="COMPLETED",
        )

        home["bedrooms"] = 4

        self.write_registry(
            self.current_path,
            [home],
        )

        self.assert_error(
            validate_current_review_registry(
                self.current_path
            ),
            "does not match the completed review",
        )

    def test_unchanged_historical_registry_accepted(self):
        home = self.make_home()

        self.assertEqual(
            self.compare(
                [home],
                [copy.deepcopy(home)],
            ),
            [],
        )

    def test_new_development_version_accepted(self):
        first = self.make_home()

        second = self.make_home(
            version="1.0.1"
        )

        self.assertEqual(
            self.compare(
                [first],
                [first, second],
            ),
            [],
        )

    def test_new_approved_version_rejected(self):
        first = self.make_home()

        second = self.make_home(
            version="1.0.1",
            lifecycle="APPROVED",
            review_status="COMPLETED",
        )

        self.assert_error(
            self.compare(
                [first],
                [first, second],
            ),
            "must begin in DEVELOPMENT",
        )

    def test_deleted_historical_version_rejected(self):
        first = self.make_home()

        second = self.make_home(
            version="1.0.1"
        )

        self.assert_error(
            self.compare(
                [first, second],
                [first],
            ),
            "version cannot be removed",
        )

    def test_legacy_registry_migration_accepted(self):
        previous = self.make_home()

        del previous["review"]

        current = self.make_home()

        self.assertEqual(
            self.compare(
                [previous],
                [current],
            ),
            [],
        )

    def test_historical_review_metadata_change_rejected(self):
        previous = self.make_home(
            lifecycle="UNDER_REVIEW",
            review_status="COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["review"]["reviewer"] = (
            "Different Reviewer"
        )

        self.assert_error(
            self.compare(
                [previous],
                [current],
            ),
            "Completed technical review metadata",
        )

    def test_historical_content_and_hash_change_rejected(self):
        previous = self.make_home(
            lifecycle="UNDER_REVIEW",
            review_status="COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["wall_insulation_r_value"] = 13

        current["review"][
            "reviewed_content_sha256"
        ] = calculate_technical_fingerprint(current)

        self.assert_error(
            self.compare(
                [previous],
                [current],
            ),
            "Previously reviewed technical content",
        )

    def test_premature_approval_rejected(self):
        previous = self.make_home(
            lifecycle="UNDER_REVIEW",
            review_status="IN_PROGRESS",
        )

        current = self.make_home(
            lifecycle="APPROVED",
            review_status="COMPLETED",
        )

        self.assert_error(
            self.compare(
                [previous],
                [current],
            ),
            "Approval requires a previously completed",
        )

    def test_valid_historical_approval_accepted(self):
        previous = self.make_home(
            lifecycle="UNDER_REVIEW",
            review_status="COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["status"] = "APPROVED"

        current["approval"]["approved_by"] = (
            "B.E.E.P. Board of Directors"
        )

        self.assertEqual(
            self.compare(
                [previous],
                [current],
            ),
            [],
        )

    def test_multiple_invalid_reviews_reported(self):
        first = self.make_home(
            home_id="BEEP-HOME-001"
        )

        second = self.make_home(
            home_id="BEEP-HOME-002"
        )

        del first["review"]
        del second["review"]

        self.write_registry(
            self.current_path,
            [first, second],
        )

        errors = validate_current_review_registry(
            self.current_path
        )

        self.assert_error(
            errors,
            "BEEP-HOME-001/1.0.0",
        )

        self.assert_error(
            errors,
            "BEEP-HOME-002/1.0.0",
        )


if __name__ == "__main__":
    unittest.main()
