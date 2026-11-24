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

from validate_review_document_reservations import (
    parse_review_document_path,
    discover_review_documents,
    validate_document_reservation_data,
    validate_review_document_reservations,
)


class TestReviewDocumentReservations(unittest.TestCase):

    def setUp(self):

        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp_directory.cleanup
        )

        self.root = Path(
            self.temp_directory.name
        )

        self.approvals_directory = (
            self.root / "approvals"
        )

        self.approvals_directory.mkdir()

        self.registry_path = (
            self.root
            / "reference-review-identifier-registry.json"
        )

        self.document_path = (
            "BEEP-HOME-TEST/1.0.0/"
            "technical-reviews/"
            "BEEP-REV-TEST-001.md"
        )

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

    def make_document(self, changes=None, omit=None):

        fields = {
            "Reference Home ID":
                "BEEP-HOME-TEST",

            "Reference Home Version":
                "1.0.0",

            "Technical Review Record ID":
                "BEEP-REV-TEST-001",

            "Technical Reviewer":
                "Fictional Test Reviewer",

            "Technical Review Date":
                "2026-01-20",

            "Technical Review Status":
                "COMPLETED",

            "Review Scope":
                "Fictional reference home review",

            "Review Findings":
                "Fictional test findings",

            "Review Recommendation":
                "RECOMMEND_APPROVAL",

            "Conflict-of-Interest Disclosure":
                "Fictional test disclosure",

            "Reviewed Content SHA-256":
                "a" * 64,

            "Supporting Evidence":
                "Fictional test evidence",
        }

        if changes is not None:
            fields.update(changes)

        if omit is not None:
            fields.pop(omit, None)

        return (
            "# Fictional Technical Review\n\n"
            + "\n".join(
                f"{field}: {value}"
                for field, value in fields.items()
            )
            + "\n"
        )

    def validate(
        self,
        content=None,
        reservations=None,
        relative_path=None,
    ):

        if content is None:
            content = self.make_document()

        if reservations is None:
            reservations = [
                self.make_reservation()
            ]

        if relative_path is None:
            relative_path = self.document_path

        return validate_document_reservation_data(
            {
                relative_path: content,
            },
            self.make_registry(reservations),
        )

    def assert_rejected(
        self,
        errors,
        message=None,
    ):

        self.assertTrue(errors)

        if message is not None:

            self.assertTrue(
                any(
                    message in error
                    for error in errors
                ),
                errors,
            )

    def write_registry(self, reservations=None):

        self.registry_path.write_text(
            json.dumps(
                self.make_registry(reservations)
            ),
            encoding="utf-8",
        )

    def write_document(
        self,
        relative_path=None,
        content=None,
    ):

        if relative_path is None:
            relative_path = self.document_path

        if content is None:
            content = self.make_document()

        path = (
            self.approvals_directory
            / relative_path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            content,
            encoding="utf-8",
        )

        return path

    def validate_files(self):

        return validate_review_document_reservations(
            self.registry_path,
            self.approvals_directory,
        )

    # Valid document and reservation scenarios

    def test_01_matching_document_and_reservation(self):

        self.assertEqual(
            self.validate(),
            [],
        )

    def test_02_empty_registry_without_documents(self):

        self.assertEqual(
            validate_document_reservation_data(
                {},
                self.make_registry(),
            ),
            [],
        )

    def test_03_abandoned_reservation_without_document(self):

        self.assertEqual(
            validate_document_reservation_data(
                {},
                self.make_registry([
                    self.make_reservation()
                ]),
            ),
            [],
        )

    def test_04_same_day_assignment_and_completion(self):

        self.assertEqual(
            self.validate(
                content=self.make_document({
                    "Technical Review Date":
                        "2026-01-15",
                })
            ),
            [],
        )

    def test_05_revisions_required_recommendation(self):

        self.assertEqual(
            self.validate(
                content=self.make_document({
                    "Review Recommendation":
                        "REVISIONS_REQUIRED",
                })
            ),
            [],
        )

    def test_06_multiple_independent_documents(self):

        second_id = "BEEP-REV-TEST-002"

        second_path = (
            "BEEP-HOME-TEST/1.0.0/"
            f"technical-reviews/{second_id}.md"
        )

        documents = {
            self.document_path:
                self.make_document(),

            second_path:
                self.make_document({
                    "Technical Review Record ID":
                        second_id,
                }),
        }

        reservations = [
            self.make_reservation(),

            self.make_reservation(
                review_record_id=second_id,
            ),
        ]

        self.assertEqual(
            validate_document_reservation_data(
                documents,
                self.make_registry(reservations),
            ),
            [],
        )

    def test_07_document_with_abandoned_reservation(self):

        reservations = [
            self.make_reservation(),

            self.make_reservation(
                review_record_id="BEEP-REV-TEST-002",
            ),
        ]

        self.assertEqual(
            self.validate(
                reservations=reservations,
            ),
            [],
        )

    def test_08_original_inputs_not_modified(self):

        documents = {
            self.document_path:
                self.make_document(),
        }

        registry = self.make_registry([
            self.make_reservation()
        ])

        original = copy.deepcopy((
            documents,
            registry,
        ))

        validate_document_reservation_data(
            documents,
            registry,
        )

        self.assertEqual(
            (documents, registry),
            original,
        )

    # Reservation and metadata matching

    def test_09_document_without_reservation(self):

        self.assert_rejected(
            self.validate(reservations=[]),
            "has no permanent identifier reservation",
        )

    def test_10_unrecognized_document_identifier(self):

        self.assert_rejected(
            self.validate(
                relative_path=(
                    "BEEP-HOME-TEST/1.0.0/"
                    "technical-reviews/"
                    "BEEP-REV-UNKNOWN.md"
                )
            ),
            "has no permanent identifier reservation",
        )

    def test_11_filename_capitalization_mismatch(self):

        self.assert_rejected(
            self.validate(
                relative_path=(
                    "BEEP-HOME-TEST/1.0.0/"
                    "technical-reviews/"
                    "beep-rev-test-001.md"
                )
            ),
            "does not match reserved review_record_id",
        )

    def test_12_home_directory_mismatch(self):

        self.assert_rejected(
            self.validate(
                relative_path=(
                    "BEEP-HOME-OTHER/1.0.0/"
                    "technical-reviews/"
                    "BEEP-REV-TEST-001.md"
                )
            ),
            "does not match reserved reference_home_id",
        )

    def test_13_version_directory_mismatch(self):

        self.assert_rejected(
            self.validate(
                relative_path=(
                    "BEEP-HOME-TEST/2.0.0/"
                    "technical-reviews/"
                    "BEEP-REV-TEST-001.md"
                )
            ),
            "does not match reserved reference_home_version",
        )

    def test_14_document_home_id_mismatch(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Reference Home ID":
                        "BEEP-HOME-OTHER",
                })
            ),
            "does not match reserved Reference Home ID",
        )

    def test_15_document_version_mismatch(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Reference Home Version":
                        "2.0.0",
                })
            ),
            "does not match reserved Reference Home Version",
        )

    def test_16_document_identifier_mismatch(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Technical Review Record ID":
                        "BEEP-REV-TEST-002",
                })
            ),
            "does not match reserved Technical Review Record ID",
        )

    def test_17_document_reviewer_mismatch(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Technical Reviewer":
                        "Different Reviewer",
                })
            ),
            "does not match reserved Technical Reviewer",
        )

    def test_18_reviewer_capitalization_mismatch(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Technical Reviewer":
                        "fictional test reviewer",
                })
            ),
            "does not match reserved Technical Reviewer",
        )

    def test_19_duplicate_identifier_across_paths(self):

        documents = {
            self.document_path:
                self.make_document(),

            (
                "BEEP-HOME-OTHER/1.0.0/"
                "technical-reviews/"
                "BEEP-REV-TEST-001.md"
            ):
                self.make_document(),
        }

        self.assert_rejected(
            validate_document_reservation_data(
                documents,
                self.make_registry([
                    self.make_reservation()
                ]),
            ),
            "appears in multiple document paths",
        )

    def test_20_case_insensitive_duplicate_identifier(self):

        documents = {
            self.document_path:
                self.make_document(),

            (
                "BEEP-HOME-TEST/1.0.0/"
                "technical-reviews/"
                "beep-rev-test-001.md"
            ):
                self.make_document(),
        }

        self.assert_rejected(
            validate_document_reservation_data(
                documents,
                self.make_registry([
                    self.make_reservation()
                ]),
            ),
            "appears in multiple document paths",
        )

    # Document content and chronology

    def test_21_completion_before_assignment(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Technical Review Date":
                        "2026-01-14",
                })
            ),
            "completion date cannot precede",
        )

    def test_22_invalid_completion_date(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Technical Review Date":
                        "2026-02-30",
                })
            ),
            "Invalid technical review document completion date",
        )

    def test_23_noncanonical_completion_date(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Technical Review Date":
                        "20260120",
                })
            ),
            "Invalid technical review document completion date",
        )

    def test_24_incomplete_review_status(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Technical Review Status":
                        "IN_PROGRESS",
                })
            ),
            "must have COMPLETED review status",
        )

    def test_25_invalid_recommendation(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Review Recommendation":
                        "INVALID",
                })
            ),
            "Invalid technical review document recommendation",
        )

    def test_26_invalid_fingerprint_length(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Reviewed Content SHA-256":
                        "a" * 63,
                })
            ),
            "Invalid reviewed content SHA-256 fingerprint",
        )

    def test_27_invalid_fingerprint_characters(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Reviewed Content SHA-256":
                        "z" * 64,
                })
            ),
            "Invalid reviewed content SHA-256 fingerprint",
        )

    def test_28_missing_required_metadata(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document(
                    omit="Supporting Evidence",
                )
            ),
            "Missing required field",
        )

    def test_29_duplicate_required_metadata(self):

        content = (
            self.make_document()
            + "Technical Reviewer: Different Reviewer\n"
        )

        self.assert_rejected(
            self.validate(content=content),
            "Duplicate required field",
        )

    def test_30_placeholder_metadata(self):

        self.assert_rejected(
            self.validate(
                content=self.make_document({
                    "Review Findings":
                        "TBD",
                })
            ),
            "Invalid or placeholder value",
        )

    # Path and filesystem validation

    def test_31_valid_document_path_parsing(self):

        self.assertEqual(
            parse_review_document_path(
                self.document_path
            ),
            (
                "BEEP-HOME-TEST",
                "1.0.0",
                "BEEP-REV-TEST-001",
            ),
        )

    def test_32_invalid_document_directory_structure(self):

        with self.assertRaises(ValueError):

            parse_review_document_path(
                "technical-reviews/"
                "BEEP-REV-TEST-001.md"
            )

    def test_33_invalid_document_extension(self):

        with self.assertRaises(ValueError):

            parse_review_document_path(
                "BEEP-HOME-TEST/1.0.0/"
                "technical-reviews/"
                "BEEP-REV-TEST-001.txt"
            )

    def test_34_invalid_version_in_path(self):

        with self.assertRaises(ValueError):

            parse_review_document_path(
                "BEEP-HOME-TEST/01.0.0/"
                "technical-reviews/"
                "BEEP-REV-TEST-001.md"
            )

    def test_35_discovery_ignores_approval_record(self):

        self.write_document(
            relative_path=(
                "BEEP-HOME-TEST/1.0.0/"
                "approval-record.md"
            ),
            content="Fictional approval document",
        )

        self.write_document()

        documents, errors = (
            discover_review_documents(
                self.approvals_directory
            )
        )

        self.assertEqual(errors, [])

        self.assertEqual(
            set(documents),
            {self.document_path},
        )

    def test_36_nested_review_directory_rejected(self):

        self.write_document(
            relative_path=(
                "BEEP-HOME-TEST/1.0.0/"
                "technical-reviews/nested/"
                "BEEP-REV-TEST-001.md"
            )
        )

        _, errors = discover_review_documents(
            self.approvals_directory
        )

        self.assert_rejected(
            errors,
            "Unexpected nested directory",
        )

    def test_37_document_symlink_rejected(self):

        document = self.write_document()

        target = (
            self.root / "external-document.md"
        )

        document.rename(target)

        document.symlink_to(target)

        self.write_registry([
            self.make_reservation()
        ])

        self.assert_rejected(
            self.validate_files(),
            "cannot be a symbolic link",
        )

    def test_38_missing_approvals_directory(self):

        self.write_registry()

        self.approvals_directory.rmdir()

        self.assert_rejected(
            self.validate_files(),
            "does not exist as a regular directory",
        )

    def test_39_invalid_identifier_registry(self):

        self.registry_path.write_text(
            '{"invalid": true}',
            encoding="utf-8",
        )

        self.assert_rejected(
            self.validate_files(),
            "Identifier registry:",
        )

    def test_40_integrated_document_validation(self):

        self.write_registry([
            self.make_reservation()
        ])

        self.write_document()

        self.assertEqual(
            self.validate_files(),
            [],
        )


if __name__ == "__main__":
    unittest.main()
