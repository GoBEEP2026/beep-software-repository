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
)

from validate_approval_audit_consistency import (
    validate_approval_audit_consistency_data,
)

from validate_retirement_audit_consistency import (
    validate_retirement_audit_consistency,
    validate_retirement_audit_consistency_data,
)


class TestRetirementAuditConsistency(unittest.TestCase):

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
        status="RETIRED",
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
                    f"BEEP-AUDIT-APPROVAL-{suffix}"
                ),
                "board_resolution_reference": (
                    f"BEEP-RES-APPROVAL-{suffix}"
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

    def make_approval(self, home):

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
            "evidence": (
                "Fictional original approval evidence"
            ),
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

    def make_retirement(
        self,
        approval,
        suffix="001",
    ):

        retirement = copy.deepcopy(approval)

        retirement.update({
            "record_id": (
                f"BEEP-AUDIT-RETIREMENT-{suffix}"
            ),
            "decision": "RETIRED",
            "evidence": (
                "Fictional retirement decision evidence"
            ),
            "pull_request": "TEST-PR-002",
            "board_resolution_reference": (
                f"BEEP-RES-RETIREMENT-{suffix}"
            ),
            "decision_date": "2026-07-15",
        })

        return retirement

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

        return validate_retirement_audit_consistency_data(
            registry,
            audit,
        )

    def assert_accepted(self, registry, audit):

        self.assertEqual(
            validate_live_audit_data(audit),
            [],
        )

        self.assertEqual(
            validate_approval_audit_consistency_data(
                registry,
                audit,
            ),
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

    def assert_retirement_rejected(
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

        self.assertEqual(
            validate_approval_audit_consistency_data(
                registry,
                audit,
            ),
            [],
            "Original approval must remain valid",
        )

        self.assert_rejected(
            registry,
            audit,
            expected,
        )

    def make_valid_fixture(self):

        home = self.make_home()

        approval = self.make_approval(home)

        retirement = self.make_retirement(
            approval
        )

        registry = self.make_registry([home])

        audit = self.make_audit(
            [approval, retirement]
        )

        self.assert_accepted(
            registry,
            audit,
        )

        return (
            registry,
            audit,
            home,
            approval,
            retirement,
        )

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

        return validate_retirement_audit_consistency(
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
    # VALID LIFECYCLE RELATIONSHIPS

    def test_01_development_without_retirement(self):

        self.assert_accepted(
            self.make_registry(),
            self.make_audit(),
        )

    def test_02_under_review_without_retirement(self):

        self.assert_accepted(
            self.make_registry([
                self.make_home("UNDER_REVIEW")
            ]),
            self.make_audit(),
        )

    def test_03_approved_without_retirement(self):

        home = self.make_home("APPROVED")

        self.assert_accepted(
            self.make_registry([home]),
            self.make_audit([
                self.make_approval(home)
            ]),
        )

    def test_04_valid_retirement(self):

        self.make_valid_fixture()

    def test_05_independent_version_retirements(self):

        first = self.make_home(
            "RETIRED",
            "1.0.0",
            "001",
        )

        second = self.make_home(
            "RETIRED",
            "1.1.0",
            "002",
        )

        third = self.make_home(
            "APPROVED",
            "1.2.0",
            "003",
        )

        first_approval = self.make_approval(first)

        second_approval = self.make_approval(second)

        third_approval = self.make_approval(third)

        self.assert_accepted(
            self.make_registry([
                first,
                second,
                third,
            ]),
            self.make_audit([
                first_approval,
                second_approval,
                third_approval,
                self.make_retirement(
                    first_approval,
                    "001",
                ),
                self.make_retirement(
                    second_approval,
                    "002",
                ),
            ]),
        )

    # CATEGORY 2
    # FORWARD RETIREMENT VALIDATION

    def test_06_retired_missing_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        audit["records"] = [approval]

        self.assert_retirement_rejected(
            registry,
            audit,
            "Missing RETIRED audit decision",
        )

    def test_07_retired_missing_original_approval(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        audit["records"] = [retirement]

        self.assert_rejected(
            registry,
            audit,
            "Missing original APPROVED audit decision",
        )

    def test_08_multiple_retirement_decisions(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        duplicate = self.make_retirement(
            approval,
            "002",
        )

        audit["records"].append(duplicate)

        self.assert_retirement_rejected(
            registry,
            audit,
            "Multiple RETIRED audit decisions",
        )

    def test_09_multiple_original_approvals(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        duplicate = copy.deepcopy(approval)

        duplicate["record_id"] = (
            "BEEP-AUDIT-APPROVAL-OTHER"
        )

        audit["records"].append(duplicate)

        self.assert_rejected(
            registry,
            audit,
            "Multiple APPROVED audit decisions",
        )

    def test_10_rejection_is_not_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["decision"] = "REJECTED"

        self.assert_retirement_rejected(
            registry,
            audit,
            "Missing RETIRED audit decision",
        )

    # CATEGORY 3
    # REVERSE RETIREMENT VALIDATION

    def test_11_unregistered_home_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["reference_home_id"] = (
            "BEEP-HOME-UNKNOWN"
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "references an unregistered "
            "reference home version",
        )

    def test_12_unregistered_version_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["reference_home_version"] = (
            "2.0.0"
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "references an unregistered "
            "reference home version",
        )

    def test_13_development_home_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        registry["reference_homes"] = [
            self.make_home("DEVELOPMENT")
        ]

        audit["records"] = [retirement]

        self.assert_retirement_rejected(
            registry,
            audit,
            "ineligible reference home status: "
            "DEVELOPMENT",
        )

    def test_14_under_review_home_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        registry["reference_homes"] = [
            self.make_home("UNDER_REVIEW")
        ]

        audit["records"] = [retirement]

        self.assert_retirement_rejected(
            registry,
            audit,
            "ineligible reference home status: "
            "UNDER_REVIEW",
        )

    def test_15_approved_home_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        home["status"] = "APPROVED"

        self.assert_retirement_rejected(
            registry,
            audit,
            "ineligible reference home status: "
            "APPROVED",
        )

    # CATEGORY 4
    # CHRONOLOGY AND INDEPENDENT DECISIONS

    def test_16_retirement_date_before_approval(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["decision_date"] = (
            "2026-01-24"
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "Retirement decision date cannot "
            "precede original approval date",
        )

    def test_17_retirement_before_approval_in_audit(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        audit["records"] = [
            retirement,
            approval,
        ]

        self.assert_retirement_rejected(
            registry,
            audit,
            "Retirement audit decision must "
            "appear after the original "
            "APPROVED audit decision",
        )

    def test_18_same_day_ordered_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["decision_date"] = (
            approval["decision_date"]
        )

        self.assert_accepted(
            registry,
            audit,
        )

    def test_19_same_day_reversed_retirement(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["decision_date"] = (
            approval["decision_date"]
        )

        audit["records"] = [
            retirement,
            approval,
        ]

        self.assert_retirement_rejected(
            registry,
            audit,
            "Retirement audit decision must "
            "appear after the original",
        )

    def test_20_independent_board_resolution_required(self):

        for transform in (
            lambda value: value,
            lambda value: value.lower(),
            lambda value: value.upper(),
        ):

            with self.subTest(transform=transform):

                (
                    registry,
                    audit,
                    home,
                    approval,
                    retirement,
                ) = self.make_valid_fixture()

                retirement[
                    "board_resolution_reference"
                ] = transform(
                    approval[
                        "board_resolution_reference"
                    ]
                )

                self.assert_retirement_rejected(
                    registry,
                    audit,
                    "Retirement requires an independent "
                    "Board resolution reference",
                )

    # CATEGORY 5
    # ORIGINAL TECHNICAL EVIDENCE PRESERVATION

    def test_21_technical_reviewer_mismatch(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["reviewer"] = (
            "Different Fictional Reviewer"
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "Retirement technical review "
            "evidence mismatch: reviewer",
        )

    def test_22_technical_review_identifier_mismatch(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["technical_review_record"] = (
            "BEEP-REV-TEST-OTHER"
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "Retirement technical review evidence "
            "mismatch: technical_review_record",
        )

    def test_23_technical_review_date_mismatch(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["technical_review_date"] = (
            "2026-01-21"
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "Retirement technical review evidence "
            "mismatch: technical_review_date",
        )

    def test_24_technical_document_checksum_mismatch(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["technical_review_sha256"] = (
            "c" * 64
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "Retirement technical review evidence "
            "mismatch: technical_review_sha256",
        )

    def test_25_reviewed_content_fingerprint_mismatch(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        original = approval[
            "reviewed_content_sha256"
        ]

        retirement["reviewed_content_sha256"] = (
            "0" * 64
            if original != "0" * 64
            else "1" * 64
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "Retirement technical review evidence "
            "mismatch: reviewed_content_sha256",
        )

    # CATEGORY 6
    # ORIGINAL APPROVAL AND SCHEMA ENFORCEMENT

    def test_26_invalid_retirement_authority(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["approval_authority"] = (
            "Unauthorized Organization"
        )

        self.assert_rejected(
            registry,
            audit,
            "Invalid approval authority",
        )

    def test_27_duplicate_audit_identifier(self):

        for transform in (
            lambda value: value,
            lambda value: value.lower(),
        ):

            with self.subTest(transform=transform):

                (
                    registry,
                    audit,
                    home,
                    approval,
                    retirement,
                ) = self.make_valid_fixture()

                retirement["record_id"] = transform(
                    approval["record_id"]
                )

                self.assert_rejected(
                    registry,
                    audit,
                    "Duplicate record ID",
                )

    def test_28_missing_retirement_review_evidence(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            retirement[field] = None

        self.assert_rejected(
            registry,
            audit,
            "RETIRED audit decisions require "
            "complete technical review evidence",
        )

    def test_29_original_approval_metadata_changed(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        home["approval"][
            "board_resolution_reference"
        ] = "BEEP-RES-CHANGED"

        self.assert_rejected(
            registry,
            audit,
            "Approval audit metadata mismatch: "
            "board_resolution_reference",
        )

    def test_30_original_technical_content_changed(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        home["reference_files"][0]["sha256"] = (
            "d" * 64
        )

        original_errors = (
            validate_approval_audit_consistency_data(
                registry,
                audit,
            )
        )

        self.assertTrue(original_errors)

        self.assertEqual(
            self.validate(registry, audit),
            [
                f"Original approval consistency: {error}"
                for error in original_errors
            ],
        )

    # CATEGORY 7
    # HISTORICAL CONSISTENCY AND DATA INTEGRITY

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

    def test_32_invalid_reference_registry(self):

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

    def test_33_preserve_historical_rejected_decisions(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        rejected = copy.deepcopy(approval)

        rejected["record_id"] = (
            "BEEP-AUDIT-REJECTED-001"
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

    def test_34_retirement_home_identifier_case_mismatch(self):

        registry, audit, home, approval, retirement = (
            self.make_valid_fixture()
        )

        retirement["reference_home_id"] = (
            retirement["reference_home_id"].lower()
        )

        self.assert_retirement_rejected(
            registry,
            audit,
            "references an unregistered "
            "reference home version",
        )

    def test_35_validation_does_not_modify_registries(self):

        registry, audit, home, approval, retirement = (
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

        registry, audit, home, approval, retirement = (
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
                    "Unable to validate retirement "
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
                    "Unable to validate retirement "
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

        target = (
            self.root
            / "external-registry.json"
        )

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

        target = (
            self.root
            / "external-audit.json"
        )

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
