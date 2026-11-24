import copy
import json
import unittest

from validate_technical_review import (
    get_technical_content,
    calculate_technical_fingerprint,
    validate_review_status,
)


class TestTechnicalFingerprint(unittest.TestCase):

    def setUp(self):
        self.home = {
            "test_home_id": "BEEP-HOME-TEST",
            "test_home_version": "1.0.0",
            "parent_version": None,
            "name": "Test Reference Home",
            "description": "Technical fingerprint test.",
            "status": "DEVELOPMENT",
            "building_type": "SINGLE_FAMILY_DETACHED",
            "conditioned_floor_area_ft2": 2200,
            "conditioned_volume_ft3": 19800,
            "bedrooms": 3,
            "reference_files": [
                {
                    "filename": "test-home.xml",
                    "sha256": "a" * 64,
                }
            ],
            "approved_compliance_paths": [
                "ERI",
                "R405",
            ],
            "test_cycles": [],
            "review": {
                "review_status": "NOT_STARTED",
            },
            "approval": {
                "approved_by": None,
            },
            "version_history": [
                {
                    "version": "1.0.0",
                    "change_type": "INITIAL",
                    "description": "Initial test version.",
                }
            ],
        }

    def fingerprint(self, home=None):
        if home is None:
            home = self.home

        return calculate_technical_fingerprint(home)

    def test_valid_sha256_format(self):
        result = self.fingerprint()

        self.assertRegex(
            result,
            r"^[0-9a-f]{64}$",
        )

    def test_identical_content_same_fingerprint(self):
        duplicate = copy.deepcopy(self.home)

        self.assertEqual(
            self.fingerprint(),
            self.fingerprint(duplicate),
        )

    def test_object_key_order_does_not_matter(self):
        reordered = dict(
            reversed(list(self.home.items()))
        )

        self.assertEqual(
            self.fingerprint(),
            self.fingerprint(reordered),
        )

    def test_json_formatting_does_not_matter(self):
        formatted = json.dumps(
            self.home,
            indent=4,
        )

        compact = json.dumps(
            self.home,
            separators=(",", ":"),
        )

        self.assertEqual(
            self.fingerprint(json.loads(formatted)),
            self.fingerprint(json.loads(compact)),
        )

    def test_administrative_fields_excluded(self):
        technical = get_technical_content(self.home)

        for field in (
            "status",
            "review",
            "approval",
            "test_cycles",
        ):
            with self.subTest(field=field):
                self.assertNotIn(field, technical)

    def test_lifecycle_status_change_ignored(self):
        modified = copy.deepcopy(self.home)
        modified["status"] = "UNDER_REVIEW"

        self.assertEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_review_metadata_change_ignored(self):
        modified = copy.deepcopy(self.home)
        modified["review"] = {
            "review_status": "COMPLETED",
            "reviewer": "Test Reviewer",
        }

        self.assertEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_approval_metadata_change_ignored(self):
        modified = copy.deepcopy(self.home)
        modified["approval"] = {
            "approved_by": "Test Authority",
        }

        self.assertEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_test_cycle_assignment_ignored(self):
        modified = copy.deepcopy(self.home)
        modified["test_cycles"] = [
            "TEST-CYCLE-001",
        ]

        self.assertEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_reference_home_id_change_detected(self):
        modified = copy.deepcopy(self.home)
        modified["test_home_id"] = "BEEP-HOME-OTHER"

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_version_change_detected(self):
        modified = copy.deepcopy(self.home)
        modified["test_home_version"] = "1.0.1"

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_parent_version_change_detected(self):
        modified = copy.deepcopy(self.home)
        modified["parent_version"] = "1.0.0"

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_floor_area_change_detected(self):
        modified = copy.deepcopy(self.home)
        modified["conditioned_floor_area_ft2"] = 2300

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_conditioned_volume_change_detected(self):
        modified = copy.deepcopy(self.home)
        modified["conditioned_volume_ft3"] = 20000

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_bedroom_count_change_detected(self):
        modified = copy.deepcopy(self.home)
        modified["bedrooms"] = 4

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_reference_filename_change_detected(self):
        modified = copy.deepcopy(self.home)

        modified["reference_files"][0]["filename"] = (
            "different-home.xml"
        )

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_reference_checksum_change_detected(self):
        modified = copy.deepcopy(self.home)

        modified["reference_files"][0]["sha256"] = (
            "b" * 64
        )

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_compliance_path_change_detected(self):
        modified = copy.deepcopy(self.home)
        modified["approved_compliance_paths"] = [
            "ERI",
        ]

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_version_history_change_detected(self):
        modified = copy.deepcopy(self.home)

        modified["version_history"][0]["description"] = (
            "Modified change documentation."
        )

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_future_technical_field_included(self):
        modified = copy.deepcopy(self.home)
        modified["wall_insulation_r_value"] = 15

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_array_order_change_detected(self):
        modified = copy.deepcopy(self.home)

        modified["approved_compliance_paths"].reverse()

        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(modified),
        )

    def test_invalid_reference_home_rejected(self):
        for invalid in (
            None,
            [],
            "invalid",
            123,
            True,
        ):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    calculate_technical_fingerprint(invalid)

    def test_nonfinite_numeric_values_rejected(self):
        for invalid in (
            float("nan"),
            float("inf"),
            float("-inf"),
        ):
            with self.subTest(value=invalid):
                modified = copy.deepcopy(self.home)

                modified["conditioned_floor_area_ft2"] = (
                    invalid
                )

                with self.assertRaises(ValueError):
                    self.fingerprint(modified)

    def test_original_reference_home_not_modified(self):
        original = copy.deepcopy(self.home)

        self.fingerprint()

        self.assertEqual(
            original,
            self.home,
        )


