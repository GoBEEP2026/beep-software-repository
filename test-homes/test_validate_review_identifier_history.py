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

from validate_review_identifier_history import (
    REGISTRY_RELATIVE_PATH,
    load_historical_identifier_registry,
    validate_append_only_reservations,
    validate_review_identifier_history,
)


class TestReviewIdentifierHistory(unittest.TestCase):

    def setUp(self):

        self.temp_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temp_directory.cleanup
        )

        self.repository_root = Path(
            self.temp_directory.name
        ).resolve()

        self.registry_path = (
            self.repository_root
            / REGISTRY_RELATIVE_PATH
        )

    def make_reservation(self, number=1, **changes):

        reservation = {
            "review_record_id": (
                f"BEEP-REV-TEST-{number:03d}"
            ),
            "reference_home_id": "BEEP-HOME-TEST",
            "reference_home_version": "1.0.0",
            "assigned_reviewer": "Fictional Test Reviewer",
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

    def write_registry(self, registry):

        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8",
        )

    def git(self, *arguments):

        result = subprocess.run(
            ["git", *arguments],
            cwd=self.repository_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        return result.stdout.decode(
            "utf-8"
        ).strip()

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
            "Controlled test baseline",
        )

        return self.git(
            "rev-parse",
            "HEAD",
        )

    def create_baseline(self, registry=None):

        self.initialize_repository()

        if registry is not None:

            self.write_registry(registry)

        return self.commit_repository()

    def assert_errors_contain(
        self,
        errors,
        expected_message,
    ):

        self.assertTrue(errors)

        self.assertTrue(
            any(
                expected_message in error
                for error in errors
            ),
            errors,
        )

    # Append-only reservation validation

    def test_unchanged_empty_registry(self):

        self.assertEqual(
            validate_append_only_reservations(
                self.make_registry(),
                self.make_registry(),
            ),
            [],
        )

    def test_unchanged_existing_reservations(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        self.assertEqual(
            validate_append_only_reservations(
                previous,
                copy.deepcopy(previous),
            ),
            [],
        )

    def test_append_first_reservation(self):

        self.assertEqual(
            validate_append_only_reservations(
                self.make_registry(),
                self.make_registry([
                    self.make_reservation()
                ]),
            ),
            [],
        )

    def test_append_multiple_reservations(self):

        previous = self.make_registry([
            self.make_reservation(1)
        ])

        current = self.make_registry([
            self.make_reservation(1),
            self.make_reservation(2),
            self.make_reservation(3),
        ])

        self.assertEqual(
            validate_append_only_reservations(
                previous,
                current,
            ),
            [],
        )

    def test_delete_historical_reservation(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                self.make_registry(),
            ),
            "Historical identifier reservations "
            "cannot be deleted",
        )

    def test_delete_middle_reservation(self):

        previous = self.make_registry([
            self.make_reservation(1),
            self.make_reservation(2),
            self.make_reservation(3),
        ])

        current = self.make_registry([
            self.make_reservation(1),
            self.make_reservation(3),
        ])

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "Historical identifier reservations "
            "cannot be deleted",
        )

    def test_modify_reserved_identifier(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        current = copy.deepcopy(previous)

        current["reservations"][0][
            "review_record_id"
        ] = "BEEP-REV-REPLACEMENT"

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_reassign_reference_home(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        current = copy.deepcopy(previous)

        current["reservations"][0][
            "reference_home_id"
        ] = "BEEP-HOME-OTHER"

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_reassign_reference_home_version(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        current = copy.deepcopy(previous)

        current["reservations"][0][
            "reference_home_version"
        ] = "2.0.0"

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_modify_assigned_reviewer(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        current = copy.deepcopy(previous)

        current["reservations"][0][
            "assigned_reviewer"
        ] = "Different Fictional Reviewer"

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_modify_assignment_date(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        current = copy.deepcopy(previous)

        current["reservations"][0][
            "assignment_date"
        ] = "2026-02-15"

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_reorder_historical_reservations(self):

        previous = self.make_registry([
            self.make_reservation(1),
            self.make_reservation(2),
        ])

        current = copy.deepcopy(previous)

        current["reservations"].reverse()

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_insert_between_historical_reservations(self):

        previous = self.make_registry([
            self.make_reservation(1),
            self.make_reservation(2),
        ])

        current = self.make_registry([
            self.make_reservation(1),
            self.make_reservation(3),
            self.make_reservation(2),
        ])

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_prepend_new_reservation(self):

        previous = self.make_registry([
            self.make_reservation(1)
        ])

        current = self.make_registry([
            self.make_reservation(2),
            self.make_reservation(1),
        ])

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_append_duplicate_identifier(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        current = copy.deepcopy(previous)

        current["reservations"].append(
            self.make_reservation()
        )

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "Duplicate technical review record identifier",
        )

    def test_append_case_insensitive_duplicate(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        current = copy.deepcopy(previous)

        current["reservations"].append(
            self.make_reservation(
                review_record_id="beep-rev-test-001"
            )
        )

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "Duplicate technical review record identifier",
        )

    def test_modify_reservation_policy(self):

        previous = self.make_registry()

        current = copy.deepcopy(previous)

        current["reservation_policy"][
            "identifier_reuse_allowed"
        ] = True

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "Invalid reservation policy field",
        )

    def test_modify_governance_authority(self):

        previous = self.make_registry()

        current = copy.deepcopy(previous)

        current["governance_authority"] = (
            "Unauthorized Authority"
        )

        self.assert_errors_contain(
            validate_append_only_reservations(
                previous,
                current,
            ),
            "Invalid registry field: governance_authority",
        )

    def test_invalid_historical_registry(self):

        self.assert_errors_contain(
            validate_append_only_reservations(
                [],
                self.make_registry(),
            ),
            "Historical registry:",
        )

    def test_invalid_current_registry(self):

        self.assert_errors_contain(
            validate_append_only_reservations(
                self.make_registry(),
                [],
            ),
            "Current registry:",
        )

    def test_original_registries_not_modified(self):

        previous = self.make_registry([
            self.make_reservation(1)
        ])

        current = self.make_registry([
            self.make_reservation(1),
            self.make_reservation(2),
        ])

        previous_copy = copy.deepcopy(previous)
        current_copy = copy.deepcopy(current)

        validate_append_only_reservations(
            previous,
            current,
        )

        self.assertEqual(previous, previous_copy)
        self.assertEqual(current, current_copy)

    # Historical Git registry loading

    def test_load_missing_historical_registry(self):

        base_commit = self.create_baseline()

        self.assertIsNone(
            load_historical_identifier_registry(
                self.repository_root,
                base_commit,
            )
        )

    def test_load_existing_historical_registry(self):

        registry = self.make_registry([
            self.make_reservation()
        ])

        base_commit = self.create_baseline(
            registry
        )

        self.assertEqual(
            load_historical_identifier_registry(
                self.repository_root,
                base_commit,
            ),
            registry,
        )

    def test_invalid_historical_commit_identifier(self):

        with self.assertRaises(ValueError):

            load_historical_identifier_registry(
                self.repository_root,
                "invalid-commit",
            )

    def test_unavailable_historical_commit(self):

        self.initialize_repository()

        with self.assertRaises(
            subprocess.CalledProcessError
        ):

            load_historical_identifier_registry(
                self.repository_root,
                "0" * 40,
            )

    def test_malformed_historical_json(self):

        self.initialize_repository()

        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.registry_path.write_text(
            "{invalid json",
            encoding="utf-8",
        )

        base_commit = self.commit_repository()

        with self.assertRaises(ValueError):

            load_historical_identifier_registry(
                self.repository_root,
                base_commit,
            )

    def test_null_historical_registry(self):

        base_commit = self.create_baseline(
            self.make_registry()
        )

        self.registry_path.write_text(
            "null",
            encoding="utf-8",
        )

        base_commit = self.commit_repository()

        with self.assertRaises(ValueError):

            load_historical_identifier_registry(
                self.repository_root,
                base_commit,
            )

    def test_duplicate_historical_json_keys(self):

        self.initialize_repository()

        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.registry_path.write_text(
            '{"reservations": [], "reservations": []}',
            encoding="utf-8",
        )

        base_commit = self.commit_repository()

        with self.assertRaises(ValueError):

            load_historical_identifier_registry(
                self.repository_root,
                base_commit,
            )

    # Integrated historical validation

    def test_initial_empty_registry_accepted(self):

        base_commit = self.create_baseline()

        self.write_registry(
            self.make_registry()
        )

        self.assertEqual(
            validate_review_identifier_history(
                base_commit,
                self.repository_root,
            ),
            [],
        )

    def test_initial_nonempty_registry_rejected(self):

        base_commit = self.create_baseline()

        self.write_registry(
            self.make_registry([
                self.make_reservation()
            ])
        )

        self.assert_errors_contain(
            validate_review_identifier_history(
                base_commit,
                self.repository_root,
            ),
            "Initial identifier reservation "
            "registry must be empty",
        )

    def test_integrated_unchanged_registry(self):

        base_commit = self.create_baseline(
            self.make_registry([
                self.make_reservation()
            ])
        )

        self.assertEqual(
            validate_review_identifier_history(
                base_commit,
                self.repository_root,
            ),
            [],
        )

    def test_integrated_appended_reservation(self):

        base_commit = self.create_baseline(
            self.make_registry([
                self.make_reservation(1)
            ])
        )

        self.write_registry(
            self.make_registry([
                self.make_reservation(1),
                self.make_reservation(2),
            ])
        )

        self.assertEqual(
            validate_review_identifier_history(
                base_commit,
                self.repository_root,
            ),
            [],
        )

    def test_integrated_deleted_reservation(self):

        base_commit = self.create_baseline(
            self.make_registry([
                self.make_reservation()
            ])
        )

        self.write_registry(
            self.make_registry()
        )

        self.assert_errors_contain(
            validate_review_identifier_history(
                base_commit,
                self.repository_root,
            ),
            "Historical identifier reservations "
            "cannot be deleted",
        )

    def test_integrated_modified_reservation(self):

        previous = self.make_registry([
            self.make_reservation()
        ])

        base_commit = self.create_baseline(
            previous
        )

        current = copy.deepcopy(previous)

        current["reservations"][0][
            "assigned_reviewer"
        ] = "Different Fictional Reviewer"

        self.write_registry(current)

        self.assert_errors_contain(
            validate_review_identifier_history(
                base_commit,
                self.repository_root,
            ),
            "cannot be modified, replaced, or reordered",
        )

    def test_integrated_missing_current_registry(self):

        base_commit = self.create_baseline(
            self.make_registry()
        )

        self.registry_path.unlink()

        self.assert_errors_contain(
            validate_review_identifier_history(
                base_commit,
                self.repository_root,
            ),
            "Current identifier reservation "
            "registry does not exist",
        )

    def test_integrated_symbolic_link_rejected(self):

        registry = self.make_registry()

        base_commit = self.create_baseline(
            registry
        )

        replacement = (
            self.repository_root
            / "replacement-registry.json"
        )

        replacement.write_text(
            json.dumps(registry),
            encoding="utf-8",
        )

        self.registry_path.unlink()

        self.registry_path.symlink_to(
            replacement
        )

        self.assert_errors_contain(
            validate_review_identifier_history(
                base_commit,
                self.repository_root,
            ),
            "Identifier registry path "
            "cannot contain symbolic links",
        )


if __name__ == "__main__":
    unittest.main()
