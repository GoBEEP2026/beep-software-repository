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
    validate_audit,
    validate_audit_data,
)


class TestExpandedAuditSchema(unittest.TestCase):

    def make_record(self, decision="APPROVED"):

        return {
            "record_id": "BEEP-AUDIT-TEST-001",
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

    def make_registry(
        self,
        records=None,
        schema_version=CURRENT_SCHEMA_VERSION,
    ):

        return {
            "audit_schema_version": schema_version,
            "repository": REPOSITORY_NAME,
            "audit_status": AUDIT_STATUS,
            "description": AUDIT_DESCRIPTION,
            "records": [] if records is None else records,
        }

    def make_null_evidence_record(
        self,
        decision="REJECTED",
    ):

        record = self.make_record(decision)

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:
            record[field] = None

        return record

    def assert_accepted(self, registry):

        errors = validate_audit_data(registry)

        self.assertEqual(errors, [])

    def assert_rejected(self, registry, expected_message):

        errors = validate_audit_data(registry)

        self.assertTrue(
            errors,
            "Expected validation failure",
        )

        self.assertTrue(
            any(
                expected_message in error
                for error in errors
            ),
            f"Expected {expected_message!r}; got {errors}",
        )

    def test_01_valid_empty_current_registry(self):

        self.assert_accepted(
            self.make_registry()
        )

    def test_02_valid_empty_legacy_registry(self):

        self.assert_accepted(
            self.make_registry(
                schema_version=LEGACY_SCHEMA_VERSION
            )
        )

    def test_03_valid_legacy_record(self):

        record = self.make_record()

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:
            del record[field]

        self.assert_accepted(
            self.make_registry(
                [record],
                schema_version=LEGACY_SCHEMA_VERSION,
            )
        )

    def test_04_valid_approved_record(self):

        self.assert_accepted(
            self.make_registry(
                [self.make_record("APPROVED")]
            )
        )

    def test_05_valid_rejected_with_complete_evidence(self):

        self.assert_accepted(
            self.make_registry(
                [self.make_record("REJECTED")]
            )
        )

    def test_06_valid_rejected_with_null_evidence(self):

        self.assert_accepted(
            self.make_registry(
                [self.make_null_evidence_record()]
            )
        )

    def test_07_valid_retired_record(self):

        self.assert_accepted(
            self.make_registry(
                [self.make_record("RETIRED")]
            )
        )

    def test_08_valid_same_day_review_and_decision(self):

        record = self.make_record()

        record["decision_date"] = (
            record["technical_review_date"]
        )

        self.assert_accepted(
            self.make_registry([record])
        )

    def test_09_valid_multiple_unique_records(self):

        first = self.make_record()

        second = self.make_record("REJECTED")

        second["record_id"] = "BEEP-AUDIT-TEST-002"

        self.assert_accepted(
            self.make_registry([first, second])
        )

    def test_10_validation_does_not_modify_input(self):

        registry = self.make_registry(
            [self.make_record()]
        )

        original = copy.deepcopy(registry)

        self.assert_accepted(registry)

        self.assertEqual(registry, original)

    def test_11_approved_null_evidence_rejected(self):

        record = self.make_null_evidence_record(
            "APPROVED"
        )

        self.assert_rejected(
            self.make_registry([record]),
            "APPROVED audit decisions require",
        )

    def test_12_retired_null_evidence_rejected(self):

        record = self.make_null_evidence_record(
            "RETIRED"
        )

        self.assert_rejected(
            self.make_registry([record]),
            "RETIRED audit decisions require",
        )

    def test_13_rejected_partial_evidence_rejected(self):

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            with self.subTest(field=field):

                record = self.make_record("REJECTED")

                record[field] = None

                self.assert_rejected(
                    self.make_registry([record]),
                    "either complete technical review",
                )

    def test_14_missing_evidence_field_rejected(self):

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            with self.subTest(field=field):

                record = self.make_record()

                del record[field]

                self.assert_rejected(
                    self.make_registry([record]),
                    f"Missing {field}",
                )

    def test_15_rejected_missing_null_field_rejected(self):

        record = self.make_null_evidence_record()

        del record["technical_review_date"]

        self.assert_rejected(
            self.make_registry([record]),
            "Missing technical_review_date",
        )

    def test_16_invalid_technical_review_identifier(self):

        for value in (
            "",
            "../REVIEW",
            "REVIEW 001",
            123,
        ):

            with self.subTest(value=value):

                record = self.make_record()

                record["technical_review_record"] = value

                self.assert_rejected(
                    self.make_registry([record]),
                    "Invalid technical review record identifier",
                )

    def test_17_invalid_review_completion_date(self):

        record = self.make_record()

        record["technical_review_date"] = "2026-02-30"

        self.assert_rejected(
            self.make_registry([record]),
            "Invalid technical review completion date",
        )

    def test_18_noncanonical_review_completion_date(self):

        record = self.make_record()

        record["technical_review_date"] = "20260120"

        self.assert_rejected(
            self.make_registry([record]),
            "Invalid technical review completion date",
        )

    def test_19_invalid_document_checksum(self):

        for value in (
            "a" * 63,
            "a" * 65,
            "g" * 64,
            "A" * 64,
            123,
        ):

            with self.subTest(value=value):

                record = self.make_record()

                record["technical_review_sha256"] = value

                self.assert_rejected(
                    self.make_registry([record]),
                    "Invalid technical review document",
                )

    def test_20_invalid_reviewed_content_fingerprint(self):

        for value in (
            "b" * 63,
            "b" * 65,
            "z" * 64,
            "B" * 64,
            [],
        ):

            with self.subTest(value=value):

                record = self.make_record()

                record["reviewed_content_sha256"] = value

                self.assert_rejected(
                    self.make_registry([record]),
                    "Invalid reviewed content",
                )

    def test_21_decision_before_review_completion(self):

        for decision in (
            "APPROVED",
            "REJECTED",
            "RETIRED",
        ):

            with self.subTest(decision=decision):

                record = self.make_record(decision)

                record["decision_date"] = "2026-01-19"

                self.assert_rejected(
                    self.make_registry([record]),
                    "Audit decision date cannot precede",
                )

    def test_22_invalid_decision_date(self):

        record = self.make_record()

        record["decision_date"] = "2026-13-01"

        self.assert_rejected(
            self.make_registry([record]),
            "Invalid decision date",
        )

    def test_23_invalid_board_authority(self):

        record = self.make_record()

        record["approval_authority"] = "Unauthorized Reviewer"

        self.assert_rejected(
            self.make_registry([record]),
            "Invalid approval authority",
        )

    def test_24_invalid_decision_type(self):

        for value in (
            "PENDING",
            "approved",
            [],
            {},
            None,
        ):

            with self.subTest(value=value):

                record = self.make_record()

                record["decision"] = value

                self.assert_rejected(
                    self.make_registry([record]),
                    "Invalid decision",
                )

    def test_25_invalid_audit_record_identifier(self):

        record = self.make_record()

        record["record_id"] = "../AUDIT"

        self.assert_rejected(
            self.make_registry([record]),
            "Invalid audit record ID",
        )

    def test_26_invalid_reference_home_identifier(self):

        record = self.make_record()

        record["reference_home_id"] = "HOME/001"

        self.assert_rejected(
            self.make_registry([record]),
            "Invalid reference home ID",
        )

    def test_27_noncanonical_reference_home_version(self):

        for value in (
            "01.0.0",
            "1.00.0",
            "1.0.00",
            "1.0",
            "v1.0.0",
        ):

            with self.subTest(value=value):

                record = self.make_record()

                record["reference_home_version"] = value

                self.assert_rejected(
                    self.make_registry([record]),
                    "Invalid reference home version",
                )

    def test_28_duplicate_audit_record_identifier(self):

        first = self.make_record()

        second = copy.deepcopy(first)

        self.assert_rejected(
            self.make_registry([first, second]),
            "Duplicate record ID",
        )

    def test_29_case_insensitive_duplicate_identifier(self):

        first = self.make_record()

        second = copy.deepcopy(first)

        second["record_id"] = (
            first["record_id"].lower()
        )

        self.assert_rejected(
            self.make_registry([first, second]),
            "Duplicate record ID",
        )

    def test_30_placeholder_administrative_values(self):

        for field in (
            "reviewer",
            "evidence",
            "pull_request",
            "board_resolution_reference",
        ):

            for value in (
                "",
                "PENDING",
                "TBD",
                "[PLACEHOLDER]",
                " leading space",
                "line one\nline two",
            ):

                with self.subTest(
                    field=field,
                    value=value,
                ):

                    record = self.make_record()

                    record[field] = value

                    self.assert_rejected(
                        self.make_registry([record]),
                        f"Missing or invalid {field}",
                    )

    def test_31_missing_administrative_field(self):

        record = self.make_record()

        del record["board_resolution_reference"]

        self.assert_rejected(
            self.make_registry([record]),
            "Missing board_resolution_reference",
        )

    def test_32_unexpected_record_field(self):

        record = self.make_record()

        record["unauthorized_field"] = "unexpected"

        self.assert_rejected(
            self.make_registry([record]),
            "Unexpected audit record field",
        )

    def test_33_invalid_schema_version(self):

        for value in (
            "2.0.0",
            "1.2.0",
            [],
            None,
        ):

            with self.subTest(value=value):

                registry = self.make_registry()

                registry["audit_schema_version"] = value

                self.assert_rejected(
                    registry,
                    "Invalid audit schema version",
                )

    def test_34_invalid_registry_status(self):

        registry = self.make_registry()

        registry["audit_status"] = "APPROVED"

        self.assert_rejected(
            registry,
            "Unsupported audit status",
        )

    def test_35_invalid_repository_name(self):

        registry = self.make_registry()

        registry["repository"] = "Unauthorized Repository"

        self.assert_rejected(
            registry,
            "Invalid audit repository name",
        )

    def test_36_invalid_registry_description(self):

        registry = self.make_registry()

        registry["description"] = "Unauthorized description"

        self.assert_rejected(
            registry,
            "Invalid audit registry description",
        )

    def test_37_missing_and_unexpected_registry_fields(self):

        registry = self.make_registry()

        del registry["description"]

        self.assert_rejected(
            registry,
            "Missing audit registry field: description",
        )

        registry = self.make_registry()

        registry["unauthorized_field"] = True

        self.assert_rejected(
            registry,
            "Unexpected audit registry field",
        )

    def test_38_malformed_registry_and_records(self):

        self.assert_rejected(
            [],
            "Audit log must be a JSON object",
        )

        registry = self.make_registry()

        registry["records"] = {}

        self.assert_rejected(
            registry,
            "Audit records must be an array",
        )

        registry = self.make_registry(
            ["invalid record"]
        )

        self.assert_rejected(
            registry,
            "Must be an object",
        )

    def test_39_duplicate_json_keys_rejected(self):

        with tempfile.TemporaryDirectory() as directory:

            path = Path(directory) / "audit.json"

            path.write_text(
                '{"records": [], "records": []}',
                encoding="utf-8",
            )

            errors = validate_audit(path)

            self.assertTrue(
                any(
                    "Duplicate JSON key" in error
                    for error in errors
                ),
                errors,
            )

    def test_40_file_loading_validation(self):

        with tempfile.TemporaryDirectory() as directory:

            path = Path(directory) / "audit.json"

            registry = self.make_registry(
                [self.make_record()]
            )

            path.write_text(
                json.dumps(registry),
                encoding="utf-8",
            )

            self.assertEqual(
                validate_audit(path),
                [],
            )

            path.write_text(
                "{invalid JSON",
                encoding="utf-8",
            )

            self.assertTrue(
                validate_audit(path)
            )

            path.unlink()

            self.assertTrue(
                validate_audit(path)
            )


if __name__ == "__main__":

    unittest.main(verbosity=2)
