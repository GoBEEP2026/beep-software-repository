import copy
import json
import subprocess
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

from validate_review_assignment_history import (
    REFERENCE_REGISTRY_RELATIVE_PATH,
    build_home_lookup,
    get_active_assignment,
    load_historical_reference_registry,
    validate_historical_assignment_data,
    validate_review_assignment_history,
)

from validate_review_identifier_history import (
    REGISTRY_RELATIVE_PATH,
)


class TestReviewAssignmentHistory(unittest.TestCase):

    def setUp(self):

        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp_directory.cleanup
        )

        self.repository_root = Path(
            self.temp_directory.name
        )

        self.reference_path = (
            self.repository_root
            / REFERENCE_REGISTRY_RELATIVE_PATH
        )

        self.identifier_path = (
            self.repository_root
            / REGISTRY_RELATIVE_PATH
        )

        self.reference_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def make_home(
        self,
        review_status="NOT_STARTED",
        record_id="BEEP-REV-TEST-001",
        reviewer="Fictional Test Reviewer",
        home_id="BEEP-HOME-TEST",
        version="1.0.0",
    ):

        home = {
            "test_home_id": home_id,
            "test_home_version": version,
            "status": "DEVELOPMENT",
            "conditioned_floor_area_ft2": 2200,
            "conditioned_volume_ft3": 19800,
            "bedrooms": 3,
            "review": {
                "reviewer": None,
                "review_record": None,
                "review_status": review_status,
                "review_date": None,
                "review_findings": None,
                "review_recommendation": None,
                "conflict_of_interest_disclosure": None,
                "reviewed_content_sha256": None,
            },
        }

        if review_status in (
            "IN_PROGRESS",
            "COMPLETED",
        ):

            home["status"] = "UNDER_REVIEW"

            home["review"].update({
                "reviewer": reviewer,
                "review_record": record_id,
                "conflict_of_interest_disclosure": (
                    "Fictional test disclosure"
                ),
            })

        if review_status == "COMPLETED":

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

    def validate(
        self,
        previous_home,
        current_home,
        previous_reservations,
        current_reservations,
    ):

        previous_registry = (
            None
            if previous_reservations is None
            else self.make_registry(
                previous_reservations
            )
        )

        return validate_historical_assignment_data(
            self.make_lookup(previous_home),
            self.make_lookup(current_home),
            previous_registry,
            self.make_registry(
                current_reservations
            ),
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

    def write_registries(
        self,
        homes,
        reservations,
    ):

        self.reference_path.write_text(
            json.dumps({
                "reference_homes": homes,
            }),
            encoding="utf-8",
        )

        if reservations is None:

            self.identifier_path.unlink(
                missing_ok=True
            )

        else:

            self.identifier_path.write_text(
                json.dumps(
                    self.make_registry(
                        reservations
                    )
                ),
                encoding="utf-8",
            )

    def git(self, *arguments):

        return subprocess.run(
            ["git", *arguments],
            cwd=self.repository_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.decode("utf-8").strip()

    def initialize_repository(self):

        self.git("init")

        self.git(
            "config",
            "user.name",
            "Fictional Test User",
        )

        self.git(
            "config",
            "user.email",
            "test@example.invalid",
        )

        self.git(
            "config",
            "commit.gpgsign",
            "false",
        )

        self.git(
            "config",
            "core.autocrlf",
            "false",
        )

    def commit_repository(self):

        self.git("add", ".")

        self.git(
            "commit",
            "--allow-empty",
            "-m",
            "Fictional test baseline",
        )

        return self.git(
            "rev-parse",
            "HEAD",
        )

    def create_baseline(
        self,
        homes,
        reservations,
    ):

        self.initialize_repository()

        self.write_registries(
            homes,
            reservations,
        )

        return self.commit_repository()

    # Valid historical assignment transitions

    def test_01_unchanged_not_started(self):

        home = self.make_home()

        self.assertEqual(
            self.validate(home, home, [], []),
            [],
        )

    def test_02_initial_empty_registry(self):

        home = self.make_home()

        self.assertEqual(
            self.validate(home, home, None, []),
            [],
        )

    def test_03_legacy_development_bootstrap(self):

        previous = self.make_home()

        del previous["review"]

        self.assertEqual(
            self.validate(
                previous,
                self.make_home(),
                None,
                [],
            ),
            [],
        )

    def test_04_new_assignment_with_reservation(self):

        self.assertEqual(
            self.validate(
                self.make_home(),
                self.make_home("IN_PROGRESS"),
                [],
                [self.make_reservation()],
            ),
            [],
        )

    def test_05_existing_assignment_continues(self):

        home = self.make_home("IN_PROGRESS")

        reservations = [
            self.make_reservation()
        ]

        self.assertEqual(
            self.validate(
                home,
                copy.deepcopy(home),
                reservations,
                reservations,
            ),
            [],
        )

    def test_06_existing_assignment_completes(self):

        reservations = [
            self.make_reservation()
        ]

        self.assertEqual(
            self.validate(
                self.make_home("IN_PROGRESS"),
                self.make_home("COMPLETED"),
                reservations,
                reservations,
            ),
            [],
        )

    def test_07_in_progress_assignment_reset(self):

        reservations = [
            self.make_reservation()
        ]

        self.assertEqual(
            self.validate(
                self.make_home("IN_PROGRESS"),
                self.make_home(),
                reservations,
                reservations,
            ),
            [],
        )

    def test_08_completed_assignment_reset(self):

        reservations = [
            self.make_reservation()
        ]

        self.assertEqual(
            self.validate(
                self.make_home("COMPLETED"),
                self.make_home(),
                reservations,
                reservations,
            ),
            [],
        )

    def test_09_unchanged_completed_assignment(self):

        home = self.make_home("COMPLETED")

        reservations = [
            self.make_reservation()
        ]

        self.assertEqual(
            self.validate(
                home,
                copy.deepcopy(home),
                reservations,
                reservations,
            ),
            [],
        )

    def test_10_new_assignment_after_abandonment(self):

        old_reservation = self.make_reservation()

        new_reservation = self.make_reservation(
            review_record_id="BEEP-REV-TEST-002"
        )

        current = self.make_home(
            "IN_PROGRESS",
            record_id="BEEP-REV-TEST-002",
        )

        self.assertEqual(
            self.validate(
                self.make_home(),
                current,
                [old_reservation],
                [
                    old_reservation,
                    new_reservation,
                ],
            ),
            [],
        )

    # Permanent identifier reuse prevention

    def test_11_abandoned_identifier_reuse(self):

        reservations = [
            self.make_reservation()
        ]

        self.assert_rejected(
            self.validate(
                self.make_home(),
                self.make_home("IN_PROGRESS"),
                reservations,
                reservations,
            ),
            "cannot be reused",
        )

    def test_12_completed_identifier_reuse_after_reset(self):

        completed = self.make_home("COMPLETED")

        reset = self.make_home()

        reservations = [
            self.make_reservation()
        ]

        self.assertEqual(
            self.validate(
                completed,
                reset,
                reservations,
                reservations,
            ),
            [],
        )

        self.assert_rejected(
            self.validate(
                reset,
                self.make_home("IN_PROGRESS"),
                reservations,
                reservations,
            ),
            "cannot be reused",
        )

    def test_13_case_variant_identifier_reuse(self):

        reservations = [
            self.make_reservation()
        ]

        current = self.make_home(
            "IN_PROGRESS",
            record_id="beep-rev-test-001",
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                current,
                reservations,
                reservations,
            )
        )

    def test_14_existing_identifier_cannot_change(self):

        old_reservation = self.make_reservation()

        new_reservation = self.make_reservation(
            review_record_id="BEEP-REV-TEST-002"
        )

        current = self.make_home(
            "IN_PROGRESS",
            record_id="BEEP-REV-TEST-002",
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                [old_reservation],
                [
                    old_reservation,
                    new_reservation,
                ],
            ),
            "identifier cannot be changed",
        )

    def test_15_existing_reviewer_cannot_change(self):

        old_reservation = self.make_reservation()

        new_reservation = self.make_reservation(
            review_record_id="BEEP-REV-TEST-002",
            assigned_reviewer="Different Reviewer",
        )

        current = self.make_home(
            "IN_PROGRESS",
            record_id="BEEP-REV-TEST-002",
            reviewer="Different Reviewer",
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                [old_reservation],
                [
                    old_reservation,
                    new_reservation,
                ],
            ),
            "reviewer cannot be changed",
        )

    def test_16_reviewer_change_on_completion(self):

        old_reservation = self.make_reservation()

        new_reservation = self.make_reservation(
            review_record_id="BEEP-REV-TEST-002",
            assigned_reviewer="Different Reviewer",
        )

        current = self.make_home(
            "COMPLETED",
            record_id="BEEP-REV-TEST-002",
            reviewer="Different Reviewer",
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                [old_reservation],
                [
                    old_reservation,
                    new_reservation,
                ],
            ),
            "reviewer cannot be changed",
        )

    def test_17_assignment_without_reservation(self):

        self.assert_rejected(
            self.validate(
                self.make_home(),
                self.make_home("IN_PROGRESS"),
                [],
                [],
            ),
            "has no permanent reservation",
        )

    def test_18_orphan_new_reservation(self):

        home = self.make_home()

        self.assert_rejected(
            self.validate(
                home,
                home,
                [],
                [self.make_reservation()],
            ),
            "has no corresponding new review assignment",
        )

    def test_19_multiple_reservations_one_assignment(self):

        reservations = [
            self.make_reservation(),
            self.make_reservation(
                review_record_id="BEEP-REV-TEST-002"
            ),
        ]

        self.assert_rejected(
            self.validate(
                self.make_home(),
                self.make_home("IN_PROGRESS"),
                [],
                reservations,
            ),
            "has no corresponding new review assignment",
        )

    def test_20_reservation_cannot_be_deleted_on_reset(self):

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                self.make_home(),
                [self.make_reservation()],
                [],
            ),
            "cannot be deleted",
        )

    # Historical integrity and transition safeguards

    def test_21_historical_reservation_modification(self):

        home = self.make_home()

        self.assert_rejected(
            self.validate(
                home,
                home,
                [self.make_reservation()],
                [
                    self.make_reservation(
                        assignment_date="2026-01-16"
                    )
                ],
            ),
            "cannot be modified",
        )

    def test_22_initial_registry_cannot_contain_reservations(self):

        home = self.make_home()

        self.assert_rejected(
            self.validate(
                home,
                home,
                None,
                [self.make_reservation()],
            ),
            "must be empty",
        )

    def test_23_preexisting_assignment_before_bootstrap(self):

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                self.make_home(),
                None,
                [],
            ),
            "exists before establishment",
        )

    def test_24_historical_assignment_without_reservation(self):

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                self.make_home(),
                [],
                [],
            ),
            "Historical assignment:",
        )

    def test_25_direct_transition_to_completed(self):

        self.assert_rejected(
            self.validate(
                self.make_home(),
                self.make_home("COMPLETED"),
                [],
                [self.make_reservation()],
            )
        )

    def test_26_historical_home_cannot_be_removed(self):

        previous = self.make_home()

        current = self.make_home(
            home_id="BEEP-HOME-OTHER"
        )

        self.assert_rejected(
            validate_historical_assignment_data(
                self.make_lookup(previous),
                self.make_lookup(current),
                self.make_registry(),
                self.make_registry(),
            ),
            "cannot be removed",
        )

    def test_27_new_development_home_allowed(self):

        previous = self.make_home()

        new_home = self.make_home(
            home_id="BEEP-HOME-OTHER"
        )

        self.assertEqual(
            validate_historical_assignment_data(
                self.make_lookup(previous),
                self.make_lookup(
                    previous,
                    new_home,
                ),
                self.make_registry(),
                self.make_registry(),
            ),
            [],
        )

    def test_28_new_home_cannot_begin_under_review(self):

        previous = self.make_home()

        new_home = self.make_home(
            "IN_PROGRESS",
            home_id="BEEP-HOME-OTHER",
        )

        reservation = self.make_reservation(
            reference_home_id="BEEP-HOME-OTHER"
        )

        self.assert_rejected(
            validate_historical_assignment_data(
                self.make_lookup(previous),
                self.make_lookup(
                    previous,
                    new_home,
                ),
                self.make_registry(),
                self.make_registry([
                    reservation
                ]),
            ),
            "must begin in DEVELOPMENT",
        )

    def test_29_duplicate_home_lookup_rejected(self):

        home = self.make_home()

        with self.assertRaises(ValueError):

            build_home_lookup(
                {
                    "reference_homes": [
                        home,
                        copy.deepcopy(home),
                    ]
                },
                "Historical",
            )

    def test_30_invalid_assignment_status_rejected(self):

        home = self.make_home()

        home["review"]["review_status"] = (
            "INVALID"
        )

        with self.assertRaises(ValueError):

            get_active_assignment(home)

    def test_31_original_inputs_not_modified(self):

        previous = self.make_lookup(
            self.make_home()
        )

        current = self.make_lookup(
            self.make_home("IN_PROGRESS")
        )

        previous_registry = self.make_registry()

        current_registry = self.make_registry([
            self.make_reservation()
        ])

        original = copy.deepcopy((
            previous,
            current,
            previous_registry,
            current_registry,
        ))

        validate_historical_assignment_data(
            previous,
            current,
            previous_registry,
            current_registry,
        )

        self.assertEqual(
            (
                previous,
                current,
                previous_registry,
                current_registry,
            ),
            original,
        )

    # Integrated Git repository validation

    def test_32_git_initial_empty_registry(self):

        home = self.make_home()

        base_commit = self.create_baseline(
            [home],
            None,
        )

        self.write_registries(
            [home],
            [],
        )

        self.assertEqual(
            validate_review_assignment_history(
                base_commit,
                self.repository_root,
            ),
            [],
        )

    def test_33_git_new_assignment(self):

        base_commit = self.create_baseline(
            [self.make_home()],
            [],
        )

        self.write_registries(
            [self.make_home("IN_PROGRESS")],
            [self.make_reservation()],
        )

        self.assertEqual(
            validate_review_assignment_history(
                base_commit,
                self.repository_root,
            ),
            [],
        )

    def test_34_git_abandoned_identifier_reuse(self):

        reservations = [
            self.make_reservation()
        ]

        base_commit = self.create_baseline(
            [self.make_home("IN_PROGRESS")],
            reservations,
        )

        self.write_registries(
            [self.make_home()],
            reservations,
        )

        self.assertEqual(
            validate_review_assignment_history(
                base_commit,
                self.repository_root,
            ),
            [],
        )

        reset_commit = self.commit_repository()

        self.write_registries(
            [self.make_home("IN_PROGRESS")],
            reservations,
        )

        self.assert_rejected(
            validate_review_assignment_history(
                reset_commit,
                self.repository_root,
            ),
            "cannot be reused",
        )

    def test_35_git_orphan_reservation(self):

        home = self.make_home()

        base_commit = self.create_baseline(
            [home],
            [],
        )

        self.write_registries(
            [home],
            [self.make_reservation()],
        )

        self.assert_rejected(
            validate_review_assignment_history(
                base_commit,
                self.repository_root,
            ),
            "has no corresponding new review assignment",
        )

    def test_36_git_invalid_commit_identifier(self):

        self.create_baseline(
            [self.make_home()],
            [],
        )

        self.assert_rejected(
            validate_review_assignment_history(
                "invalid-commit",
                self.repository_root,
            )
        )

    def test_37_git_missing_current_reference_registry(self):

        base_commit = self.create_baseline(
            [self.make_home()],
            [],
        )

        self.reference_path.unlink()

        self.assert_rejected(
            validate_review_assignment_history(
                base_commit,
                self.repository_root,
            ),
            "regular file",
        )

    def test_38_git_duplicate_current_json_keys(self):

        base_commit = self.create_baseline(
            [self.make_home()],
            [],
        )

        self.reference_path.write_text(
            '{"reference_homes": [], '
            '"reference_homes": []}',
            encoding="utf-8",
        )

        self.assert_rejected(
            validate_review_assignment_history(
                base_commit,
                self.repository_root,
            )
        )

    def test_39_git_current_reference_symlink(self):

        base_commit = self.create_baseline(
            [self.make_home()],
            [],
        )

        target = (
            self.repository_root
            / "alternate-registry.json"
        )

        self.reference_path.rename(target)

        self.reference_path.symlink_to(target)

        self.assert_rejected(
            validate_review_assignment_history(
                base_commit,
                self.repository_root,
            ),
            "symbolic links",
        )

    def test_40_git_load_historical_reference_registry(self):

        home = self.make_home()

        base_commit = self.create_baseline(
            [home],
            [],
        )

        self.assertEqual(
            load_historical_reference_registry(
                self.repository_root,
                base_commit,
            ),
            {
                "reference_homes": [home]
            },
        )


if __name__ == "__main__":
    unittest.main()
