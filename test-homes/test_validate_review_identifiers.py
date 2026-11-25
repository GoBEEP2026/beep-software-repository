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
    validate_identifier_registry_data,
    validate_review_identifiers,
)


class TestReviewIdentifiers(unittest.TestCase):

    def setUp(self):

        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp_directory.cleanup
        )

        self.registry_path = (
            Path(self.temp_directory.name)
            / "identifier-registry.json"
        )

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

    def make_reservation(self, **changes):

        reservation = {
            "review_record_id": "BEEP-REV-TEST-001",
            "reference_home_id": "BEEP-HOME-TEST",
            "reference_home_version": "1.0.0",
            "assigned_reviewer": "Fictional Test Reviewer",
            "assignment_date": "2026-01-15",
        }

        reservation.update(changes)

        return reservation

    def write_registry(self, registry):

        self.registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8",
        )

    def assert_registry_rejected(
        self,
        registry,
        expected_message,
    ):

        errors = validate_identifier_registry_data(
            registry
        )

        self.assertTrue(errors)

        self.assertTrue(
            any(
                expected_message in error
                for error in errors
            ),
            errors,
        )

    def assert_reservation_rejected(
        self,
        reservation,
        expected_message,
    ):

        self.assert_registry_rejected(
            self.make_registry([reservation]),
            expected_message,
        )

    # Registry structure and metadata

    def test_valid_empty_registry(self):

        self.assertEqual(
            validate_identifier_registry_data(
                self.make_registry()
            ),
            [],
        )

    def test_invalid_registry_root(self):

        self.assert_registry_rejected(
            [],
            "Identifier registry must be an object",
        )

    def test_missing_schema_version(self):

        registry = self.make_registry()

        del registry["registry_schema_version"]

        self.assert_registry_rejected(
            registry,
            "Invalid registry field: registry_schema_version",
        )

    def test_invalid_schema_version(self):

        registry = self.make_registry()

        registry["registry_schema_version"] = "2.0.0"

        self.assert_registry_rejected(
            registry,
            "Invalid registry field: registry_schema_version",
        )

    def test_invalid_registry_status(self):

        registry = self.make_registry()

        registry["registry_status"] = "APPROVED"

        self.assert_registry_rejected(
            registry,
            "Invalid registry field: registry_status",
        )

    def test_invalid_registry_name(self):

        registry = self.make_registry()

        registry["registry_name"] = "Invalid Registry"

        self.assert_registry_rejected(
            registry,
            "Invalid registry field: registry_name",
        )

    def test_invalid_governance_authority(self):

        registry = self.make_registry()

        registry["governance_authority"] = (
            "Unauthorized Authority"
        )

        self.assert_registry_rejected(
            registry,
            "Invalid registry field: governance_authority",
        )

    def test_unexpected_registry_field(self):

        registry = self.make_registry()

        registry["unexpected"] = True

        self.assert_registry_rejected(
            registry,
            "Unexpected registry field",
        )

    def test_missing_reservations(self):

        registry = self.make_registry()

        del registry["reservations"]

        self.assert_registry_rejected(
            registry,
            "Identifier reservations must be a list",
        )

    def test_invalid_reservations_type(self):

        registry = self.make_registry()

        registry["reservations"] = {}

        self.assert_registry_rejected(
            registry,
            "Identifier reservations must be a list",
        )

    # Permanent reservation policy

    def test_missing_reservation_policy(self):

        registry = self.make_registry()

        del registry["reservation_policy"]

        self.assert_registry_rejected(
            registry,
            "Reservation policy must be an object",
        )

    def test_invalid_reservation_policy_type(self):

        registry = self.make_registry()

        registry["reservation_policy"] = []

        self.assert_registry_rejected(
            registry,
            "Reservation policy must be an object",
        )

    def test_missing_policy_field(self):

        registry = self.make_registry()

        del registry["reservation_policy"]["append_only"]

        self.assert_registry_rejected(
            registry,
            "Missing reservation policy field: append_only",
        )

    def test_modified_reservation_policy(self):

        for field, expected in EXPECTED_POLICY.items():

            with self.subTest(field=field):

                registry = self.make_registry()

                registry["reservation_policy"][field] = (
                    not expected
                    if isinstance(expected, bool)
                    else "INVALID"
                )

                self.assert_registry_rejected(
                    registry,
                    f"Invalid reservation policy field: {field}",
                )

    def test_policy_boolean_type_enforced(self):

        registry = self.make_registry()

        registry["reservation_policy"][
            "identifier_reuse_allowed"
        ] = 0

        self.assert_registry_rejected(
            registry,
            "Invalid reservation policy field: "
            "identifier_reuse_allowed",
        )

    def test_unexpected_policy_field(self):

        registry = self.make_registry()

        registry["reservation_policy"][
            "temporary_reservation"
        ] = True

        self.assert_registry_rejected(
            registry,
            "Unexpected reservation policy field",
        )

    # Individual reservation validation

    def test_valid_reservation(self):

        registry = self.make_registry([
            self.make_reservation()
        ])

        self.assertEqual(
            validate_identifier_registry_data(registry),
            [],
        )

    def test_invalid_reservation_type(self):

        self.assert_reservation_rejected(
            "invalid",
            "Identifier reservation must be an object",
        )

    def test_missing_reservation_fields(self):

        original = self.make_reservation()

        for field in original:

            with self.subTest(field=field):

                reservation = copy.deepcopy(original)

                del reservation[field]

                self.assert_reservation_rejected(
                    reservation,
                    f"Missing reservation field: {field}",
                )

    def test_unexpected_reservation_field(self):

        reservation = self.make_reservation(
            review_status="COMPLETED"
        )

        self.assert_reservation_rejected(
            reservation,
            "Unexpected reservation field",
        )

    def test_invalid_review_record_identifier(self):

        for value in (
            "",
            None,
            123,
            "../BEEP-REV-001",
            "BEEP REV 001",
            "BEEP/REV/001",
            "-BEEP-REV-001",
        ):

            with self.subTest(value=value):

                self.assert_reservation_rejected(
                    self.make_reservation(
                        review_record_id=value
                    ),
                    "Invalid technical review record identifier",
                )

    def test_invalid_reference_home_identifier(self):

        for value in (
            "",
            None,
            [],
            "../HOME",
            "HOME/001",
            "HOME 001",
        ):

            with self.subTest(value=value):

                self.assert_reservation_rejected(
                    self.make_reservation(
                        reference_home_id=value
                    ),
                    "Invalid reference home identifier",
                )

    def test_invalid_semantic_version(self):

        for value in (
            "",
            None,
            "1.0",
            "01.0.0",
            "1.00.0",
            "1.0.00",
            "1.0.0-beta",
            "1.0.0+build",
            "v1.0.0",
        ):

            with self.subTest(value=value):

                self.assert_reservation_rejected(
                    self.make_reservation(
                        reference_home_version=value
                    ),
                    "Invalid reference home semantic version",
                )

    def test_valid_semantic_versions(self):

        for value in (
            "0.0.0",
            "1.0.0",
            "2.3.4",
            "10.20.30",
        ):

            with self.subTest(value=value):

                registry = self.make_registry([
                    self.make_reservation(
                        reference_home_version=value
                    )
                ])

                self.assertEqual(
                    validate_identifier_registry_data(
                        registry
                    ),
                    [],
                )

    def test_empty_reviewer(self):

        for value in ("", " ", None, 123):

            with self.subTest(value=value):

                self.assert_reservation_rejected(
                    self.make_reservation(
                        assigned_reviewer=value
                    ),
                    "Invalid assigned reviewer",
                )

    def test_placeholder_reviewer(self):

        for value in (
            "Pending",
            "REQUIRED",
            "Unknown",
            "None",
            "N/A",
            "TBD",
            "TODO",
            "Placeholder",
            "To Be Determined",
            "[Reviewer Name]",
        ):

            with self.subTest(value=value):

                self.assert_reservation_rejected(
                    self.make_reservation(
                        assigned_reviewer=value
                    ),
                    "Invalid assigned reviewer",
                )

    def test_multiline_reviewer(self):

        self.assert_reservation_rejected(
            self.make_reservation(
                assigned_reviewer="Reviewer\nSecond Line"
            ),
            "Invalid assigned reviewer",
        )

    def test_reviewer_surrounding_whitespace(self):

        for value in (
            " Reviewer",
            "Reviewer ",
            "Reviewer\n",
        ):

            with self.subTest(value=value):

                self.assert_reservation_rejected(
                    self.make_reservation(
                        assigned_reviewer=value
                    ),
                    "Invalid assigned reviewer",
                )

    def test_invalid_assignment_date(self):

        for value in (
            "",
            None,
            "2026-02-30",
            "2026-13-01",
            "01/15/2026",
            "20260115",
            "2026-1-15",
            "2026-01-15T12:00:00",
        ):

            with self.subTest(value=value):

                self.assert_reservation_rejected(
                    self.make_reservation(
                        assignment_date=value
                    ),
                    "Invalid review assignment date",
                )

    def test_valid_leap_year_assignment_date(self):

        registry = self.make_registry([
            self.make_reservation(
                assignment_date="2024-02-29"
            )
        ])

        self.assertEqual(
            validate_identifier_registry_data(registry),
            [],
        )

    # Repository-wide identifier uniqueness

    def test_multiple_unique_reservations(self):

        registry = self.make_registry([
            self.make_reservation(),
            self.make_reservation(
                review_record_id="BEEP-REV-TEST-002"
            ),
        ])

        self.assertEqual(
            validate_identifier_registry_data(registry),
            [],
        )

    def test_duplicate_identifier_same_home(self):

        registry = self.make_registry([
            self.make_reservation(),
            self.make_reservation(),
        ])

        self.assert_registry_rejected(
            registry,
            "Duplicate technical review record identifier",
        )

    def test_duplicate_identifier_different_home(self):

        registry = self.make_registry([
            self.make_reservation(),
            self.make_reservation(
                reference_home_id="BEEP-HOME-OTHER"
            ),
        ])

        self.assert_registry_rejected(
            registry,
            "Duplicate technical review record identifier",
        )

    def test_duplicate_identifier_different_version(self):

        registry = self.make_registry([
            self.make_reservation(),
            self.make_reservation(
                reference_home_version="2.0.0"
            ),
        ])

        self.assert_registry_rejected(
            registry,
            "Duplicate technical review record identifier",
        )

    def test_case_insensitive_duplicate_identifier(self):

        registry = self.make_registry([
            self.make_reservation(),
            self.make_reservation(
                review_record_id="beep-rev-test-001"
            ),
        ])

        self.assert_registry_rejected(
            registry,
            "Duplicate technical review record identifier",
        )

    # Registry file loading and preservation

    def test_valid_registry_file(self):

        self.write_registry(
            self.make_registry([
                self.make_reservation()
            ])
        )

        self.assertEqual(
            validate_review_identifiers(
                self.registry_path
            ),
            [],
        )

    def test_missing_registry_file(self):

        errors = validate_review_identifiers(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Unable to load identifier" in error
                for error in errors
            ),
            errors,
        )

    def test_malformed_json(self):

        self.registry_path.write_text(
            "{invalid json",
            encoding="utf-8",
        )

        errors = validate_review_identifiers(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Unable to load identifier" in error
                for error in errors
            ),
            errors,
        )

    def test_duplicate_json_keys(self):

        self.registry_path.write_text(
            '{"reservations": [], "reservations": []}',
            encoding="utf-8",
        )

        errors = validate_review_identifiers(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Duplicate JSON key: reservations" in error
                for error in errors
            ),
            errors,
        )

    def test_original_registry_not_modified(self):

        registry = self.make_registry([
            self.make_reservation()
        ])

        original = copy.deepcopy(registry)

        validate_identifier_registry_data(registry)

        self.assertEqual(
            registry,
            original,
        )


if __name__ == "__main__":
    unittest.main()
