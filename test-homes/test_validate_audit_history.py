import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_audit_append_only import (
    validate_append_only,
    validate_append_only_data,
)

from validate_reference_audit import (
    AUDIT_DESCRIPTION,
    AUDIT_STATUS,
    CURRENT_SCHEMA_VERSION,
    GOVERNANCE_AUTHORITY,
    LEGACY_SCHEMA_VERSION,
    REPOSITORY_NAME,
    TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    validate_audit_data,
)


class TestAuditHistory(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(self.temp_dir.cleanup)

        self.folder = Path(self.temp_dir.name)

        self.previous_path = (
            self.folder / "previous.json"
        )

        self.current_path = (
            self.folder / "current.json"
        )

    def make_record(
        self,
        record_id="BEEP-AUDIT-TEST-001",
        decision="APPROVED",
        schema_version=CURRENT_SCHEMA_VERSION,
    ):

        record = {
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
        }

        if schema_version == CURRENT_SCHEMA_VERSION:

            record.update({
                "technical_review_record": "BEEP-REV-TEST-001",
                "technical_review_date": "2026-01-20",
                "technical_review_sha256": "a" * 64,
                "reviewed_content_sha256": "b" * 64,
            })

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

    def assert_accepted(self, previous, current):

        self.assertEqual(
            validate_audit_data(previous),
            [],
        )

        self.assertEqual(
            validate_audit_data(current),
            [],
        )

        self.assertEqual(
            validate_append_only_data(
                previous,
                current,
            ),
            [],
        )

    def assert_rejected(
        self,
        previous,
        current,
        expected_message,
    ):

        errors = validate_append_only_data(
            previous,
            current,
        )

        self.assertTrue(
            errors,
            "Expected historical validation failure",
        )

        self.assertTrue(
            any(
                expected_message in error
                for error in errors
            ),
            f"Expected {expected_message!r}; got {errors}",
        )

    def write_histories(self, previous, current):

        self.previous_path.write_text(
            json.dumps(previous, indent=2),
            encoding="utf-8",
        )

        self.current_path.write_text(
            json.dumps(current, indent=2),
            encoding="utf-8",
        )

    def validate_files(self):

        return validate_append_only(
            self.previous_path,
            self.current_path,
        )

    def test_01_unchanged_empty_current_registry(self):

        registry = self.make_registry()

        self.assert_accepted(
            registry,
            copy.deepcopy(registry),
        )

    def test_02_unchanged_empty_legacy_registry(self):

        registry = self.make_registry(
            schema_version=LEGACY_SCHEMA_VERSION
        )

        self.assert_accepted(
            registry,
            copy.deepcopy(registry),
        )

    def test_03_unchanged_current_records(self):

        registry = self.make_registry(
            [self.make_record()]
        )

        self.assert_accepted(
            registry,
            copy.deepcopy(registry),
        )

    def test_04_append_first_current_record(self):

        self.assert_accepted(
            self.make_registry(),
            self.make_registry(
                [self.make_record()]
            ),
        )

    def test_05_append_multiple_current_records(self):

        first = self.make_record()

        second = self.make_record(
            "BEEP-AUDIT-TEST-002"
        )

        third = self.make_record(
            "BEEP-AUDIT-TEST-003",
            decision="REJECTED",
        )

        self.assert_accepted(
            self.make_registry([first]),
            self.make_registry(
                [first, second, third]
            ),
        )

    def test_06_append_rejected_null_evidence(self):

        first = self.make_record()

        rejected = self.make_record(
            "BEEP-AUDIT-TEST-002",
            decision="REJECTED",
        )

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            rejected[field] = None

        self.assert_accepted(
            self.make_registry([first]),
            self.make_registry(
                [first, rejected]
            ),
        )

    def test_07_append_retirement_record(self):

        approved = self.make_record()

        retired = self.make_record(
            "BEEP-AUDIT-TEST-002",
            decision="RETIRED",
        )

        retired["decision_date"] = "2026-02-01"

        self.assert_accepted(
            self.make_registry([approved]),
            self.make_registry(
                [approved, retired]
            ),
        )

    def test_08_authorized_empty_schema_migration(self):

        self.assert_accepted(
            self.make_registry(
                schema_version=LEGACY_SCHEMA_VERSION
            ),
            self.make_registry(
                schema_version=CURRENT_SCHEMA_VERSION
            ),
        )

    def test_09_validation_does_not_modify_inputs(self):

        previous = self.make_registry(
            [self.make_record()]
        )

        current = copy.deepcopy(previous)

        current["records"].append(
            self.make_record(
                "BEEP-AUDIT-TEST-002"
            )
        )

        previous_original = copy.deepcopy(previous)

        current_original = copy.deepcopy(current)

        self.assert_accepted(previous, current)

        self.assertEqual(
            previous,
            previous_original,
        )

        self.assertEqual(
            current,
            current_original,
        )

    def test_10_valid_legacy_record_append(self):

        first = self.make_record(
            schema_version=LEGACY_SCHEMA_VERSION
        )

        second = self.make_record(
            "BEEP-AUDIT-TEST-002",
            schema_version=LEGACY_SCHEMA_VERSION,
        )

        self.assert_accepted(
            self.make_registry(
                [first],
                LEGACY_SCHEMA_VERSION,
            ),
            self.make_registry(
                [first, second],
                LEGACY_SCHEMA_VERSION,
            ),
        )

    def test_11_historical_record_modification(self):

        original = self.make_record()

        modified = copy.deepcopy(original)

        modified["evidence"] = "Modified evidence"

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([modified]),
            "Audit record 1 was modified or reordered",
        )

    def test_12_historical_record_deletion(self):

        self.assert_rejected(
            self.make_registry(
                [self.make_record()]
            ),
            self.make_registry(),
            "Audit history cannot remove existing records",
        )

    def test_13_historical_record_reordering(self):

        first = self.make_record()

        second = self.make_record(
            "BEEP-AUDIT-TEST-002"
        )

        self.assert_rejected(
            self.make_registry([first, second]),
            self.make_registry([second, first]),
            "Audit record 1 was modified or reordered",
        )

    def test_14_historical_record_replacement(self):

        original = self.make_record()

        replacement = self.make_record(
            "BEEP-AUDIT-TEST-002"
        )

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([replacement]),
            "Audit record 1 was modified or reordered",
        )

    def test_15_historical_decision_modification(self):

        original = self.make_record()

        modified = copy.deepcopy(original)

        modified["decision"] = "REJECTED"

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([modified]),
            "Audit record 1 was modified or reordered",
        )

    def test_16_historical_reviewer_modification(self):

        original = self.make_record()

        modified = copy.deepcopy(original)

        modified["reviewer"] = "Different Test Reviewer"

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([modified]),
            "Audit record 1 was modified or reordered",
        )

    def test_17_historical_resolution_modification(self):

        original = self.make_record()

        modified = copy.deepcopy(original)

        modified["board_resolution_reference"] = (
            "BEEP-RES-TEST-002"
        )

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([modified]),
            "Audit record 1 was modified or reordered",
        )

    def test_18_historical_review_identifier_modification(self):

        original = self.make_record()

        modified = copy.deepcopy(original)

        modified["technical_review_record"] = (
            "BEEP-REV-TEST-002"
        )

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([modified]),
            "Audit record 1 was modified or reordered",
        )

    def test_19_historical_document_checksum_modification(self):

        original = self.make_record()

        modified = copy.deepcopy(original)

        modified["technical_review_sha256"] = "c" * 64

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([modified]),
            "Audit record 1 was modified or reordered",
        )

    def test_20_historical_content_fingerprint_modification(self):

        original = self.make_record()

        modified = copy.deepcopy(original)

        modified["reviewed_content_sha256"] = "d" * 64

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([modified]),
            "Audit record 1 was modified or reordered",
        )

    def test_21_historical_review_date_modification(self):

        original = self.make_record()

        modified = copy.deepcopy(original)

        modified["technical_review_date"] = "2026-01-21"

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([modified]),
            "Audit record 1 was modified or reordered",
        )

    def test_22_repository_name_modification(self):

        previous = self.make_registry()

        current = copy.deepcopy(previous)

        current["repository"] = "Unauthorized Repository"

        self.assert_rejected(
            previous,
            current,
            "Historical audit registry metadata cannot be modified",
        )

    def test_23_registry_description_modification(self):

        previous = self.make_registry()

        current = copy.deepcopy(previous)

        current["description"] = "Modified description"

        self.assert_rejected(
            previous,
            current,
            "Historical audit registry metadata cannot be modified",
        )

    def test_24_registry_status_modification(self):

        previous = self.make_registry()

        current = copy.deepcopy(previous)

        current["audit_status"] = "APPROVED"

        self.assert_rejected(
            previous,
            current,
            "Historical audit registry metadata cannot be modified",
        )

    def test_25_registry_metadata_removal(self):

        previous = self.make_registry()

        current = copy.deepcopy(previous)

        del current["description"]

        self.assert_rejected(
            previous,
            current,
            "Historical audit registry metadata cannot be modified",
        )

    def test_26_unauthorized_registry_metadata(self):

        previous = self.make_registry()

        current = copy.deepcopy(previous)

        current["unauthorized_field"] = True

        self.assert_rejected(
            previous,
            current,
            "Historical audit registry metadata cannot be modified",
        )

    def test_27_migration_with_historical_records(self):

        legacy_record = self.make_record(
            schema_version=LEGACY_SCHEMA_VERSION
        )

        previous = self.make_registry(
            [legacy_record],
            LEGACY_SCHEMA_VERSION,
        )

        current = self.make_registry()

        self.assert_rejected(
            previous,
            current,
            "Audit schema migration requires an empty historical audit registry",
        )

    def test_28_migration_with_new_records(self):

        previous = self.make_registry(
            schema_version=LEGACY_SCHEMA_VERSION
        )

        current = self.make_registry(
            [self.make_record()]
        )

        self.assert_rejected(
            previous,
            current,
            "Audit schema migration cannot introduce audit records",
        )

    def test_29_schema_downgrade(self):

        previous = self.make_registry()

        current = self.make_registry(
            schema_version=LEGACY_SCHEMA_VERSION
        )

        self.assert_rejected(
            previous,
            current,
            "Audit schema downgrade is prohibited",
        )

    def test_30_unauthorized_schema_transition(self):

        previous = self.make_registry()

        current = self.make_registry(
            schema_version="2.0.0"
        )

        self.assert_rejected(
            previous,
            current,
            "Unauthorized audit schema transition",
        )

    def test_31_migration_with_metadata_change(self):

        previous = self.make_registry(
            schema_version=LEGACY_SCHEMA_VERSION
        )

        current = self.make_registry()

        current["description"] = "Modified description"

        self.assert_rejected(
            previous,
            current,
            "Historical audit registry metadata cannot be modified",
        )

    def test_32_invalid_appended_record(self):

        previous = self.make_registry()

        record = self.make_record()

        record["technical_review_sha256"] = "invalid"

        current = self.make_registry([record])

        self.assert_rejected(
            previous,
            current,
            "Current audit: Record 1: Invalid technical review document",
        )

    def test_33_invalid_historical_record(self):

        record = self.make_record()

        record["approval_authority"] = "Unauthorized Authority"

        previous = self.make_registry([record])

        current = copy.deepcopy(previous)

        self.assert_rejected(
            previous,
            current,
            "Historical audit: Record 1: Invalid approval authority",
        )

    def test_34_duplicate_appended_record_identifier(self):

        original = self.make_record()

        duplicate = copy.deepcopy(original)

        duplicate["record_id"] = (
            original["record_id"].lower()
        )

        self.assert_rejected(
            self.make_registry([original]),
            self.make_registry([original, duplicate]),
            "Duplicate record ID",
        )

    def test_35_malformed_registry_roots(self):

        for malformed in (
            [],
            None,
            "invalid",
        ):

            with self.subTest(malformed=malformed):

                self.assert_rejected(
                    malformed,
                    self.make_registry(),
                    "Audit histories must be JSON objects",
                )

                self.assert_rejected(
                    self.make_registry(),
                    malformed,
                    "Audit histories must be JSON objects",
                )

    def test_36_malformed_record_arrays(self):

        previous = self.make_registry()

        current = self.make_registry()

        previous["records"] = {}

        self.assert_rejected(
            previous,
            current,
            "Previous audit records must be an array",
        )

        previous = self.make_registry()

        current["records"] = None

        self.assert_rejected(
            previous,
            current,
            "Current audit records must be an array",
        )

    def test_37_valid_file_based_migration(self):

        self.write_histories(
            self.make_registry(
                schema_version=LEGACY_SCHEMA_VERSION
            ),
            self.make_registry(),
        )

        self.assertEqual(
            self.validate_files(),
            [],
        )

    def test_38_duplicate_json_keys_rejected(self):

        registry = self.make_registry()

        for path in (
            self.previous_path,
            self.current_path,
        ):

            with self.subTest(path=path.name):

                self.write_histories(
                    registry,
                    registry,
                )

                path.write_text(
                    '{"records": [], "records": []}',
                    encoding="utf-8",
                )

                errors = self.validate_files()

                self.assertTrue(
                    any(
                        "Duplicate JSON key" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_39_missing_and_invalid_audit_files(self):

        registry = self.make_registry()

        self.write_histories(
            registry,
            registry,
        )

        self.previous_path.unlink()

        errors = self.validate_files()

        self.assertTrue(
            any(
                "Unable to load audit history" in error
                for error in errors
            ),
            errors,
        )

        self.write_histories(
            registry,
            registry,
        )

        self.current_path.write_text(
            "{invalid JSON",
            encoding="utf-8",
        )

        errors = self.validate_files()

        self.assertTrue(
            any(
                "Unable to load audit history" in error
                for error in errors
            ),
            errors,
        )

    def test_40_symbolic_link_audit_files_rejected(self):

        registry = self.make_registry()

        for path, expected in (
            (
                self.previous_path,
                "Historical audit file cannot be a symbolic link",
            ),
            (
                self.current_path,
                "Current audit file cannot be a symbolic link",
            ),
        ):

            with self.subTest(path=path.name):

                for audit_path in (
                    self.previous_path,
                    self.current_path,
                ):

                    if audit_path.is_symlink():

                        audit_path.unlink()

                self.write_histories(
                    registry,
                    registry,
                )

                target = self.folder / "target.json"

                target.write_text(
                    json.dumps(registry),
                    encoding="utf-8",
                )

                path.unlink()

                path.symlink_to(target)

                errors = self.validate_files()

                self.assertIn(
                    expected,
                    errors,
                )


if __name__ == "__main__":

    unittest.main(verbosity=2)
