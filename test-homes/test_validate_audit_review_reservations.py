import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_reference_audit import (
    AUDIT_DESCRIPTION,
    AUDIT_STATUS,
    CURRENT_SCHEMA_VERSION,
    GOVERNANCE_AUTHORITY,
    LEGACY_SCHEMA_VERSION,
    REPOSITORY_NAME,
    TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    validate_live_audit_data,
)

from validate_review_identifiers import (
    EXPECTED_POLICY,
    REGISTRY_NAME,
    SCHEMA_VERSION,
    validate_identifier_registry_data,
)

from validate_audit_review_reservations import (
    validate_audit_review_reservations,
    validate_audit_review_reservations_data,
)


class TestAuditReviewReservations(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)

        self.audit_path = (
            self.root
            / "reference-approval-audit.json"
        )

        self.identifier_path = (
            self.root
            / "reference-review-identifier-registry.json"
        )

    def make_record(
        self,
        decision="APPROVED",
        record_id="BEEP-AUDIT-TEST-001",
    ):

        return {
            "record_id": record_id,
            "reference_home_id": "BEEP-HOME-TEST",
            "reference_home_version": "1.0.0",
            "decision": decision,
            "reviewer": "Fictional Test Reviewer",
            "approval_authority": GOVERNANCE_AUTHORITY,
            "evidence": "Fictional supporting evidence",
            "pull_request": "TEST-PR-001",
            "board_resolution_reference": "BEEP-RES-TEST-001",
            "decision_date": "2026-01-25",
            "technical_review_record": "BEEP-REV-TEST-001",
            "technical_review_date": "2026-01-20",
            "technical_review_sha256": "a" * 64,
            "reviewed_content_sha256": "b" * 64,
        }

    def make_reservation(
        self,
        record_id="BEEP-REV-TEST-001",
    ):

        return {
            "review_record_id": record_id,
            "reference_home_id": "BEEP-HOME-TEST",
            "reference_home_version": "1.0.0",
            "assigned_reviewer": "Fictional Test Reviewer",
            "assignment_date": "2026-01-10",
        }

    def make_audit(self, records=None):

        return {
            "audit_schema_version": CURRENT_SCHEMA_VERSION,
            "repository": REPOSITORY_NAME,
            "audit_status": AUDIT_STATUS,
            "description": AUDIT_DESCRIPTION,
            "records": [] if records is None else records,
        }

    def make_identifier_registry(
        self,
        reservations=None,
    ):

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

    def make_null_evidence_record(self):

        record = self.make_record("REJECTED")

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            record[field] = None

        return record

    def validate(self, audit, identifiers):

        return validate_audit_review_reservations_data(
            audit,
            identifiers,
        )

    def assert_accepted(self, audit, identifiers):

        self.assertEqual(
            validate_live_audit_data(audit),
            [],
        )

        self.assertEqual(
            validate_identifier_registry_data(
                identifiers
            ),
            [],
        )

        self.assertEqual(
            self.validate(audit, identifiers),
            [],
        )

    def assert_rejected(
        self,
        audit,
        identifiers,
        expected,
    ):

        errors = self.validate(
            audit,
            identifiers,
        )

        self.assertTrue(
            any(
                expected in error
                for error in errors
            ),
            f"Expected {expected!r}; got {errors}",
        )

    def assert_matching_rejected(
        self,
        audit,
        identifiers,
        expected,
    ):

        self.assertEqual(
            validate_live_audit_data(audit),
            [],
            "Audit schema must remain valid",
        )

        self.assertEqual(
            validate_identifier_registry_data(
                identifiers
            ),
            [],
            "Reservation schema must remain valid",
        )

        self.assert_rejected(
            audit,
            identifiers,
            expected,
        )

    def make_valid_fixture(
        self,
        decision="APPROVED",
    ):

        record = self.make_record(decision)

        reservation = self.make_reservation()

        audit = self.make_audit([record])

        identifiers = self.make_identifier_registry(
            [reservation]
        )

        self.assert_accepted(
            audit,
            identifiers,
        )

        return (
            audit,
            identifiers,
            record,
            reservation,
        )

    def save_registries(
        self,
        audit,
        identifiers,
    ):

        self.audit_path.write_text(
            json.dumps(audit, indent=2),
            encoding="utf-8",
        )

        self.identifier_path.write_text(
            json.dumps(identifiers, indent=2),
            encoding="utf-8",
        )

    def validate_files(self):

        return validate_audit_review_reservations(
            self.audit_path,
            self.identifier_path,
        )

    def assert_file_rejected(self, expected):

        errors = self.validate_files()

        self.assertTrue(
            any(
                expected in error
                for error in errors
            ),
            f"Expected {expected!r}; got {errors}",
        )

    # CATEGORY 1
    # VALID RESERVATION MATCHING

    def test_01_empty_valid_registries(self):

        self.assert_accepted(
            self.make_audit(),
            self.make_identifier_registry(),
        )

    def test_02_approved_matching_reservation(self):

        self.make_valid_fixture("APPROVED")

    def test_03_retired_matching_reservation(self):

        self.make_valid_fixture("RETIRED")

    def test_04_rejected_matching_reservation(self):

        self.make_valid_fixture("REJECTED")

    def test_05_multiple_decisions_same_reservation(self):

        approved = self.make_record(
            "APPROVED",
            "BEEP-AUDIT-TEST-001",
        )

        retired = self.make_record(
            "RETIRED",
            "BEEP-AUDIT-TEST-002",
        )

        retired["decision_date"] = "2026-02-01"

        self.assert_accepted(
            self.make_audit(
                [approved, retired]
            ),
            self.make_identifier_registry(
                [self.make_reservation()]
            ),
        )

    # CATEGORY 2
    # IDENTIFIER MATCHING AND UNIQUENESS

    def test_06_missing_reservation(self):

        record = self.make_record()

        self.assert_matching_rejected(
            self.make_audit([record]),
            self.make_identifier_registry(),
            "Missing permanent technical review "
            "identifier reservation",
        )

    def test_07_unrelated_reservation(self):

        record = self.make_record()

        reservation = self.make_reservation(
            "BEEP-REV-OTHER"
        )

        self.assert_matching_rejected(
            self.make_audit([record]),
            self.make_identifier_registry(
                [reservation]
            ),
            "Missing permanent technical review "
            "identifier reservation",
        )

    def test_08_identifier_capitalization_mismatch(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        record["technical_review_record"] = (
            record["technical_review_record"].lower()
        )

        self.assert_matching_rejected(
            audit,
            identifiers,
            "reservation mismatch: "
            "technical_review_record",
        )

    def test_09_duplicate_exact_reservation_identifier(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        identifiers["reservations"].append(
            copy.deepcopy(reservation)
        )

        self.assert_rejected(
            audit,
            identifiers,
            "Duplicate technical review record identifier",
        )

    def test_10_duplicate_casefold_reservation_identifier(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        duplicate = copy.deepcopy(reservation)

        duplicate["review_record_id"] = (
            duplicate["review_record_id"].lower()
        )

        identifiers["reservations"].append(
            duplicate
        )

        self.assert_rejected(
            audit,
            identifiers,
            "Duplicate technical review record identifier",
        )

    # CATEGORY 3
    # HOME, VERSION, AND REVIEWER CONSISTENCY

    def test_11_reference_home_mismatch(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        record["reference_home_id"] = (
            "BEEP-HOME-OTHER"
        )

        self.assert_matching_rejected(
            audit,
            identifiers,
            "reservation mismatch: reference_home_id",
        )

    def test_12_reference_home_version_mismatch(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        record["reference_home_version"] = "2.0.0"

        self.assert_matching_rejected(
            audit,
            identifiers,
            "reservation mismatch: "
            "reference_home_version",
        )

    def test_13_assigned_reviewer_mismatch(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        record["reviewer"] = (
            "Different Fictional Reviewer"
        )

        self.assert_matching_rejected(
            audit,
            identifiers,
            "reservation mismatch: reviewer",
        )

    def test_14_reviewer_capitalization_mismatch(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        record["reviewer"] = (
            record["reviewer"].lower()
        )

        self.assert_matching_rejected(
            audit,
            identifiers,
            "reservation mismatch: reviewer",
        )

    def test_15_multiple_matching_errors_reported(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        record["reference_home_id"] = (
            "BEEP-HOME-OTHER"
        )

        record["reference_home_version"] = "2.0.0"

        record["reviewer"] = (
            "Different Fictional Reviewer"
        )

        self.assertEqual(
            validate_live_audit_data(audit),
            [],
        )

        self.assertEqual(
            validate_identifier_registry_data(
                identifiers
            ),
            [],
        )

        errors = self.validate(
            audit,
            identifiers,
        )

        self.assertEqual(
            len(errors),
            3,
        )

        for field in (
            "reference_home_id",
            "reference_home_version",
            "reviewer",
        ):

            with self.subTest(field=field):

                self.assertTrue(
                    any(
                        f"reservation mismatch: {field}"
                        in error
                        for error in errors
                    ),
                    errors,
                )

    # CATEGORY 4
    # CHRONOLOGICAL ENFORCEMENT

    def test_16_review_before_assignment(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        reservation["assignment_date"] = (
            "2026-01-21"
        )

        self.assert_matching_rejected(
            audit,
            identifiers,
            "Technical review completion date "
            "cannot precede reservation assignment date",
        )

    def test_17_decision_before_review_completion(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        record["decision_date"] = "2026-01-19"

        self.assert_rejected(
            audit,
            identifiers,
            "Audit decision date cannot precede "
            "the technical review completion date",
        )

    def test_18_decision_before_assignment(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        reservation["assignment_date"] = (
            "2026-01-26"
        )

        self.assert_matching_rejected(
            audit,
            identifiers,
            "Audit decision date cannot precede "
            "reservation assignment date",
        )

    def test_19_same_day_chronology_accepted(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        reservation["assignment_date"] = (
            "2026-01-20"
        )

        record["decision_date"] = "2026-01-20"

        self.assert_accepted(
            audit,
            identifiers,
        )

    def test_20_invalid_assignment_dates(self):

        for invalid_date in (
            "2026-02-30",
            "2026-1-10",
            "20260110",
            "",
            None,
        ):

            with self.subTest(
                assignment_date=invalid_date
            ):

                audit, identifiers, record, reservation = (
                    self.make_valid_fixture()
                )

                reservation["assignment_date"] = (
                    invalid_date
                )

                self.assert_rejected(
                    audit,
                    identifiers,
                    "Invalid review assignment date",
                )

    # CATEGORY 5
    # CONDITIONAL EVIDENCE REQUIREMENTS

    def test_21_rejected_all_null_evidence(self):

        record = self.make_null_evidence_record()

        self.assert_accepted(
            self.make_audit([record]),
            self.make_identifier_registry(),
        )

    def test_22_rejected_partial_evidence(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture("REJECTED")
        )

        record["technical_review_sha256"] = None

        self.assert_rejected(
            audit,
            identifiers,
            "REJECTED audit decisions require either "
            "complete technical review evidence "
            "or all-null evidence",
        )

    def test_23_approved_null_evidence(self):

        record = self.make_null_evidence_record()

        record["decision"] = "APPROVED"

        self.assert_rejected(
            self.make_audit([record]),
            self.make_identifier_registry(),
            "APPROVED audit decisions require "
            "complete technical review evidence",
        )

    def test_24_retired_null_evidence(self):

        record = self.make_null_evidence_record()

        record["decision"] = "RETIRED"

        self.assert_rejected(
            self.make_audit([record]),
            self.make_identifier_registry(),
            "RETIRED audit decisions require "
            "complete technical review evidence",
        )

    def test_25_mixed_complete_and_null_evidence(self):

        approved = self.make_record()

        rejected = self.make_null_evidence_record()

        rejected["record_id"] = (
            "BEEP-AUDIT-TEST-002"
        )

        self.assert_accepted(
            self.make_audit(
                [approved, rejected]
            ),
            self.make_identifier_registry(
                [self.make_reservation()]
            ),
        )

    # CATEGORY 6
    # RESERVATION REGISTRY ENFORCEMENT

    def test_26_invalid_reservation_registry_root(self):

        for invalid in (
            None,
            [],
            "invalid",
        ):

            with self.subTest(registry=invalid):

                self.assert_rejected(
                    self.make_audit(),
                    invalid,
                    "Identifier registry must be an object",
                )

    def test_27_invalid_reservation_policy(self):

        identifiers = self.make_identifier_registry()

        identifiers["reservation_policy"][
            "identifier_reuse_allowed"
        ] = True

        self.assert_rejected(
            self.make_audit(),
            identifiers,
            "Invalid reservation policy field: "
            "identifier_reuse_allowed",
        )

    def test_28_invalid_reservation_metadata(self):

        identifiers = self.make_identifier_registry()

        identifiers["governance_authority"] = (
            "Unauthorized Organization"
        )

        self.assert_rejected(
            self.make_audit(),
            identifiers,
            "Invalid registry field: governance_authority",
        )

    def test_29_missing_required_reservation_field(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        del reservation["assigned_reviewer"]

        self.assert_rejected(
            audit,
            identifiers,
            "Missing reservation field: assigned_reviewer",
        )

    def test_30_invalid_reservation_array(self):

        identifiers = self.make_identifier_registry()

        identifiers["reservations"] = {}

        self.assert_rejected(
            self.make_audit(),
            identifiers,
            "Identifier reservations must be a list",
        )

    # CATEGORY 7
    # AUDIT SCHEMA AND HISTORICAL CONSISTENCY

    def test_31_legacy_live_audit_schema(self):

        audit = self.make_audit()

        audit["audit_schema_version"] = (
            LEGACY_SCHEMA_VERSION
        )

        self.assert_rejected(
            audit,
            self.make_identifier_registry(),
            "Live audit registry must use schema version",
        )

    def test_32_missing_audit_review_evidence_field(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        del record["technical_review_record"]

        self.assert_rejected(
            audit,
            identifiers,
            "Missing technical_review_record",
        )

    def test_33_historical_reservation_remains_valid(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture("REJECTED")
        )

        later_reservation = self.make_reservation(
            "BEEP-REV-TEST-002"
        )

        later_reservation["assigned_reviewer"] = (
            "Later Fictional Reviewer"
        )

        later_reservation["assignment_date"] = (
            "2026-02-10"
        )

        identifiers["reservations"].append(
            later_reservation
        )

        self.assert_accepted(
            audit,
            identifiers,
        )

    def test_34_multiple_independent_reservations(self):

        first_record = self.make_record()

        first_reservation = self.make_reservation()

        second_record = self.make_record(
            "APPROVED",
            "BEEP-AUDIT-TEST-002",
        )

        second_record["technical_review_record"] = (
            "BEEP-REV-TEST-002"
        )

        second_record["reference_home_version"] = (
            "1.1.0"
        )

        second_reservation = self.make_reservation(
            "BEEP-REV-TEST-002"
        )

        second_reservation[
            "reference_home_version"
        ] = "1.1.0"

        self.assert_accepted(
            self.make_audit(
                [first_record, second_record]
            ),
            self.make_identifier_registry(
                [first_reservation, second_reservation]
            ),
        )

    def test_35_validation_does_not_modify_registries(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        original_audit = copy.deepcopy(audit)

        original_identifiers = copy.deepcopy(
            identifiers
        )

        self.assert_accepted(
            audit,
            identifiers,
        )

        self.assertEqual(
            audit,
            original_audit,
        )

        self.assertEqual(
            identifiers,
            original_identifiers,
        )

    # CATEGORY 8
    # FILE-BASED VALIDATION AND SECURITY

    def test_36_valid_registry_files(self):

        audit, identifiers, record, reservation = (
            self.make_valid_fixture()
        )

        self.save_registries(
            audit,
            identifiers,
        )

        self.assertEqual(
            self.validate_files(),
            [],
        )

    def test_37_missing_registry_files(self):

        for missing_file in (
            self.audit_path,
            self.identifier_path,
        ):

            with self.subTest(
                missing_file=missing_file
            ):

                self.save_registries(
                    self.make_audit(),
                    self.make_identifier_registry(),
                )

                missing_file.unlink()

                self.assert_file_rejected(
                    "Unable to validate audit technical "
                    "review reservations"
                )

    def test_38_malformed_or_duplicate_json_keys(self):

        for target in (
            self.audit_path,
            self.identifier_path,
        ):

            for content, expected in (
                (
                    "{invalid JSON",
                    "Unable to validate audit technical "
                    "review reservations",
                ),
                (
                    '{"duplicate": 1, "duplicate": 2}',
                    "Duplicate JSON key: duplicate",
                ),
            ):

                with self.subTest(
                    target=target,
                    content=content,
                ):

                    self.save_registries(
                        self.make_audit(),
                        self.make_identifier_registry(),
                    )

                    target.write_text(
                        content,
                        encoding="utf-8",
                    )

                    self.assert_file_rejected(
                        expected
                    )

    def test_39_audit_registry_symbolic_link(self):

        self.save_registries(
            self.make_audit(),
            self.make_identifier_registry(),
        )

        target = self.root / "external-audit.json"

        self.audit_path.rename(target)

        self.audit_path.symlink_to(target)

        self.assertEqual(
            self.validate_files(),
            [
                "Audit registry cannot be "
                "a symbolic link"
            ],
        )

    def test_40_identifier_registry_symbolic_link(self):

        self.save_registries(
            self.make_audit(),
            self.make_identifier_registry(),
        )

        target = (
            self.root / "external-identifiers.json"
        )

        self.identifier_path.rename(target)

        self.identifier_path.symlink_to(target)

        self.assertEqual(
            self.validate_files(),
            [
                "Identifier reservation registry "
                "cannot be a symbolic link"
            ],
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
