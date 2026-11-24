import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_review_identifiers import (
    EXPECTED_POLICY,
    GOVERNANCE_AUTHORITY,
    REGISTRY_NAME,
    SCHEMA_VERSION,
)

from validate_technical_review import (
    calculate_technical_fingerprint,
)

from validate_review_assignment_consistency import (
    validate_assignment_consistency_data,
    validate_review_assignment_consistency,
)


class TestReviewAssignmentConsistency(unittest.TestCase):

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

        self.reference_path = (
            self.directory
            / "reference-home-registry.json"
        )

        self.identifier_path = (
            self.directory
            / "reference-review-identifier-registry.json"
        )

    def make_home(
        self,
        home_id="BEEP-HOME-TEST",
        version="1.0.0",
        review_status="IN_PROGRESS",
        record_id="BEEP-REV-TEST-001",
        reviewer="Fictional Test Reviewer",
    ):

        home = {
            "test_home_id": home_id,
            "test_home_version": version,
            "status": "UNDER_REVIEW",
            "conditioned_floor_area_ft2": 2200,
            "conditioned_volume_ft3": 19800,
            "bedrooms": 3,
            "review": {
                "reviewer": reviewer,
                "review_record": record_id,
                "review_status": review_status,
                "review_date": None,
                "review_findings": None,
                "review_recommendation": None,
                "conflict_of_interest_disclosure": (
                    "Fictional test disclosure"
                ),
                "reviewed_content_sha256": None,
            },
        }

        if review_status == "NOT_STARTED":

            home["status"] = "DEVELOPMENT"

            for field in home["review"]:

                if field != "review_status":

                    home["review"][field] = None

        elif review_status == "COMPLETED":

            home["review"].update({
                "review_date": "2026-01-20",
                "review_findings": (
                    "Fictional test findings"
                ),
                "review_recommendation": (
                    "RECOMMEND_APPROVAL"
                ),
                "reviewed_content_sha256": (
                    calculate_technical_fingerprint(
                        home
                    )
                ),
            })

        return home

    def make_reservation(self, **changes):

        reservation = {
            "review_record_id": "BEEP-REV-TEST-001",
            "reference_home_id": "BEEP-HOME-TEST",
            "reference_home_version": "1.0.0",
            "assigned_reviewer": (
                "Fictional Test Reviewer"
            ),
            "assignment_date": "2026-01-15",
        }

        reservation.update(changes)

        return reservation

    def make_registry(self, reservations=None):

        return {
            "registry_schema_version": SCHEMA_VERSION,
            "registry_status": "DEVELOPMENT",
            "registry_name": REGISTRY_NAME,
            "governance_authority": GOVERNANCE_AUTHORITY,
            "reservation_policy": copy.deepcopy(
                EXPECTED_POLICY
            ),
            "reservations": (
                []
                if reservations is None
                else reservations
            ),
        }

    def make_lookup(self, *homes):

        return {
            (
                home["test_home_id"],
                home["test_home_version"],
            ): home
            for home in homes
        }

    def validate(self, home, reservations):

        return validate_assignment_consistency_data(
            self.make_lookup(home),
            self.make_registry(reservations),
        )

    def assert_rejected(self, errors, message=None):

        self.assertTrue(errors)

        if message is not None:

            self.assertTrue(
                any(
                    message in error
                    for error in errors
                ),
                errors,
            )

    def write_files(self, homes, reservations):

        self.reference_path.write_text(
            json.dumps({
                "reference_homes": homes,
            }),
            encoding="utf-8",
        )

        self.identifier_path.write_text(
            json.dumps(
                self.make_registry(reservations)
            ),
            encoding="utf-8",
        )

    def validate_files(self):

        return validate_review_assignment_consistency(
            self.reference_path,
            self.identifier_path,
        )

    # Valid assignment scenarios

    def test_not_started_without_reservation(self):

        home = self.make_home(
            review_status="NOT_STARTED"
        )

        self.assertEqual(
            self.validate(home, []),
            [],
        )

    def test_in_progress_matching_reservation(self):

        self.assertEqual(
            self.validate(
                self.make_home(),
                [self.make_reservation()],
            ),
            [],
        )

    def test_completed_matching_reservation(self):

        home = self.make_home(
            review_status="COMPLETED"
        )

        self.assertEqual(
            self.validate(
                home,
                [self.make_reservation()],
            ),
            [],
        )

    def test_completed_on_assignment_date(self):

        home = self.make_home(
            review_status="COMPLETED"
        )

        home["review"]["review_date"] = (
            "2026-01-15"
        )

        self.assertEqual(
            self.validate(
                home,
                [self.make_reservation()],
            ),
            [],
        )

    def test_abandoned_reservation_retained(self):

        home = self.make_home(
            review_status="NOT_STARTED"
        )

        self.assertEqual(
            self.validate(
                home,
                [self.make_reservation()],
            ),
            [],
        )

    def test_active_and_abandoned_reservations(self):

        reservations = [
            self.make_reservation(),
            self.make_reservation(
                review_record_id="BEEP-REV-OLD-001"
            ),
        ]

        self.assertEqual(
            self.validate(
                self.make_home(),
                reservations,
            ),
            [],
        )

    def test_multiple_independent_home_assignments(self):

        first = self.make_home()

        second = self.make_home(
            home_id="BEEP-HOME-OTHER",
            record_id="BEEP-REV-TEST-002",
        )

        reservations = [
            self.make_reservation(),
            self.make_reservation(
                review_record_id="BEEP-REV-TEST-002",
                reference_home_id="BEEP-HOME-OTHER",
            ),
        ]

        self.assertEqual(
            validate_assignment_consistency_data(
                self.make_lookup(first, second),
                self.make_registry(reservations),
            ),
            [],
        )

    def test_independent_version_assignments(self):

        first = self.make_home()

        second = self.make_home(
            version="2.0.0",
            record_id="BEEP-REV-TEST-002",
        )

        reservations = [
            self.make_reservation(),
            self.make_reservation(
                review_record_id="BEEP-REV-TEST-002",
                reference_home_version="2.0.0",
            ),
        ]

        self.assertEqual(
            validate_assignment_consistency_data(
                self.make_lookup(first, second),
                self.make_registry(reservations),
            ),
            [],
        )

    # Assignment mismatch rejection

    def test_in_progress_without_reservation(self):

        self.assert_rejected(
            self.validate(self.make_home(), []),
            "has no permanent reservation",
        )

    def test_completed_without_reservation(self):

        home = self.make_home(
            review_status="COMPLETED"
        )

        self.assert_rejected(
            self.validate(home, []),
            "has no permanent reservation",
        )

    def test_mismatched_record_identifier(self):

        reservation = self.make_reservation(
            review_record_id="BEEP-REV-OTHER"
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                [reservation],
            ),
            "has no permanent reservation",
        )

    def test_identifier_capitalization_mismatch(self):

        reservation = self.make_reservation(
            review_record_id="beep-rev-test-001"
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                [reservation],
            ),
            "capitalization does not match",
        )

    def test_mismatched_reference_home(self):

        reservation = self.make_reservation(
            reference_home_id="BEEP-HOME-OTHER"
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                [reservation],
            ),
            "belongs to a different reference home",
        )

    def test_mismatched_reference_home_version(self):

        reservation = self.make_reservation(
            reference_home_version="2.0.0"
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                [reservation],
            ),
            "belongs to a different reference home version",
        )

    def test_mismatched_reviewer(self):

        reservation = self.make_reservation(
            assigned_reviewer="Different Fictional Reviewer"
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                [reservation],
            ),
            "reviewer does not match",
        )

    def test_reviewer_capitalization_mismatch(self):

        reservation = self.make_reservation(
            assigned_reviewer="fictional test reviewer"
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                [reservation],
            ),
            "reviewer does not match",
        )

    def test_review_completed_before_assignment(self):

        home = self.make_home(
            review_status="COMPLETED"
        )

        reservation = self.make_reservation(
            assignment_date="2026-01-21"
        )

        self.assert_rejected(
            self.validate(home, [reservation]),
            "completion date cannot precede",
        )

    def test_duplicate_identifier_across_homes(self):

        first = self.make_home()

        second = self.make_home(
            home_id="BEEP-HOME-OTHER"
        )

        self.assert_rejected(
            validate_assignment_consistency_data(
                self.make_lookup(first, second),
                self.make_registry([
                    self.make_reservation()
                ]),
            ),
            "is already referenced by",
        )

    def test_duplicate_identifier_across_versions(self):

        first = self.make_home()

        second = self.make_home(
            version="2.0.0"
        )

        self.assert_rejected(
            validate_assignment_consistency_data(
                self.make_lookup(first, second),
                self.make_registry([
                    self.make_reservation()
                ]),
            ),
            "is already referenced by",
        )

    def test_case_insensitive_duplicate_review_usage(self):

        first = self.make_home()

        second = self.make_home(
            home_id="BEEP-HOME-OTHER",
            record_id="beep-rev-test-001",
        )

        self.assert_rejected(
            validate_assignment_consistency_data(
                self.make_lookup(first, second),
                self.make_registry([
                    self.make_reservation()
                ]),
            ),
            "is already referenced by",
        )

    # Registry and input validation

    def test_reservation_for_unregistered_home(self):

        home = self.make_home(
            review_status="NOT_STARTED"
        )

        reservation = self.make_reservation(
            reference_home_id="BEEP-HOME-UNKNOWN"
        )

        self.assert_rejected(
            self.validate(home, [reservation]),
            "references an unregistered reference home version",
        )

    def test_reservation_for_unregistered_version(self):

        home = self.make_home(
            review_status="NOT_STARTED"
        )

        reservation = self.make_reservation(
            reference_home_version="9.0.0"
        )

        self.assert_rejected(
            self.validate(home, [reservation]),
            "references an unregistered reference home version",
        )

    def test_invalid_identifier_registry(self):

        self.assert_rejected(
            validate_assignment_consistency_data(
                self.make_lookup(self.make_home()),
                [],
            ),
            "Identifier registry:",
        )

    def test_invalid_reservation_date(self):

        reservation = self.make_reservation(
            assignment_date="2026-02-30"
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                [reservation],
            ),
            "Invalid review assignment date",
        )

    def test_duplicate_reservation_identifiers(self):

        self.assert_rejected(
            self.validate(
                self.make_home(),
                [
                    self.make_reservation(),
                    self.make_reservation(),
                ],
            ),
            "Duplicate technical review record identifier",
        )

    def test_invalid_home_lookup_type(self):

        self.assert_rejected(
            validate_assignment_consistency_data(
                [],
                self.make_registry(),
            ),
            "lookup must be a dictionary",
        )

    def test_empty_home_lookup(self):

        self.assert_rejected(
            validate_assignment_consistency_data(
                {},
                self.make_registry(),
            ),
            "at least one reference home",
        )

    def test_malformed_home_lookup_entry(self):

        self.assert_rejected(
            validate_assignment_consistency_data(
                {
                    ("BEEP-HOME-TEST", "1.0.0"): None
                },
                self.make_registry(),
            ),
            "malformed reference home",
        )

    def test_lookup_identity_mismatch(self):

        self.assert_rejected(
            validate_assignment_consistency_data(
                {
                    ("BEEP-HOME-OTHER", "1.0.0"):
                    self.make_home()
                },
                self.make_registry(),
            ),
            "lookup identity does not match",
        )

    def test_invalid_reference_home_identifier(self):

        home = self.make_home(
            home_id="../invalid"
        )

        self.assert_rejected(
            self.validate(home, []),
            "Invalid reference home identifier",
        )

    def test_invalid_reference_home_version(self):

        home = self.make_home(
            version="01.0.0"
        )

        self.assert_rejected(
            self.validate(home, []),
            "Invalid reference home version",
        )

    def test_invalid_review_status(self):

        home = self.make_home()

        home["review"]["review_status"] = (
            "INVALID"
        )

        self.assert_rejected(
            self.validate(
                home,
                [self.make_reservation()],
            )
        )

    def test_invalid_completed_review_fingerprint(self):

        home = self.make_home(
            review_status="COMPLETED"
        )

        home["conditioned_floor_area_ft2"] = 2400

        self.assert_rejected(
            self.validate(
                home,
                [self.make_reservation()],
            ),
            "fingerprint does not match",
        )

    def test_original_inputs_not_modified(self):

        homes = self.make_lookup(
            self.make_home()
        )

        registry = self.make_registry([
            self.make_reservation()
        ])

        homes_copy = copy.deepcopy(homes)
        registry_copy = copy.deepcopy(registry)

        validate_assignment_consistency_data(
            homes,
            registry,
        )

        self.assertEqual(homes, homes_copy)
        self.assertEqual(registry, registry_copy)

    # Integrated file validation

    def test_valid_registry_files(self):

        self.write_files(
            [self.make_home()],
            [self.make_reservation()],
        )

        self.assertEqual(
            self.validate_files(),
            [],
        )

    def test_missing_reference_registry(self):

        self.write_files(
            [self.make_home()],
            [self.make_reservation()],
        )

        self.reference_path.unlink()

        self.assert_rejected(
            self.validate_files()
        )

    def test_missing_identifier_registry(self):

        self.write_files(
            [self.make_home()],
            [self.make_reservation()],
        )

        self.identifier_path.unlink()

        self.assert_rejected(
            self.validate_files()
        )

    def test_malformed_reference_registry_json(self):

        self.write_files(
            [self.make_home()],
            [self.make_reservation()],
        )

        self.reference_path.write_text(
            "{invalid json",
            encoding="utf-8",
        )

        self.assert_rejected(
            self.validate_files()
        )

    def test_malformed_identifier_registry_json(self):

        self.write_files(
            [self.make_home()],
            [self.make_reservation()],
        )

        self.identifier_path.write_text(
            "{invalid json",
            encoding="utf-8",
        )

        self.assert_rejected(
            self.validate_files()
        )

    def test_duplicate_reference_home_versions(self):

        home = self.make_home()

        self.write_files(
            [home, copy.deepcopy(home)],
            [self.make_reservation()],
        )

        self.assert_rejected(
            self.validate_files(),
            "duplicate reference home version",
        )


if __name__ == "__main__":
    unittest.main()
