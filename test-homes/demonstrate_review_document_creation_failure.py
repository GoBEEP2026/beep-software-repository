import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from test_validate_review_document_creation import (
    TestReviewDocumentCreation,
)


EXPECTED_REJECTION = (
    "New technical review document "
    "has no authorized review completion transition"
)


def demonstrate_controlled_failure():
    """
    Demonstrate unauthorized technical review
    document creation rejection using an isolated
    temporary Git repository.
    """

    source_directory = (
        Path(__file__).resolve().parent
    )

    fixture = TestReviewDocumentCreation()

    fixture.setUp()

    try:

        print("=" * 60)
        print(
            "B.E.E.P. CONTROLLED DOCUMENT "
            "CREATION FAILURE DEMONSTRATION"
        )
        print("=" * 60)

        # Establish a legitimate historical
        # technical review assignment.

        fixture.create_baseline(
            status="IN_PROGRESS"
        )

        print(
            "STEP 1 PASSED: Historical review "
            "assignment established"
        )

        # Reset the review while retaining
        # its permanent identifier reservation.

        fixture.write_registries(
            fixture.make_home("NOT_STARTED"),
            [fixture.make_reservation()],
        )

        base_commit = (
            fixture.commit_repository()
        )

        print(
            "STEP 2 PASSED: Review abandoned "
            "and identifier permanently retained"
        )

        # Copy the existing validators into
        # the isolated temporary repository.

        temporary_test_homes = (
            fixture.root / "test-homes"
        )

        for source_file in (
            source_directory.glob("validate_*.py")
        ):

            shutil.copy2(
                source_file,
                temporary_test_homes
                / source_file.name,
            )

        validator = (
            temporary_test_homes
            / "validate_review_document_creation.py"
        )

        # Confirm that the abandoned review
        # without a supporting document is valid.

        baseline_result = subprocess.run(
            [
                sys.executable,
                str(validator),
                base_commit,
            ],
            cwd=fixture.root,
            capture_output=True,
            text=True,
            check=False,
        )

        if baseline_result.returncode != 0:

            print(baseline_result.stdout)
            print(baseline_result.stderr)

            raise RuntimeError(
                "Valid baseline unexpectedly failed"
            )

        print(
            "STEP 3 PASSED: Valid abandoned "
            "review baseline accepted"
        )

        # Introduce a technically formatted
        # supporting document for the abandoned
        # review identifier.

        unauthorized_document = (
            fixture.write_document()
        )

        print(
            "STEP 4 PASSED: Unauthorized "
            "supporting document introduced"
        )

        print()
        print(
            "Executing actual command-line validator..."
        )
        print()

        failure_result = subprocess.run(
            [
                sys.executable,
                str(validator),
                base_commit,
            ],
            cwd=fixture.root,
            capture_output=True,
            text=True,
            check=False,
        )

        print(failure_result.stdout)

        if failure_result.stderr:

            print(failure_result.stderr)

        print(
            "Actual validator exit code: "
            f"{failure_result.returncode}"
        )

        if failure_result.returncode != 1:

            raise RuntimeError(
                "Expected validator exit code 1"
            )

        if EXPECTED_REJECTION not in (
            failure_result.stdout
        ):

            raise RuntimeError(
                "Validator did not report the "
                "expected authorization rejection"
            )

        print(
            "STEP 5 PASSED: Unauthorized document "
            "rejected with correct exit code "
            "and rejection message"
        )

        # Remove the unauthorized document and
        # confirm that validation succeeds again.

        unauthorized_document.unlink()

        recovery_result = subprocess.run(
            [
                sys.executable,
                str(validator),
                base_commit,
            ],
            cwd=fixture.root,
            capture_output=True,
            text=True,
            check=False,
        )

        if recovery_result.returncode != 0:

            print(recovery_result.stdout)
            print(recovery_result.stderr)

            raise RuntimeError(
                "Validation failed after removal "
                "of unauthorized document"
            )

        print(
            "STEP 6 PASSED: Valid repository "
            "state restored"
        )

        print()
        print("=" * 60)
        print(
            "CONTROLLED FAILURE DEMONSTRATION PASSED"
        )
        print(
            "Unauthorized document creation: REJECTED"
        )
        print(
            "Expected failure exit code: 1"
        )
        print(
            "Actual failure exit code: 1"
        )
        print(
            "Recovery validation exit code: 0"
        )
        print(
            "Verified demonstration steps: 6/6"
        )
        print("=" * 60)

        return 0

    finally:

        fixture.doCleanups()


if __name__ == "__main__":

    try:

        sys.exit(
            demonstrate_controlled_failure()
        )

    except Exception as exc:

        print(
            "CONTROLLED FAILURE "
            "DEMONSTRATION FAILED"
        )

        print(f"ERROR: {exc}")

        sys.exit(1)
