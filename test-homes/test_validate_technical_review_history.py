import copy
import unittest

from validate_technical_review import (
    calculate_technical_fingerprint,
)

from validate_technical_review_history import (
    validate_historical_review_transition,
)


class TestHistoricalTechnicalReview(unittest.TestCase):

    def make_home(
        self,
        lifecycle="DEVELOPMENT",
        review_status="NOT_STARTED",
        recommendation="RECOMMEND_APPROVAL",
    ):
        home = {
            "test_home_id": "BEEP-HOME-TEST",
            "test_home_version": "1.0.0",
            "parent_version": None,
            "status": lifecycle,
            "conditioned_floor_area_ft2": 2200,
            "conditioned_volume_ft3": 19800,
            "bedrooms": 3,
            "wall_insulation_r_value": 15,
            "ceiling_insulation_r_value": 49,
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

    def assert_rejected(
        self,
        previous,
        current,
        expected_message,
    ):
        errors = validate_historical_review_transition(
            previous,
            current,
        )

        self.assertTrue(
            any(
                expected_message in error
                for error in errors
            ),
            errors,
        )

    def test_not_started_unchanged_accepted(self):
        previous = self.make_home()
        current = copy.deepcopy(previous)

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_review_start_accepted(self):
        previous = self.make_home()

        current = self.make_home(
            "UNDER_REVIEW",
            "IN_PROGRESS",
        )

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_review_start_cannot_be_skipped(self):
        previous = self.make_home()

        current = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        self.assert_rejected(
            previous,
            current,
            "Invalid technical review transition",
        )

    def test_in_progress_review_unchanged_accepted(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "IN_PROGRESS",
        )

        current = copy.deepcopy(previous)

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_review_completion_accepted(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "IN_PROGRESS",
        )

        current = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_completed_review_unchanged_accepted(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_completed_reviewer_change_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["review"]["reviewer"] = (
            "Different Reviewer"
        )

        self.assert_rejected(
            previous,
            current,
            "Completed technical review metadata",
        )

    def test_completed_findings_change_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["review"]["review_findings"] = (
            "Modified findings."
        )

        self.assert_rejected(
            previous,
            current,
            "Completed technical review metadata",
        )

    def test_completed_review_date_change_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["review"]["review_date"] = (
            "2026-11-23"
        )

        self.assert_rejected(
            previous,
            current,
            "Completed technical review metadata",
        )

    def test_completed_record_id_change_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["review"]["review_record"] = (
            "BEEP-REV-TEST-002"
        )

        self.assert_rejected(
            previous,
            current,
            "Completed technical review metadata",
        )

    def test_completed_disclosure_change_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["review"][
            "conflict_of_interest_disclosure"
        ] = "Modified disclosure."

        self.assert_rejected(
            previous,
            current,
            "Completed technical review metadata",
        )

    def test_completed_recommendation_change_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["review"][
            "review_recommendation"
        ] = "REVISIONS_REQUIRED"

        self.assert_rejected(
            previous,
            current,
            "Completed technical review metadata",
        )

    def test_technical_change_and_new_hash_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["wall_insulation_r_value"] = 13

        current["review"][
            "reviewed_content_sha256"
        ] = calculate_technical_fingerprint(current)

        self.assert_rejected(
            previous,
            current,
            "Previously reviewed technical content",
        )

    def test_reference_checksum_and_hash_change_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["reference_files"][0]["sha256"] = (
            "b" * 64
        )

        current["review"][
            "reviewed_content_sha256"
        ] = calculate_technical_fingerprint(current)

        self.assert_rejected(
            previous,
            current,
            "Previously reviewed technical content",
        )

    def test_technical_change_without_new_hash_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)

        current["conditioned_floor_area_ft2"] = 2300

        self.assert_rejected(
            previous,
            current,
            "does not match the completed review",
        )

    def test_in_progress_review_reset_accepted(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "IN_PROGRESS",
        )

        current = self.make_home()

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_completed_review_reset_accepted(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = self.make_home()

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_completed_to_in_progress_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = self.make_home(
            "UNDER_REVIEW",
            "IN_PROGRESS",
        )

        self.assert_rejected(
            previous,
            current,
            "Invalid technical review transition",
        )

    def test_approval_after_completed_review_accepted(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)
        current["status"] = "APPROVED"

        current["approval"]["approved_by"] = (
            "B.E.E.P. Board of Directors"
        )

        current["test_cycles"] = [
            "TEST-CYCLE-001",
        ]

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_simultaneous_review_and_approval_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "IN_PROGRESS",
        )

        current = self.make_home(
            "APPROVED",
            "COMPLETED",
        )

        self.assert_rejected(
            previous,
            current,
            "Approval requires a previously completed",
        )

    def test_direct_development_approval_rejected(self):
        previous = self.make_home()

        current = self.make_home(
            "APPROVED",
            "COMPLETED",
        )

        self.assert_rejected(
            previous,
            current,
            "Approval requires a previous UNDER_REVIEW",
        )

    def test_approval_after_revisions_required_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
            "REVISIONS_REQUIRED",
        )

        current = copy.deepcopy(previous)
        current["status"] = "APPROVED"

        current["review"][
            "review_recommendation"
        ] = "RECOMMEND_APPROVAL"

        self.assert_rejected(
            previous,
            current,
            "Previous technical review must recommend approval",
        )

    def test_approved_review_reset_rejected(self):
        previous = self.make_home(
            "APPROVED",
            "COMPLETED",
        )

        current = self.make_home()

        self.assert_rejected(
            previous,
            current,
            "Approved or retired technical reviews",
        )

    def test_retired_review_reset_rejected(self):
        previous = self.make_home(
            "RETIRED",
            "COMPLETED",
        )

        current = self.make_home()

        self.assert_rejected(
            previous,
            current,
            "Approved or retired technical reviews",
        )

    def test_approved_to_retired_accepted(self):
        previous = self.make_home(
            "APPROVED",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)
        current["status"] = "RETIRED"

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_legacy_development_registry_accepted(self):
        previous = self.make_home()
        del previous["review"]

        current = self.make_home()

        self.assertEqual(
            validate_historical_review_transition(
                previous, current
            ),
            [],
        )

    def test_missing_previous_active_review_rejected(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "IN_PROGRESS",
        )

        del previous["review"]

        current = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        self.assert_rejected(
            previous,
            current,
            "Previous review:",
        )

    def test_different_home_id_rejected(self):
        previous = self.make_home()
        current = copy.deepcopy(previous)

        current["test_home_id"] = "BEEP-HOME-OTHER"

        self.assert_rejected(
            previous,
            current,
            "requires matching test_home_id",
        )

    def test_different_version_rejected(self):
        previous = self.make_home()
        current = copy.deepcopy(previous)

        current["test_home_version"] = "1.0.1"

        self.assert_rejected(
            previous,
            current,
            "requires matching test_home_version",
        )

    def test_invalid_previous_home_rejected(self):
        current = self.make_home()

        for invalid in (None, [], "", 123, True):
            with self.subTest(value=invalid):
                self.assert_rejected(
                    invalid,
                    current,
                    "Previous reference home must be",
                )

    def test_invalid_current_home_rejected(self):
        previous = self.make_home()

        for invalid in (None, [], "", 123, True):
            with self.subTest(value=invalid):
                self.assert_rejected(
                    previous,
                    invalid,
                    "Current reference home must be",
                )

    def test_original_records_not_modified(self):
        previous = self.make_home(
            "UNDER_REVIEW",
            "COMPLETED",
        )

        current = copy.deepcopy(previous)
        current["status"] = "APPROVED"

        original_previous = copy.deepcopy(previous)
        original_current = copy.deepcopy(current)

        validate_historical_review_transition(
            previous,
            current,
        )

        self.assertEqual(previous, original_previous)
        self.assertEqual(current, original_current)


if __name__ == "__main__":
    unittest.main()
