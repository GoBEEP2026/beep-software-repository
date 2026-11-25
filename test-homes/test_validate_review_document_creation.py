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

from validate_review_document_creation import (
    validate_document_creation_data,
    validate_review_document_creation,
)


class TestReviewDocumentCreation(unittest.TestCase):

    HOME_ID = "BEEP-HOME-TEST"
    VERSION = "1.0.0"
    RECORD_ID = "BEEP-REV-TEST-001"
    REVIEWER = "Fictional Test Reviewer"

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

        self.home_key = (
            self.HOME_ID,
            self.VERSION,
        )

        self.document_path = (
            f"{self.HOME_ID}/{self.VERSION}/"
            f"technical-reviews/{self.RECORD_ID}.md"
        )

    def make_home(
        self,
        review_status="NOT_STARTED",
        record_id=None,
        reviewer=None,
    ):

        if record_id is None:
            record_id = self.RECORD_ID

        if reviewer is None:
            reviewer = self.REVIEWER

        home = {
            "test_home_id": self.HOME_ID,
            "test_home_version": self.VERSION,

            "status": (
                "DEVELOPMENT"
                if review_status == "NOT_STARTED"
                else "UNDER_REVIEW"
            ),

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

        review = home["review"]

        if review_status in (
            "IN_PROGRESS",
            "COMPLETED",
        ):

            review.update({
                "reviewer": reviewer,
                "review_record": record_id,
                "conflict_of_interest_disclosure":
                    "Fictional test disclosure",
            })

        if review_status == "COMPLETED":

            review.update({
                "review_date": "2026-01-20",
                "review_findings":
                    "Fictional test findings",
                "review_recommendation":
                    "RECOMMEND_APPROVAL",
                "reviewed_content_sha256":
                    calculate_technical_fingerprint(
                        home
                    ),
            })

        return home

    def make_document(
        self,
        home=None,
        changes=None,
        omit=None,
    ):

        if home is None:

            home = self.make_home(
                "COMPLETED"
            )

        review = home["review"]

        fields = {
            "Reference Home ID":
                home["test_home_id"],

            "Reference Home Version":
                home["test_home_version"],

            "Technical Review Record ID":
                review["review_record"],

            "Technical Reviewer":
                review["reviewer"],

            "Technical Review Date":
                review["review_date"],

            "Technical Review Status":
                review["review_status"],

            "Review Scope":
                "Fictional technical review",

            "Review Findings":
                review["review_findings"],

            "Review Recommendation":
                review["review_recommendation"],

            "Conflict-of-Interest Disclosure":
                review[
                    "conflict_of_interest_disclosure"
                ],

            "Reviewed Content SHA-256":
                review["reviewed_content_sha256"],

            "Supporting Evidence":
                "Fictional supporting evidence",
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

    def make_reservation(self, **changes):

        reservation = {
            "review_record_id": self.RECORD_ID,
            "reference_home_id": self.HOME_ID,
            "reference_home_version": self.VERSION,
            "assigned_reviewer": self.REVIEWER,
            "assignment_date": "2026-01-15",
        }

        reservation.update(changes)

        return reservation

    def make_identifier_registry(
        self,
        reservations=None,
    ):

        return {
            "registry_schema_version":
                SCHEMA_VERSION,

            "registry_status":
                "DEVELOPMENT",

            "registry_name":
                REGISTRY_NAME,

            "governance_authority":
                GOVERNANCE_AUTHORITY,

            "reservation_policy":
                copy.deepcopy(EXPECTED_POLICY),

            "reservations": (
                []
                if reservations is None
                else reservations
            ),
        }

    def lookup(self, home):

        if home is None:
            return {}

        return {
            (
                home["test_home_id"],
                home["test_home_version"],
            ): home
        }

    def validate(
        self,
        previous_home,
        current_home,
        previous_paths=None,
        documents=None,
    ):

        if previous_paths is None:
            previous_paths = set()

        if documents is None:
            documents = {}

        return validate_document_creation_data(
            self.lookup(previous_home),
            self.lookup(current_home),
            previous_paths,
            documents,
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

    def git(self, *arguments):

        result = subprocess.run(
            ["git", *arguments],
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        return result.stdout.decode(
            "utf-8"
        ).strip()

    def initialize_repository(self):

        self.git("init", "-q")

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

        (
            self.root / "test-homes"
        ).mkdir()

        (
            self.root / "approvals"
        ).mkdir()

        (
            self.root / "approvals" / "README.md"
        ).write_text(
            "Fictional approvals directory\n",
            encoding="utf-8",
        )

    def write_registries(
        self,
        home,
        reservations=None,
    ):

        reference_registry = {
            "registry_version": "1.1.0",
            "registry_status": "DEVELOPMENT",
            "reference_homes": [home],
        }

        (
            self.root
            / "test-homes"
            / "reference-home-registry.json"
        ).write_text(
            json.dumps(reference_registry),
            encoding="utf-8",
        )

        (
            self.root
            / "test-homes"
            / "reference-review-identifier-registry.json"
        ).write_text(
            json.dumps(
                self.make_identifier_registry(
                    reservations
                )
            ),
            encoding="utf-8",
        )

    def write_document(
        self,
        content=None,
        relative_path=None,
    ):

        if content is None:
            content = self.make_document()

        if relative_path is None:
            relative_path = self.document_path

        path = (
            self.root
            / "approvals"
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

    def commit_repository(self):

        self.git("add", ".")

        self.git(
            "commit",
            "-qm",
            "Fictional test commit",
        )

        return self.git(
            "rev-parse",
            "HEAD",
        )

    def create_baseline(
        self,
        status="IN_PROGRESS",
        include_document=False,
    ):

        self.initialize_repository()

        home = self.make_home(status)

        reservations = (
            []
            if status == "NOT_STARTED"
            else [self.make_reservation()]
        )

        self.write_registries(
            home,
            reservations,
        )

        if include_document:

            self.write_document(
                self.make_document(home)
            )

        return self.commit_repository()

    # Valid review and document scenarios

    def test_01_unchanged_not_started_review(self):

        home = self.make_home()

        self.assertEqual(
            self.validate(home, home),
            [],
        )

    def test_02_unchanged_in_progress_review(self):

        home = self.make_home(
            "IN_PROGRESS"
        )

        self.assertEqual(
            self.validate(home, home),
            [],
        )

    def test_03_legitimate_review_completion(self):

        previous = self.make_home(
            "IN_PROGRESS"
        )

        current = self.make_home(
            "COMPLETED"
        )

        self.assertEqual(
            self.validate(
                previous,
                current,
                documents={
                    self.document_path:
                        self.make_document(current)
                },
            ),
            [],
        )

    def test_04_unchanged_completed_review(self):

        home = self.make_home(
            "COMPLETED"
        )

        self.assertEqual(
            self.validate(
                home,
                home,
                {self.document_path},
                {
                    self.document_path:
                        self.make_document(home)
                },
            ),
            [],
        )

    def test_05_preserved_document_after_reset(self):

        previous = self.make_home(
            "COMPLETED"
        )

        current = self.make_home()

        self.assertEqual(
            self.validate(
                previous,
                current,
                {self.document_path},
                {
                    self.document_path:
                        self.make_document(previous)
                },
            ),
            [],
        )

    def test_06_abandoned_review_without_document(self):

        self.assertEqual(
            self.validate(
                self.make_home("IN_PROGRESS"),
                self.make_home(),
            ),
            [],
        )

    def test_07_new_development_home(self):

        self.assertEqual(
            self.validate(
                None,
                self.make_home(),
            ),
            [],
        )

    def test_08_new_review_assignment_without_document(self):

        self.assertEqual(
            self.validate(
                self.make_home(),
                self.make_home("IN_PROGRESS"),
            ),
            [],
        )

    def test_09_revisions_required_completion(self):

        previous = self.make_home(
            "IN_PROGRESS"
        )

        current = self.make_home(
            "COMPLETED"
        )

        current["review"][
            "review_recommendation"
        ] = "REVISIONS_REQUIRED"

        self.assertEqual(
            self.validate(
                previous,
                current,
                documents={
                    self.document_path:
                        self.make_document(current)
                },
            ),
            [],
        )

    def test_10_inputs_remain_unchanged(self):

        previous = self.make_home(
            "IN_PROGRESS"
        )

        current = self.make_home(
            "COMPLETED"
        )

        documents = {
            self.document_path:
                self.make_document(current)
        }

        original = copy.deepcopy((
            previous,
            current,
            documents,
        ))

        self.validate(
            previous,
            current,
            documents=documents,
        )

        self.assertEqual(
            (previous, current, documents),
            original,
        )

    # Unauthorized document creation

    def test_11_document_for_not_started_review(self):

        self.assert_rejected(
            self.validate(
                self.make_home(),
                self.make_home(),
                documents={
                    self.document_path:
                        self.make_document()
                },
            ),
            "has no authorized review completion",
        )

    def test_12_document_for_in_progress_review(self):

        home = self.make_home(
            "IN_PROGRESS"
        )

        self.assert_rejected(
            self.validate(
                home,
                home,
                documents={
                    self.document_path:
                        self.make_document()
                },
            ),
            "has no authorized review completion",
        )

    def test_13_document_for_abandoned_review(self):

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                self.make_home(),
                documents={
                    self.document_path:
                        self.make_document()
                },
            ),
            "has no authorized review completion",
        )

    def test_14_direct_not_started_to_completed(self):

        current = self.make_home(
            "COMPLETED"
        )

        self.assert_rejected(
            self.validate(
                self.make_home(),
                current,
                documents={
                    self.document_path:
                        self.make_document(current)
                },
            )
        )

    def test_15_completed_review_without_document(self):

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                self.make_home("COMPLETED"),
            ),
            "requires a supporting document",
        )

    def test_16_retroactive_document_creation(self):

        home = self.make_home(
            "COMPLETED"
        )

        self.assert_rejected(
            self.validate(
                home,
                home,
                documents={
                    self.document_path:
                        self.make_document(home)
                },
            ),
            "requires an IN_PROGRESS to COMPLETED transition",
        )

    def test_17_changed_reviewer_during_completion(self):

        current = self.make_home(
            "COMPLETED",
            reviewer="Different Test Reviewer",
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                documents={
                    self.document_path:
                        self.make_document(current)
                },
            )
        )

    def test_18_changed_identifier_during_completion(self):

        current = self.make_home(
            "COMPLETED",
            record_id="BEEP-REV-TEST-002",
        )

        path = (
            f"{self.HOME_ID}/{self.VERSION}/"
            "technical-reviews/BEEP-REV-TEST-002.md"
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                documents={
                    path:
                        self.make_document(current)
                },
            )
        )

    def test_19_existing_document_reuse(self):

        current = self.make_home(
            "COMPLETED"
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                {self.document_path},
                {
                    self.document_path:
                        self.make_document(current)
                },
            ),
            "Existing historical document cannot be reused",
        )

    def test_20_completed_new_home_without_history(self):

        current = self.make_home(
            "COMPLETED"
        )

        self.assert_rejected(
            self.validate(
                None,
                current,
                documents={
                    self.document_path:
                        self.make_document(current)
                },
            ),
            "requires a historical reference home",
        )

    # Document consistency and preservation

    def test_21_mismatched_document_fingerprint(self):

        current = self.make_home(
            "COMPLETED"
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                documents={
                    self.document_path:
                        self.make_document(
                            current,
                            changes={
                                "Reviewed Content SHA-256":
                                    "0" * 64,
                            },
                        )
                },
            ),
            "mismatched Reviewed Content SHA-256",
        )

    def test_22_invalid_current_review_fingerprint(self):

        current = self.make_home(
            "COMPLETED"
        )

        current[
            "conditioned_floor_area_ft2"
        ] = 2400

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                documents={
                    self.document_path:
                        self.make_document(current)
                },
            ),
            "fingerprint does not match",
        )

    def test_23_mismatched_document_reviewer(self):

        current = self.make_home(
            "COMPLETED"
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                documents={
                    self.document_path:
                        self.make_document(
                            current,
                            changes={
                                "Technical Reviewer":
                                    "Different Reviewer",
                            },
                        )
                },
            ),
            "mismatched Technical Reviewer",
        )

    def test_24_missing_document_metadata(self):

        current = self.make_home(
            "COMPLETED"
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                documents={
                    self.document_path:
                        self.make_document(
                            current,
                            omit="Supporting Evidence",
                        )
                },
            ),
            "Missing required field",
        )

    def test_25_extra_unauthorized_document(self):

        current = self.make_home(
            "COMPLETED"
        )

        extra_path = (
            f"{self.HOME_ID}/{self.VERSION}/"
            "technical-reviews/BEEP-REV-TEST-002.md"
        )

        self.assert_rejected(
            self.validate(
                self.make_home("IN_PROGRESS"),
                current,
                documents={
                    self.document_path:
                        self.make_document(current),

                    extra_path:
                        self.make_document(current),
                },
            ),
            "has no authorized review completion",
        )

    def test_26_historical_document_removed(self):

        self.assert_rejected(
            self.validate(
                self.make_home("COMPLETED"),
                self.make_home(),
                {self.document_path},
                {},
            ),
            "Historical technical review document cannot be removed",
        )

    def test_27_malformed_document_path(self):

        home = self.make_home()

        self.assert_rejected(
            self.validate(
                home,
                home,
                documents={
                    "invalid.md":
                        self.make_document()
                },
            ),
            "Invalid technical review document directory structure",
        )

    def test_28_invalid_historical_home_lookup(self):

        self.assert_rejected(
            validate_document_creation_data(
                [],
                {},
                set(),
                {},
            ),
            "Historical reference home lookup",
        )

    def test_29_invalid_current_home_lookup(self):

        self.assert_rejected(
            validate_document_creation_data(
                {},
                [],
                set(),
                {},
            ),
            "Current reference home lookup",
        )

    def test_30_invalid_historical_document_paths(self):

        self.assert_rejected(
            validate_document_creation_data(
                {},
                {},
                [],
                {},
            ),
            "Historical document paths",
        )

    def test_31_invalid_current_documents(self):

        self.assert_rejected(
            validate_document_creation_data(
                {},
                {},
                set(),
                [],
            ),
            "Current technical review documents",
        )

    def test_32_home_lookup_identity_mismatch(self):

        home = self.make_home()

        self.assert_rejected(
            validate_document_creation_data(
                self.lookup(home),
                {
                    ("WRONG-HOME", "1.0.0"):
                        home
                },
                set(),
                {},
            ),
            "Reference home lookup identity mismatch",
        )

    # Integrated historical Git repository tests

    def test_33_git_legitimate_completion(self):

        base = self.create_baseline()

        current = self.make_home(
            "COMPLETED"
        )

        self.write_registries(
            current,
            [self.make_reservation()],
        )

        self.write_document(
            self.make_document(current)
        )

        self.assertEqual(
            validate_review_document_creation(
                base,
                self.root,
            ),
            [],
        )

    def test_34_git_abandoned_document_rejected(self):

        self.create_baseline()

        self.write_registries(
            self.make_home(),
            [self.make_reservation()],
        )

        base = self.commit_repository()

        self.write_document()

        self.assert_rejected(
            validate_review_document_creation(
                base,
                self.root,
            ),
            "has no authorized review completion",
        )

    def test_35_git_historical_document_preserved(self):

        base = self.create_baseline(
            status="COMPLETED",
            include_document=True,
        )

        self.write_registries(
            self.make_home(),
            [self.make_reservation()],
        )

        self.assertEqual(
            validate_review_document_creation(
                base,
                self.root,
            ),
            [],
        )

    def test_36_git_historical_document_modified(self):

        base = self.create_baseline(
            status="COMPLETED",
            include_document=True,
        )

        path = (
            self.root
            / "approvals"
            / self.document_path
        )

        path.write_text(
            path.read_text(
                encoding="utf-8"
            ) + "\nUnauthorized modification\n",
            encoding="utf-8",
        )

        self.assert_rejected(
            validate_review_document_creation(
                base,
                self.root,
            ),
            "cannot be modified",
        )

    def test_37_git_historical_document_deleted(self):

        base = self.create_baseline(
            status="COMPLETED",
            include_document=True,
        )

        (
            self.root
            / "approvals"
            / self.document_path
        ).unlink()

        self.assert_rejected(
            validate_review_document_creation(
                base,
                self.root,
            ),
            "cannot be deleted or renamed",
        )

    def test_38_git_invalid_base_commit(self):

        self.assert_rejected(
            validate_review_document_creation(
                "invalid-commit",
                self.root,
            ),
            "Invalid historical Git commit identifier",
        )

    def test_39_git_document_without_reservation(self):

        base = self.create_baseline(
            status="NOT_STARTED",
        )

        self.write_document()

        self.assert_rejected(
            validate_review_document_creation(
                base,
                self.root,
            ),
            "has no permanent identifier reservation",
        )

    def test_40_git_completion_without_document(self):

        base = self.create_baseline()

        self.write_registries(
            self.make_home("COMPLETED"),
            [self.make_reservation()],
        )

        self.assert_rejected(
            validate_review_document_creation(
                base,
                self.root,
            ),
            "requires a supporting document",
        )


if __name__ == "__main__":
    unittest.main()
