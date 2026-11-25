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

from validate_technical_review import (
    calculate_technical_fingerprint,
    validate_review_fingerprint,
)

from validate_approval_audit_consistency import (
    validate_approval_audit_consistency,
    validate_approval_audit_consistency_data,
)


class TestApprovalAuditConsistency(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)

        self.registry_path = (
            self.root
            / "reference-home-registry.json"
        )

        self.audit_path = (
            self.root
            / "reference-approval-audit.json"
        )

    def make_home(
        self,
        status="APPROVED",
        version="1.0.0",
        suffix="001",
    ):

        home = {
            "test_home_id": "BEEP-HOME-TEST",
            "test_home_version": version,
            "status": status,
            "review": {
                "reviewer": "Fictional Test Reviewer",
                "review_record": (
                    f"BEEP-REV-TEST-{suffix}"
                ),
                "review_status": "COMPLETED",
                "review_date": "2026-01-20",
                "review_findings": (
                    "Fictional technical review findings"
                ),
                "review_recommendation": (
                    "RECOMMEND_APPROVAL"
                ),
                "conflict_of_interest_disclosure": (
                    "No conflicts disclosed"
                ),
                "reviewed_content_sha256": None,
            },
            "approval": {
                "approved_by": GOVERNANCE_AUTHORITY,
                "approval_date": "2026-01-25",
                "approval_record": (
                    f"BEEP-AUDIT-TEST-{suffix}"
                ),
                "board_resolution_reference": (
                    f"BEEP-RES-TEST-{suffix}"
                ),
            },
            "reference_files": [
                {
                    "filename": "fictional-home.xml",
                    "sha256": "a" * 64,
                }
            ],
            "test_cycles": [
                "BEEP-CYCLE-TEST-001"
            ],
        }

        if status == "DEVELOPMENT":

            for field in home["review"]:

                home["review"][field] = None

            home["review"]["review_status"] = (
                "NOT_STARTED"
            )

            for field in home["approval"]:

                home["approval"][field] = None

        elif status == "UNDER_REVIEW":

            home["review"]["review_status"] = (
                "IN_PROGRESS"
            )

            for field in (
                "review_date",
                "review_findings",
                "review_recommendation",
                "reviewed_content_sha256",
            ):

                home["review"][field] = None

            for field in home["approval"]:

                home["approval"][field] = None

        else:

            home["review"][
                "reviewed_content_sha256"
            ] = calculate_technical_fingerprint(
                home
            )

        return home

    def make_record(self, home):

        approval = home["approval"]

        review = home["review"]

        return {
            "record_id": approval["approval_record"],
            "reference_home_id": home["test_home_id"],
            "reference_home_version": (
                home["test_home_version"]
            ),
            "decision": "APPROVED",
            "reviewer": review["reviewer"],
            "approval_authority": (
                approval["approved_by"]
            ),
            "evidence": "Fictional supporting evidence",
            "pull_request": "TEST-PR-001",
            "board_resolution_reference": (
                approval["board_resolution_reference"]
            ),
            "decision_date": approval["approval_date"],
            "technical_review_record": (
                review["review_record"]
            ),
            "technical_review_date": (
                review["review_date"]
            ),
            "technical_review_sha256": "b" * 64,
            "reviewed_content_sha256": (
                review["reviewed_content_sha256"]
            ),
        }

    def make_registry(self, homes=None):

        return {
            "reference_homes": (
                [self.make_home("DEVELOPMENT")]
                if homes is None
                else homes
            ),
        }

    def make_audit(self, records=None):

        return {
            "audit_schema_version": (
                CURRENT_SCHEMA_VERSION
            ),
            "repository": REPOSITORY_NAME,
            "audit_status": AUDIT_STATUS,
            "description": AUDIT_DESCRIPTION,
            "records": (
                [] if records is None else records
            ),
        }

    def validate(self, registry, audit):

        return validate_approval_audit_consistency_data(
            registry,
            audit,
        )

    def assert_accepted(self, registry, audit):

        self.assertEqual(
            validate_live_audit_data(audit),
            [],
        )

        self.assertEqual(
            self.validate(registry, audit),
            [],
        )

    def assert_rejected(
        self,
        registry,
        audit,
        expected,
    ):

        errors = self.validate(
            registry,
            audit,
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
        registry,
        audit,
        expected,
    ):

        self.assertEqual(
            validate_live_audit_data(audit),
            [],
            "Audit schema must remain valid",
        )

        self.assert_rejected(
            registry,
            audit,
            expected,
        )

    def make_valid_fixture(
        self,
        status="APPROVED",
    ):

        home = self.make_home(status)

        record = self.make_record(home)

        registry = self.make_registry([home])

        audit = self.make_audit([record])

        self.assertEqual(
            validate_review_fingerprint(home),
            [],
        )

        self.assert_accepted(
            registry,
            audit,
        )

        return registry, audit, home, record

    def save_registries(self, registry, audit):

        self.registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8",
        )

        self.audit_path.write_text(
            json.dumps(audit, indent=2),
            encoding="utf-8",
        )

    def validate_files(self):

        return validate_approval_audit_consistency(
            self.registry_path,
            self.audit_path,
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
    # VALID APPROVAL RELATIONSHIPS

    def test_01_development_without_approval(self):

        self.assert_accepted(
            self.make_registry(),
            self.make_audit(),
        )

    def test_02_under_review_without_approval(self):

        self.assert_accepted(
            self.make_registry(
                [self.make_home("UNDER_REVIEW")]
            ),
            self.make_audit(),
        )

    def test_03_approved_matching_original_decision(self):

        self.make_valid_fixture("APPROVED")

    def test_04_retired_preserves_original_approval(self):

        self.make_valid_fixture("RETIRED")

    def test_05_independent_version_approvals(self):

        first = self.make_home(
            "RETIRED",
            "1.0.0",
            "001",
        )

        second = self.make_home(
            "APPROVED",
            "1.1.0",
            "002",
        )

        third = self.make_home(
            "UNDER_REVIEW",
            "1.2.0",
            "003",
        )

        self.assert_accepted(
            self.make_registry(
                [first, second, third]
            ),
            self.make_audit(
                [
                    self.make_record(first),
                    self.make_record(second),
                ]
            ),
        )

    # CATEGORY 2
    # FORWARD HOME-TO-AUDIT VALIDATION

    def test_06_approved_missing_original_approval(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        audit["records"] = []

        self.assert_matching_rejected(
            registry,
            audit,
            "Missing original APPROVED audit decision",
        )

    def test_07_retired_missing_original_approval(self):

        registry, audit, home, record = (
            self.make_valid_fixture("RETIRED")
        )

        audit["records"] = []

        self.assert_matching_rejected(
            registry,
            audit,
            "Missing original APPROVED audit decision",
        )

    def test_08_multiple_approved_decisions(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        duplicate = copy.deepcopy(record)

        duplicate["record_id"] = (
            "BEEP-AUDIT-TEST-002"
        )

        audit["records"].append(duplicate)

        self.assert_matching_rejected(
            registry,
            audit,
            "Multiple APPROVED audit decisions",
        )

    def test_09_retired_multiple_original_approvals(self):

        registry, audit, home, record = (
            self.make_valid_fixture("RETIRED")
        )

        duplicate = copy.deepcopy(record)

        duplicate["record_id"] = (
            "BEEP-AUDIT-TEST-002"
        )

        audit["records"].append(duplicate)

        self.assert_matching_rejected(
            registry,
            audit,
            "Multiple APPROVED audit decisions",
        )

    def test_10_rejected_decision_is_not_approval(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["decision"] = "REJECTED"

        self.assert_matching_rejected(
            registry,
            audit,
            "Missing original APPROVED audit decision",
        )

    # CATEGORY 3
    # REVERSE AUDIT-TO-HOME VALIDATION

    def test_11_unregistered_reference_home(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["reference_home_id"] = (
            "BEEP-HOME-UNKNOWN"
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "references an unregistered "
            "reference home version",
        )

    def test_12_unregistered_reference_version(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["reference_home_version"] = (
            "2.0.0"
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "references an unregistered "
            "reference home version",
        )

    def test_13_approval_for_development_home(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        registry["reference_homes"] = [
            self.make_home("DEVELOPMENT")
        ]

        self.assert_matching_rejected(
            registry,
            audit,
            "ineligible reference home status: "
            "DEVELOPMENT",
        )

    def test_14_approval_for_under_review_home(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        registry["reference_homes"] = [
            self.make_home("UNDER_REVIEW")
        ]

        self.assert_matching_rejected(
            registry,
            audit,
            "ineligible reference home status: "
            "UNDER_REVIEW",
        )

    def test_15_home_identifier_case_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["reference_home_id"] = (
            record["reference_home_id"].lower()
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "references an unregistered "
            "reference home version",
        )

    # CATEGORY 4
    # APPROVAL METADATA CONSISTENCY

    def test_16_approval_record_identifier_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["record_id"] = (
            "BEEP-AUDIT-TEST-OTHER"
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "Approval audit metadata mismatch: "
            "approval_record",
        )

    def test_17_approval_authority_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        home["approval"]["approved_by"] = (
            "Unauthorized Organization"
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "Invalid reference home approval authority",
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "Approval audit metadata mismatch: "
            "approved_by",
        )

    def test_18_approval_date_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["decision_date"] = "2026-01-26"

        self.assert_matching_rejected(
            registry,
            audit,
            "Approval audit metadata mismatch: "
            "approval_date",
        )

    def test_19_board_resolution_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["board_resolution_reference"] = (
            "BEEP-RES-TEST-OTHER"
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "Approval audit metadata mismatch: "
            "board_resolution_reference",
        )

    def test_20_missing_approval_metadata(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        home["approval"] = None

        self.assert_matching_rejected(
            registry,
            audit,
            "Missing approval metadata",
        )

    # CATEGORY 5
    # TECHNICAL REVIEW EVIDENCE CONSISTENCY

    def test_21_technical_reviewer_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["reviewer"] = (
            "Different Fictional Reviewer"
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "Approval audit technical review "
            "mismatch: reviewer",
        )

    def test_22_technical_review_identifier_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["technical_review_record"] = (
            "BEEP-REV-TEST-OTHER"
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "Approval audit technical review "
            "mismatch: review_record",
        )

    def test_23_technical_review_date_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        record["technical_review_date"] = (
            "2026-01-21"
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "Approval audit technical review "
            "mismatch: review_date",
        )

    def test_24_reviewed_content_fingerprint_mismatch(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        original = record[
            "reviewed_content_sha256"
        ]

        record["reviewed_content_sha256"] = (
            "0" * 64
            if original != "0" * 64
            else "1" * 64
        )

        self.assert_matching_rejected(
            registry,
            audit,
            "Approval audit technical review "
            "mismatch: reviewed_content_sha256",
        )

    def test_25_invalid_retained_review_evidence(self):

        cases = (
            (
                "review_status",
                "IN_PROGRESS",
                "requires COMPLETED technical review",
            ),
            (
                "review_recommendation",
                "REVISIONS_REQUIRED",
                "requires RECOMMEND_APPROVAL",
            ),
        )

        for field, value, expected in cases:

            with self.subTest(field=field):

                registry, audit, home, record = (
                    self.make_valid_fixture()
                )

                home["review"][field] = value

                self.assert_matching_rejected(
                    registry,
                    audit,
                    expected,
                )

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        home["review"] = None

        self.assert_matching_rejected(
            registry,
            audit,
            "Missing technical review metadata",
        )

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        home["reference_files"][0]["sha256"] = (
            "c" * 64
        )

        fingerprint_errors = (
            validate_review_fingerprint(home)
        )

        self.assertTrue(fingerprint_errors)

        errors = self.validate(registry, audit)

        for expected in fingerprint_errors:

            self.assertTrue(
                any(
                    expected in error
                    for error in errors
                ),
                errors,
            )

    # CATEGORY 6
    # REFERENCE REGISTRY INTEGRITY

    def test_26_invalid_reference_registry_root(self):

        for invalid in (
            None,
            [],
            "invalid",
        ):

            with self.subTest(registry=invalid):

                self.assert_rejected(
                    invalid,
                    self.make_audit(),
                    "Reference registry must be an object",
                )

    def test_27_invalid_reference_home_array(self):

        for invalid in (
            None,
            [],
            {},
            "invalid",
        ):

            with self.subTest(homes=invalid):

                self.assert_rejected(
                    {"reference_homes": invalid},
                    self.make_audit(),
                    "Reference registry has no valid "
                    "home entries",
                )

    def test_28_invalid_reference_home_entry(self):

        self.assert_rejected(
            self.make_registry([None]),
            self.make_audit(),
            "Invalid reference home entry",
        )

    def test_29_duplicate_reference_home_version(self):

        home = self.make_home("DEVELOPMENT")

        self.assert_rejected(
            self.make_registry(
                [home, copy.deepcopy(home)]
            ),
            self.make_audit(),
            "Duplicate reference home version",
        )

    def test_30_invalid_home_identity_or_status(self):

        cases = (
            (
                "test_home_id",
                "../invalid",
                "Invalid reference home identifier",
            ),
            (
                "test_home_version",
                "01.0.0",
                "Invalid reference home version",
            ),
            (
                "status",
                "UNAUTHORIZED",
                "Invalid reference home lifecycle status",
            ),
            (
                "status",
                [],
                "Invalid reference home lifecycle status",
            ),
        )

        for field, value, expected in cases:

            with self.subTest(field=field, value=value):

                home = self.make_home("DEVELOPMENT")

                home[field] = value

                self.assert_rejected(
                    self.make_registry([home]),
                    self.make_audit(),
                    expected,
                )

    # CATEGORY 7
    # AUDIT SCHEMA AND HISTORICAL CONSISTENCY

    def test_31_legacy_live_audit_schema(self):

        audit = self.make_audit()

        audit["audit_schema_version"] = (
            LEGACY_SCHEMA_VERSION
        )

        self.assert_rejected(
            self.make_registry(),
            audit,
            "Live audit registry must use schema version",
        )

    def test_32_invalid_audit_without_approved_homes(self):

        audit = self.make_audit()

        audit["records"] = {}

        self.assert_rejected(
            self.make_registry(),
            audit,
            "Audit records must be an array",
        )

    def test_33_duplicate_audit_record_identifier(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        audit["records"].append(
            copy.deepcopy(record)
        )

        self.assert_rejected(
            registry,
            audit,
            "Duplicate record ID",
        )

    def test_34_preserve_historical_rejected_decisions(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        rejected = copy.deepcopy(record)

        rejected["record_id"] = (
            "BEEP-AUDIT-TEST-REJECTED"
        )

        rejected["decision"] = "REJECTED"

        rejected["decision_date"] = "2026-01-05"

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            rejected[field] = None

        audit["records"].insert(0, rejected)

        self.assert_accepted(
            registry,
            audit,
        )

    def test_35_validation_does_not_modify_registries(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        original_registry = copy.deepcopy(registry)

        original_audit = copy.deepcopy(audit)

        self.assert_accepted(
            registry,
            audit,
        )

        self.assertEqual(
            registry,
            original_registry,
        )

        self.assertEqual(
            audit,
            original_audit,
        )

    # CATEGORY 8
    # FILE VALIDATION AND SECURITY

    def test_36_valid_registry_files(self):

        registry, audit, home, record = (
            self.make_valid_fixture()
        )

        self.save_registries(
            registry,
            audit,
        )

        self.assertEqual(
            self.validate_files(),
            [],
        )

    def test_37_missing_registry_files(self):

        for missing_file in (
            self.registry_path,
            self.audit_path,
        ):

            with self.subTest(file=missing_file):

                self.save_registries(
                    self.make_registry(),
                    self.make_audit(),
                )

                missing_file.unlink()

                self.assert_file_rejected(
                    "Unable to validate approval "
                    "audit consistency",
                )

    def test_38_malformed_or_duplicate_json_keys(self):

        for target in (
            self.registry_path,
            self.audit_path,
        ):

            for content, expected in (
                (
                    "{invalid JSON",
                    "Unable to validate approval "
                    "audit consistency",
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
                        self.make_registry(),
                        self.make_audit(),
                    )

                    target.write_text(
                        content,
                        encoding="utf-8",
                    )

                    self.assert_file_rejected(
                        expected
                    )

    def test_39_reference_registry_symbolic_link(self):

        self.save_registries(
            self.make_registry(),
            self.make_audit(),
        )

        target = self.root / "external-registry.json"

        self.registry_path.rename(target)

        self.registry_path.symlink_to(target)

        self.assertEqual(
            self.validate_files(),
            [
                "Reference home registry "
                "cannot be a symbolic link"
            ],
        )

    def test_40_audit_registry_symbolic_link(self):

        self.save_registries(
            self.make_registry(),
            self.make_audit(),
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


if __name__ == "__main__":

    unittest.main(verbosity=2)
