import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_reference_audit import (
    LEGACY_SCHEMA_VERSION,
    TECHNICAL_REVIEW_EVIDENCE_FIELDS,
)

from validate_technical_review import (
    calculate_technical_fingerprint,
)

from validate_audit_decision_history import (
    validate_audit_decision_history,
    validate_audit_decision_history_data,
)

from test_validate_retirement_audit_consistency import (
    TestRetirementAuditConsistency as RetirementFixtures,
)


class TestAuditDecisionHistory(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)

        self.paths = [
            self.root / "previous-reference.json",
            self.root / "current-reference.json",
            self.root / "previous-audit.json",
            self.root / "current-audit.json",
        ]

        self.fixtures = RetirementFixtures()

    def make_home(self, *args, **kwargs):

        return self.fixtures.make_home(
            *args,
            **kwargs,
        )

    def make_registry(self, homes):

        return self.fixtures.make_registry(homes)

    def make_audit(self, records=None):

        return self.fixtures.make_audit(records)

    def make_approval(self, home):

        return self.fixtures.make_approval(home)

    def make_retirement(self, approval, suffix="001"):

        return self.fixtures.make_retirement(
            approval,
            suffix,
        )

    def make_completed_review(
        self,
        recommendation="RECOMMEND_APPROVAL",
        version="1.0.0",
        suffix="001",
    ):

        home = self.make_home(
            "APPROVED",
            version,
            suffix,
        )

        home["status"] = "UNDER_REVIEW"

        home["review"][
            "review_recommendation"
        ] = recommendation

        for field in home["approval"]:

            home["approval"][field] = None

        return home

    def make_rejection(
        self,
        home,
        complete=True,
        suffix="001",
    ):

        record = {
            "record_id": (
                f"BEEP-AUDIT-REJECTED-{suffix}"
            ),
            "reference_home_id": home["test_home_id"],
            "reference_home_version": (
                home["test_home_version"]
            ),
            "decision": "REJECTED",
            "reviewer": home["review"]["reviewer"],
            "approval_authority": (
                "B.E.E.P. Board of Directors"
            ),
            "evidence": (
                "Fictional rejection decision evidence"
            ),
            "pull_request": "TEST-PR-003",
            "board_resolution_reference": (
                f"BEEP-RES-REJECTED-{suffix}"
            ),
            "decision_date": "2026-02-01",
            "technical_review_record": (
                home["review"]["review_record"]
            ),
            "technical_review_date": (
                home["review"]["review_date"]
            ),
            "technical_review_sha256": "b" * 64,
            "reviewed_content_sha256": (
                home["review"][
                    "reviewed_content_sha256"
                ]
            ),
        }

        if not complete:

            for field in (
                TECHNICAL_REVIEW_EVIDENCE_FIELDS
            ):

                record[field] = None

        return record

    def make_approval_fixture(self):

        previous = self.make_completed_review()

        current = self.make_home("APPROVED")

        return [
            self.make_registry([previous]),
            self.make_registry([current]),
            self.make_audit(),
            self.make_audit([
                self.make_approval(current)
            ]),
        ]

    def make_rejection_fixture(
        self,
        complete=True,
        reset=False,
    ):

        if complete:

            previous = self.make_completed_review()

        else:

            previous = self.make_home(
                "UNDER_REVIEW"
            )

        if reset:

            current = self.make_home(
                "DEVELOPMENT"
            )

        else:

            current = copy.deepcopy(previous)

        rejection = self.make_rejection(
            previous,
            complete=complete,
        )

        return [
            self.make_registry([previous]),
            self.make_registry([current]),
            self.make_audit(),
            self.make_audit([rejection]),
        ]

    def make_retirement_fixture(self):

        previous = self.make_home("APPROVED")

        current = copy.deepcopy(previous)

        current["status"] = "RETIRED"

        approval = self.make_approval(previous)

        retirement = self.make_retirement(
            approval
        )

        return [
            self.make_registry([previous]),
            self.make_registry([current]),
            self.make_audit([
                copy.deepcopy(approval)
            ]),
            self.make_audit([
                approval,
                retirement,
            ]),
        ]

    def make_unchanged_fixture(self):

        registry = self.make_registry([
            self.make_home("DEVELOPMENT")
        ])

        audit = self.make_audit()

        return [
            registry,
            copy.deepcopy(registry),
            audit,
            copy.deepcopy(audit),
        ]

    def validate(self, fixture):

        return validate_audit_decision_history_data(
            *fixture
        )

    def assert_accepted(self, fixture):

        self.assertEqual(
            self.validate(fixture),
            [],
        )

    def assert_rejected(self, fixture, expected):

        errors = self.validate(fixture)

        self.assertTrue(
            any(
                expected in error
                for error in errors
            ),
            f"Expected {expected!r}; got {errors}",
        )

    def save_fixture(self, fixture):

        for path, data in zip(
            self.paths,
            fixture,
        ):

            path.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8",
            )

    def validate_files(self):

        return validate_audit_decision_history(
            *self.paths
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
    # VALID HISTORICAL DECISIONS

    def test_01_unchanged_development_history(self):

        self.assert_accepted(
            self.make_unchanged_fixture()
        )

    def test_02_valid_historical_approval(self):

        self.assert_accepted(
            self.make_approval_fixture()
        )

    def test_03_valid_historical_retirement(self):

        self.assert_accepted(
            self.make_retirement_fixture()
        )

    def test_04_valid_completed_review_rejection(self):

        self.assert_accepted(
            self.make_rejection_fixture()
        )

    def test_05_valid_incomplete_review_rejection(self):

        self.assert_accepted(
            self.make_rejection_fixture(
                complete=False
            )
        )

    # CATEGORY 2
    # HISTORICAL APPROVAL AUTHORIZATION

    def test_06_approval_from_development(self):

        fixture = self.make_approval_fixture()

        fixture[0]["reference_homes"] = [
            self.make_home("DEVELOPMENT")
        ]

        self.assert_rejected(
            fixture,
            "Unauthorized APPROVED audit decision",
        )

    def test_07_approval_without_prior_completed_review(self):

        fixture = self.make_approval_fixture()

        fixture[0]["reference_homes"] = [
            self.make_home("UNDER_REVIEW")
        ]

        self.assert_rejected(
            fixture,
            "previously accepted COMPLETED "
            "technical review",
        )

    def test_08_approval_without_prior_recommendation(self):

        fixture = self.make_approval_fixture()

        fixture[0]["reference_homes"][0][
            "review"
        ]["review_recommendation"] = (
            "REVISIONS_REQUIRED"
        )

        self.assert_rejected(
            fixture,
            "previously accepted RECOMMEND_APPROVAL",
        )

    def test_09_approval_without_prior_registration(self):

        fixture = self.make_approval_fixture()

        fixture[0]["reference_homes"] = [
            self.make_home(
                "DEVELOPMENT",
                "2.0.0",
                "002",
            )
        ]

        self.assert_rejected(
            fixture,
            "previously registered reference home version",
        )

    def test_10_approval_review_evidence_changed(self):

        fixture = self.make_approval_fixture()

        fixture[0]["reference_homes"][0][
            "review"
        ]["reviewer"] = (
            "Different Fictional Reviewer"
        )

        self.assert_rejected(
            fixture,
            "Historical technical review "
            "evidence mismatch: reviewer",
        )

    # CATEGORY 3
    # CONTROLLED REJECTION AUTHORIZATION

    def test_11_completed_review_rejection_with_reset(self):

        self.assert_accepted(
            self.make_rejection_fixture(
                complete=True,
                reset=True,
            )
        )

    def test_12_incomplete_review_rejection_with_reset(self):

        self.assert_accepted(
            self.make_rejection_fixture(
                complete=False,
                reset=True,
            )
        )

    def test_13_rejection_from_development(self):

        fixture = self.make_rejection_fixture()

        fixture[0]["reference_homes"] = [
            self.make_home("DEVELOPMENT")
        ]

        self.assert_rejected(
            fixture,
            "Unauthorized REJECTED audit decision",
        )

    def test_14_rejection_from_approved(self):

        fixture = self.make_retirement_fixture()

        previous = fixture[0]["reference_homes"][0]

        fixture[1] = copy.deepcopy(fixture[0])

        fixture[3] = copy.deepcopy(fixture[2])

        fixture[3]["records"].append(
            self.make_rejection(previous)
        )

        self.assert_rejected(
            fixture,
            "Unauthorized REJECTED audit decision",
        )

    def test_15_rejection_from_retired(self):

        retirement = self.make_retirement_fixture()

        registry = retirement[1]

        audit = retirement[3]

        fixture = [
            registry,
            copy.deepcopy(registry),
            audit,
            copy.deepcopy(audit),
        ]

        fixture[3]["records"].append(
            self.make_rejection(
                registry["reference_homes"][0]
            )
        )

        self.assert_rejected(
            fixture,
            "Unauthorized REJECTED audit decision",
        )

    def test_16_rejection_cannot_substitute_for_approval(self):

        fixture = self.make_approval_fixture()

        previous = fixture[0]["reference_homes"][0]

        fixture[3]["records"].append(
            self.make_rejection(previous)
        )

        self.assert_rejected(
            fixture,
            "Unauthorized REJECTED audit decision",
        )

    def test_17_completed_review_cannot_omit_evidence(self):

        fixture = self.make_rejection_fixture()

        rejection = fixture[3]["records"][0]

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            rejection[field] = None

        self.assert_rejected(
            fixture,
            "REJECTED decision must preserve "
            "previously accepted completed "
            "technical review evidence",
        )

    def test_18_rejection_cannot_use_newly_completed_review(self):

        fixture = self.make_rejection_fixture()

        fixture[0]["reference_homes"] = [
            self.make_home("UNDER_REVIEW")
        ]

        self.assert_rejected(
            fixture,
            "previously accepted COMPLETED "
            "technical review",
        )

    def test_19_rejection_review_evidence_mismatch(self):

        fixture = self.make_rejection_fixture()

        fixture[3]["records"][0][
            "technical_review_record"
        ] = "BEEP-REV-UNRELATED"

        self.assert_rejected(
            fixture,
            "Historical technical review evidence "
            "mismatch: technical_review_record",
        )

    def test_20_repeated_rejection_resolution(self):

        fixture = self.make_rejection_fixture()

        first = fixture[3]["records"][0]

        second = copy.deepcopy(first)

        second["record_id"] = (
            "BEEP-AUDIT-REJECTED-002"
        )

        second["board_resolution_reference"] = (
            first[
                "board_resolution_reference"
            ].lower()
        )

        fixture[2]["records"] = [
            copy.deepcopy(first)
        ]

        fixture[3]["records"].append(second)

        self.assert_rejected(
            fixture,
            "REJECTED decision requires an "
            "independent Board resolution",
        )

        second["board_resolution_reference"] = (
            "BEEP-RES-REJECTED-002"
        )

        self.assert_accepted(fixture)

    # CATEGORY 4
    # HISTORICAL RETIREMENT AUTHORIZATION

    def test_21_retirement_without_prior_approval(self):

        fixture = self.make_retirement_fixture()

        fixture[0]["reference_homes"] = [
            self.make_completed_review()
        ]

        fixture[2]["records"] = []

        self.assert_rejected(
            fixture,
            "Unauthorized APPROVED audit decision",
        )

        self.assert_rejected(
            fixture,
            "Unauthorized RETIRED audit decision",
        )

    def test_22_retirement_without_lifecycle_transition(self):

        fixture = self.make_retirement_fixture()

        fixture[1] = copy.deepcopy(fixture[0])

        self.assert_rejected(
            fixture,
            "ineligible reference home status: APPROVED",
        )

    def test_23_retirement_changes_approved_metadata(self):

        fixture = self.make_retirement_fixture()

        fixture[1]["reference_homes"][0][
            "test_cycles"
        ].append("BEEP-CYCLE-TEST-002")

        self.assert_rejected(
            fixture,
            "Retirement cannot modify previously "
            "approved reference home metadata",
        )

    def test_24_retirement_without_historical_audit(self):

        fixture = self.make_retirement_fixture()

        fixture[2]["records"] = []

        self.assert_rejected(
            fixture,
            "Missing original APPROVED audit decision",
        )

    def test_25_retirement_changes_original_evidence(self):

        fixture = self.make_retirement_fixture()

        fixture[3]["records"][1][
            "technical_review_sha256"
        ] = "c" * 64

        self.assert_rejected(
            fixture,
            "Retirement technical review evidence "
            "mismatch: technical_review_sha256",
        )

    # CATEGORY 5
    # APPEND-ONLY HISTORY AND SCHEMA MIGRATION

    def test_26_historical_audit_modification(self):

        fixture = self.make_retirement_fixture()

        fixture[3]["records"][0]["evidence"] = (
            "Modified historical evidence"
        )

        self.assert_rejected(
            fixture,
            "was modified or reordered",
        )

    def test_27_historical_audit_deletion(self):

        fixture = self.make_retirement_fixture()

        fixture[3]["records"] = []

        self.assert_rejected(
            fixture,
            "Audit history cannot remove existing records",
        )

    def test_28_historical_audit_reordering(self):

        fixture = self.make_retirement_fixture()

        fixture[3]["records"].reverse()

        self.assert_rejected(
            fixture,
            "was modified or reordered",
        )

    def test_29_valid_empty_schema_migration(self):

        fixture = self.make_unchanged_fixture()

        fixture[2]["audit_schema_version"] = (
            LEGACY_SCHEMA_VERSION
        )

        self.assert_accepted(fixture)

    def test_30_schema_migration_cannot_add_decisions(self):

        fixture = self.make_approval_fixture()

        fixture[2]["audit_schema_version"] = (
            LEGACY_SCHEMA_VERSION
        )

        self.assert_rejected(
            fixture,
            "Audit schema migration cannot "
            "introduce audit records",
        )

    # CATEGORY 6
    # CROSS-REGISTRY INTEGRITY

    def test_31_previous_reference_home_cannot_disappear(self):

        fixture = self.make_unchanged_fixture()

        fixture[1]["reference_homes"] = [
            self.make_home(
                "DEVELOPMENT",
                "2.0.0",
                "002",
            )
        ]

        self.assert_rejected(
            fixture,
            "Previously registered reference "
            "home version cannot be removed",
        )

    def test_32_independent_version_decisions(self):

        fixture = self.make_approval_fixture()

        previous_second = self.make_home(
            "APPROVED",
            "1.1.0",
            "002",
        )

        current_second = copy.deepcopy(
            previous_second
        )

        current_second["status"] = "RETIRED"

        approval_second = self.make_approval(
            previous_second
        )

        retirement_second = self.make_retirement(
            approval_second,
            "002",
        )

        fixture[0]["reference_homes"].append(
            previous_second
        )

        fixture[1]["reference_homes"].append(
            current_second
        )

        fixture[2]["records"].append(
            copy.deepcopy(approval_second)
        )

        fixture[3]["records"].insert(
            0,
            approval_second,
        )

        fixture[3]["records"].append(
            retirement_second
        )

        self.assert_accepted(fixture)

    def test_33_unchanged_historical_rejection(self):

        fixture = self.make_rejection_fixture(
            complete=True,
            reset=True,
        )

        self.assert_accepted(fixture)

        unchanged = [
            copy.deepcopy(fixture[1]),
            copy.deepcopy(fixture[1]),
            copy.deepcopy(fixture[3]),
            copy.deepcopy(fixture[3]),
        ]

        self.assert_accepted(unchanged)

    def test_34_invalid_registry_structure(self):

        for index in (0, 1):

            with self.subTest(index=index):

                fixture = self.make_unchanged_fixture()

                fixture[index] = None

                self.assert_rejected(
                    fixture,
                    "Reference registry must be an object",
                )

    def test_35_validation_does_not_modify_inputs(self):

        fixture = self.make_retirement_fixture()

        original = copy.deepcopy(fixture)

        self.assert_accepted(fixture)

        self.assertEqual(
            fixture,
            original,
        )

    # CATEGORY 7
    # FILE VALIDATION AND SECURITY

    def test_36_valid_historical_registry_files(self):

        fixture = self.make_approval_fixture()

        self.save_fixture(fixture)

        self.assertEqual(
            self.validate_files(),
            [],
        )

    def test_37_missing_registry_files(self):

        for path in self.paths:

            with self.subTest(path=path):

                self.save_fixture(
                    self.make_unchanged_fixture()
                )

                path.unlink()

                self.assert_file_rejected(
                    "Unable to validate historical "
                    "audit decisions",
                )

    def test_38_malformed_registry_json(self):

        for path in self.paths:

            with self.subTest(path=path):

                self.save_fixture(
                    self.make_unchanged_fixture()
                )

                path.write_text(
                    "{invalid JSON",
                    encoding="utf-8",
                )

                self.assert_file_rejected(
                    "Unable to validate historical "
                    "audit decisions",
                )

    def test_39_duplicate_json_keys(self):

        for path in self.paths:

            with self.subTest(path=path):

                self.save_fixture(
                    self.make_unchanged_fixture()
                )

                path.write_text(
                    '{"duplicate": 1, "duplicate": 2}',
                    encoding="utf-8",
                )

                self.assert_file_rejected(
                    "Duplicate JSON key: duplicate",
                )

    def test_40_registry_symbolic_links(self):

        for index, path in enumerate(self.paths):

            with self.subTest(path=path):

                self.save_fixture(
                    self.make_unchanged_fixture()
                )

                target = (
                    self.root
                    / f"external-{index}.json"
                )

                path.rename(target)

                path.symlink_to(target)

                self.assert_file_rejected(
                    "Historical decision registry "
                    "cannot be a symbolic link",
                )

                path.unlink()


if __name__ == "__main__":

    unittest.main(verbosity=2)