class TestTechnicalReviewStatus(unittest.TestCase):

    def make_home(self, lifecycle, review_status):
        return {
            "test_home_id": "BEEP-HOME-TEST",
            "test_home_version": "1.0.0",
            "status": lifecycle,
            "review": {
                "review_status": review_status,
            },
        }

    def test_development_not_started_accepted(self):
        home = self.make_home(
            "DEVELOPMENT", "NOT_STARTED"
        )
        self.assertEqual(validate_review_status(home), [])

    def test_development_in_progress_rejected(self):
        home = self.make_home(
            "DEVELOPMENT", "IN_PROGRESS"
        )
        self.assertTrue(validate_review_status(home))

    def test_development_completed_rejected(self):
        home = self.make_home(
            "DEVELOPMENT", "COMPLETED"
        )
        self.assertTrue(validate_review_status(home))

    def test_under_review_not_started_rejected(self):
        home = self.make_home(
            "UNDER_REVIEW", "NOT_STARTED"
        )
        self.assertTrue(validate_review_status(home))

    def test_under_review_in_progress_accepted(self):
        home = self.make_home(
            "UNDER_REVIEW", "IN_PROGRESS"
        )
        self.assertEqual(validate_review_status(home), [])

    def test_under_review_completed_accepted(self):
        home = self.make_home(
            "UNDER_REVIEW", "COMPLETED"
        )
        self.assertEqual(validate_review_status(home), [])

    def test_approved_not_started_rejected(self):
        home = self.make_home(
            "APPROVED", "NOT_STARTED"
        )
        self.assertTrue(validate_review_status(home))

    def test_approved_in_progress_rejected(self):
        home = self.make_home(
            "APPROVED", "IN_PROGRESS"
        )
        self.assertTrue(validate_review_status(home))

    def test_approved_completed_accepted(self):
        home = self.make_home(
            "APPROVED", "COMPLETED"
        )
        self.assertEqual(validate_review_status(home), [])

    def test_retired_not_started_rejected(self):
        home = self.make_home(
            "RETIRED", "NOT_STARTED"
        )
        self.assertTrue(validate_review_status(home))

    def test_retired_in_progress_rejected(self):
        home = self.make_home(
            "RETIRED", "IN_PROGRESS"
        )
        self.assertTrue(validate_review_status(home))

    def test_retired_completed_accepted(self):
        home = self.make_home(
            "RETIRED", "COMPLETED"
        )
        self.assertEqual(validate_review_status(home), [])

    def test_missing_review_metadata_rejected(self):
        home = self.make_home(
            "DEVELOPMENT", "NOT_STARTED"
        )
        del home["review"]

        self.assertTrue(validate_review_status(home))

    def test_malformed_review_metadata_rejected(self):
        for invalid in (None, [], "", 123, True):
            with self.subTest(value=invalid):
                home = self.make_home(
                    "DEVELOPMENT", "NOT_STARTED"
                )
                home["review"] = invalid

                self.assertTrue(
                    validate_review_status(home)
                )

    def test_missing_review_status_rejected(self):
        home = self.make_home(
            "DEVELOPMENT", "NOT_STARTED"
        )
        del home["review"]["review_status"]

        self.assertTrue(validate_review_status(home))

    def test_invalid_review_status_rejected(self):
        for invalid in (
            None,
            "",
            " ",
            "UNKNOWN",
            "completed",
            [],
            {},
            123,
            True,
        ):
            with self.subTest(value=invalid):
                home = self.make_home(
                    "UNDER_REVIEW", invalid
                )

                self.assertTrue(
                    validate_review_status(home)
                )

    def test_missing_lifecycle_status_rejected(self):
        home = self.make_home(
            "DEVELOPMENT", "NOT_STARTED"
        )
        del home["status"]

        self.assertTrue(validate_review_status(home))

    def test_invalid_lifecycle_status_rejected(self):
        for invalid in (
            None,
            "",
            "UNKNOWN",
            "development",
            [],
            {},
            123,
            True,
        ):
            with self.subTest(value=invalid):
                home = self.make_home(
                    invalid, "NOT_STARTED"
                )

                self.assertTrue(
                    validate_review_status(home)
                )

    def test_invalid_reference_home_rejected(self):
        for invalid in (None, [], "", 123, True):
            with self.subTest(value=invalid):
                self.assertTrue(
                    validate_review_status(invalid)
                )


if __name__ == "__main__":
    unittest.main()
