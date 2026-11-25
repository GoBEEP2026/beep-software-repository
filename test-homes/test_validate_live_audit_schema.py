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
    validate_live_audit_data,
)


class TestLiveAuditSchema(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(self.temp_dir.cleanup)

        self.audit_path = (
            Path(self.temp_dir.name) / "audit.json"
        )

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

    def make_legacy_record(self):

        record = self.make_record()

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            del record[field]

        return record

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

    def save_registry(self, registry):

        self.audit_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8",
        )

    def assert_live_accepted(self, registry):

        self.assertEqual(
            validate_live_audit_data(registry),
            [],
        )

    def assert_live_rejected(self, registry, expected):

        errors = validate_live_audit_data(registry)

        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected {expected!r}; got {errors}",
        )

    def assert_schema_rejected(self, registry):

        self.assertEqual(
            validate_live_audit_data(registry),
            [
                "Live audit registry must use "
                f"schema version {CURRENT_SCHEMA_VERSION}"
            ],
        )

    # CATEGORY 1
    # CURRENT SCHEMA ACCEPTANCE

    def test_01_current_empty_registry(self):

        self.assert_live_accepted(
            self.make_registry()
        )

    def test_02_current_approved_record(self):

        self.assert_live_accepted(
            self.make_registry(
                [self.make_record()]
            )
        )

    def test_03_current_rejected_record(self):

        self.assert_live_accepted(
            self.make_registry(
                [self.make_record("REJECTED")]
            )
        )

    def test_04_current_retired_record(self):

        self.assert_live_accepted(
            self.make_registry(
                [self.make_record("RETIRED")]
            )
        )

    def test_05_validation_does_not_modify_registry(self):

        registry = self.make_registry(
            [self.make_record()]
        )

        original = copy.deepcopy(registry)

        self.assert_live_accepted(registry)

        self.assertEqual(registry, original)

    # CATEGORY 2
    # LEGACY SCHEMA REJECTION

    def test_06_legacy_empty_registry_rejected(self):

        registry = self.make_registry(
            schema_version=LEGACY_SCHEMA_VERSION
        )

        self.assertEqual(
            validate_audit_data(registry),
            [],
        )

        self.assert_schema_rejected(registry)

    def test_07_legacy_approved_record_rejected(self):

        registry = self.make_registry(
            [self.make_legacy_record()],
            LEGACY_SCHEMA_VERSION,
        )

        self.assertEqual(
            validate_audit_data(registry),
            [],
        )

        self.assert_schema_rejected(registry)

    def test_08_legacy_rejected_record_rejected(self):

        record = self.make_legacy_record()

        record["decision"] = "REJECTED"

        registry = self.make_registry(
            [record],
            LEGACY_SCHEMA_VERSION,
        )

        self.assertEqual(
            validate_audit_data(registry),
            [],
        )

        self.assert_schema_rejected(registry)

    def test_09_legacy_retired_record_rejected(self):

        record = self.make_legacy_record()

        record["decision"] = "RETIRED"

        registry = self.make_registry(
            [record],
            LEGACY_SCHEMA_VERSION,
        )

        self.assertEqual(
            validate_audit_data(registry),
            [],
        )

        self.assert_schema_rejected(registry)

    def test_10_schema_relabeling_rejected(self):

        registry = self.make_registry(
            [self.make_record()]
        )

        self.assert_live_accepted(registry)

        registry["audit_schema_version"] = (
            LEGACY_SCHEMA_VERSION
        )

        self.assert_schema_rejected(registry)

    # CATEGORY 3
    # INVALID SCHEMA REJECTION

    def test_11_unsupported_future_schema(self):

        self.assert_schema_rejected(
            self.make_registry(
                schema_version="2.0.0"
            )
        )

    def test_12_missing_schema_version(self):

        registry = self.make_registry()

        del registry["audit_schema_version"]

        self.assert_schema_rejected(registry)

    def test_13_null_schema_version(self):

        self.assert_schema_rejected(
            self.make_registry(
                schema_version=None
            )
        )

    def test_14_invalid_schema_data_types(self):

        for value in (
            1,
            1.1,
            True,
            [],
            {},
        ):

            with self.subTest(value=value):

                self.assert_schema_rejected(
                    self.make_registry(
                        schema_version=value
                    )
                )

    def test_15_noncanonical_schema_strings(self):

        for value in (
            "",
            "1.1",
            "01.1.0",
            "1.1.0 ",
            " 1.1.0",
            "v1.1.0",
        ):

            with self.subTest(value=value):

                self.assert_schema_rejected(
                    self.make_registry(
                        schema_version=value
                    )
                )

    # CATEGORY 4
    # HISTORICAL COMPATIBILITY

    def test_16_historical_empty_legacy_registry(self):

        self.assertEqual(
            validate_audit_data(
                self.make_registry(
                    schema_version=LEGACY_SCHEMA_VERSION
                )
            ),
            [],
        )

    def test_17_historical_legacy_approved_record(self):

        self.assertEqual(
            validate_audit_data(
                self.make_registry(
                    [self.make_legacy_record()],
                    LEGACY_SCHEMA_VERSION,
                )
            ),
            [],
        )

    def test_18_historical_legacy_rejected_record(self):

        record = self.make_legacy_record()

        record["decision"] = "REJECTED"

        self.assertEqual(
            validate_audit_data(
                self.make_registry(
                    [record],
                    LEGACY_SCHEMA_VERSION,
                )
            ),
            [],
        )

    def test_19_historical_legacy_retired_record(self):

        record = self.make_legacy_record()

        record["decision"] = "RETIRED"

        self.assertEqual(
            validate_audit_data(
                self.make_registry(
                    [record],
                    LEGACY_SCHEMA_VERSION,
                )
            ),
            [],
        )

    def test_20_historical_current_registry(self):

        registry = self.make_registry(
            [self.make_record()]
        )

        self.assertEqual(
            validate_audit_data(registry),
            [],
        )

        self.assert_live_accepted(registry)

    # CATEGORY 5
    # FILE-BASED VALIDATION

    def test_21_current_registry_file_accepted(self):

        self.save_registry(
            self.make_registry(
                [self.make_record()]
            )
        )

        self.assertEqual(
            validate_audit(self.audit_path),
            [],
        )

    def test_22_legacy_registry_file_rejected(self):

        self.save_registry(
            self.make_registry(
                schema_version=LEGACY_SCHEMA_VERSION
            )
        )

        self.assertEqual(
            validate_audit(self.audit_path),
            [
                "Live audit registry must use "
                f"schema version {CURRENT_SCHEMA_VERSION}"
            ],
        )

    def test_23_missing_registry_file_rejected(self):

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any(
                "Unable to load audit log" in error
                for error in errors
            ),
            errors,
        )

    def test_24_malformed_json_file_rejected(self):

        self.audit_path.write_text(
            "{invalid JSON",
            encoding="utf-8",
        )

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any(
                "Unable to load audit log" in error
                for error in errors
            ),
            errors,
        )

    def test_25_duplicate_schema_key_rejected(self):

        self.audit_path.write_text(
            '{"audit_schema_version": "1.0.0",'
            '"audit_schema_version": "1.1.0"}',
            encoding="utf-8",
        )

        errors = validate_audit(self.audit_path)

        self.assertTrue(
            any(
                "Duplicate JSON key: audit_schema_version"
                in error
                for error in errors
            ),
            errors,
        )

    # CATEGORY 6
    # TECHNICAL REVIEW EVIDENCE ENFORCEMENT

    def test_26_approved_missing_review_evidence(self):

        record = self.make_record()

        registry = self.make_registry([record])

        self.assert_live_accepted(registry)

        del record["technical_review_record"]

        self.assert_live_rejected(
            registry,
            "Missing technical_review_record",
        )

    def test_27_retired_null_review_evidence(self):

        record = self.make_record("RETIRED")

        registry = self.make_registry([record])

        self.assert_live_accepted(registry)

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            record[field] = None

        self.assert_live_rejected(
            registry,
            "RETIRED audit decisions require "
            "complete technical review evidence",
        )

    def test_28_rejected_partial_review_evidence(self):

        record = self.make_record("REJECTED")

        registry = self.make_registry([record])

        self.assert_live_accepted(registry)

        record["technical_review_sha256"] = None

        self.assert_live_rejected(
            registry,
            "REJECTED audit decisions require "
            "either complete technical review "
            "evidence or all-null evidence",
        )

    def test_29_rejected_all_null_evidence_accepted(self):

        record = self.make_record("REJECTED")

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            record[field] = None

        self.assert_live_accepted(
            self.make_registry([record])
        )

    def test_30_legacy_record_in_current_schema_rejected(self):

        record = self.make_legacy_record()

        legacy_registry = self.make_registry(
            [record],
            LEGACY_SCHEMA_VERSION,
        )

        self.assertEqual(
            validate_audit_data(legacy_registry),
            [],
        )

        current_registry = self.make_registry(
            [record]
        )

        expected_errors = [
            f"Record 1: Missing {field}"
            for field in sorted(
                TECHNICAL_REVIEW_EVIDENCE_FIELDS
            )
        ]

        self.assertEqual(
            validate_live_audit_data(current_registry),
            expected_errors,
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
