import copy
import subprocess
import sys
from pathlib import Path

import test_validate_audit_decision_history as fixtures


VALIDATOR = (
    Path(__file__).resolve().parent
    / "validate_audit_decision_history.py"
)


def run_validator(fixture, data):

    fixture.save_fixture(data)

    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            *[str(path) for path in fixture.paths],
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def require_success(result, description):

    if result.returncode != 0:

        raise RuntimeError(
            f"{description}: "
            f"Expected exit code 0, "
            f"received {result.returncode}\n"
            f"{result.stdout}\n"
            f"{result.stderr}"
        )

    if (
        "HISTORICAL AUDIT DECISION "
        "AUTHORIZATION VALIDATION PASSED"
        not in result.stdout
    ):

        raise RuntimeError(
            f"{description}: "
            "Missing expected success message"
        )


def require_failure(
    result,
    expected_message,
    description,
):

    print(result.stdout)

    print(
        "Actual validator exit code: "
        f"{result.returncode}"
    )

    if result.returncode != 1:

        raise RuntimeError(
            f"{description}: "
            f"Expected exit code 1, "
            f"received {result.returncode}"
        )

    if (
        "HISTORICAL AUDIT DECISION "
        "AUTHORIZATION VALIDATION FAILED"
        not in result.stdout
    ):

        raise RuntimeError(
            f"{description}: "
            "Missing expected failure message"
        )

    if expected_message not in result.stdout:

        raise RuntimeError(
            f"{description}: "
            "Expected rejection reason not found: "
            f"{expected_message}"
        )


def demonstrate():

    fixture = fixtures.TestAuditDecisionHistory()

    try:

        fixture.setUp()

        print("=" * 60)

        print(
            "B.E.E.P. CONTROLLED HISTORICAL "
            "AUDIT AUTHORIZATION FAILURE DEMONSTRATION"
        )

        print("=" * 60)

        verified_steps = 0

        # STEP 1
        # Establish valid historical approval.

        approval = fixture.make_approval_fixture()

        result = run_validator(
            fixture,
            approval,
        )

        require_success(
            result,
            "Valid historical approval",
        )

        verified_steps += 1

        print(
            "STEP 1 PASSED: "
            "Valid historical approval accepted"
        )

        # STEP 2
        # Attempt approval without prior completed review.

        invalid_approval = copy.deepcopy(
            approval
        )

        invalid_approval[0]["reference_homes"] = [
            fixture.make_home("UNDER_REVIEW")
        ]

        result = run_validator(
            fixture,
            invalid_approval,
        )

        require_failure(
            result,
            "previously accepted COMPLETED "
            "technical review",
            "Unauthorized historical approval",
        )

        verified_steps += 1

        print(
            "STEP 2 PASSED: "
            "Approval without previously accepted "
            "completed review rejected"
        )

        # STEP 3
        # Restore valid historical approval.

        result = run_validator(
            fixture,
            approval,
        )

        require_success(
            result,
            "Approval recovery",
        )

        verified_steps += 1

        print(
            "STEP 3 PASSED: "
            "Valid approval state restored"
        )

        # STEP 4
        # Establish valid controlled rejection.

        rejection = fixture.make_rejection_fixture(
            complete=True,
            reset=True,
        )

        result = run_validator(
            fixture,
            rejection,
        )

        require_success(
            result,
            "Valid controlled rejection",
        )

        verified_steps += 1

        print(
            "STEP 4 PASSED: "
            "Valid controlled rejection accepted"
        )

        # STEP 5
        # Attempt rejection without preserving
        # previously accepted completed review evidence.

        invalid_rejection = copy.deepcopy(
            rejection
        )

        record = invalid_rejection[3]["records"][0]

        for field in (
            fixtures.TECHNICAL_REVIEW_EVIDENCE_FIELDS
        ):

            record[field] = None

        result = run_validator(
            fixture,
            invalid_rejection,
        )

        require_failure(
            result,
            "REJECTED decision must preserve "
            "previously accepted completed "
            "technical review evidence",
            "Unauthorized controlled rejection",
        )

        verified_steps += 1

        print(
            "STEP 5 PASSED: "
            "Rejection without required historical "
            "review evidence rejected"
        )

        # STEP 6
        # Restore valid controlled rejection.

        result = run_validator(
            fixture,
            rejection,
        )

        require_success(
            result,
            "Controlled rejection recovery",
        )

        verified_steps += 1

        print(
            "STEP 6 PASSED: "
            "Valid controlled rejection restored"
        )

        # STEP 7
        # Establish valid historical retirement.

        retirement = (
            fixture.make_retirement_fixture()
        )

        result = run_validator(
            fixture,
            retirement,
        )

        require_success(
            result,
            "Valid historical retirement",
        )

        verified_steps += 1

        print(
            "STEP 7 PASSED: "
            "Valid historical retirement accepted"
        )

        # STEP 8
        # Attempt retirement without previously
        # accepted original approval.

        invalid_retirement = copy.deepcopy(
            retirement
        )

        invalid_retirement[0]["reference_homes"] = [
            fixture.make_completed_review()
        ]

        invalid_retirement[2]["records"] = []

        result = run_validator(
            fixture,
            invalid_retirement,
        )

        require_failure(
            result,
            "Unauthorized RETIRED audit decision",
            "Unauthorized historical retirement",
        )

        verified_steps += 1

        print(
            "STEP 8 PASSED: "
            "Retirement without previously "
            "accepted approval rejected"
        )

        # STEP 9
        # Restore valid historical retirement.

        result = run_validator(
            fixture,
            retirement,
        )

        require_success(
            result,
            "Retirement recovery",
        )

        verified_steps += 1

        print(
            "STEP 9 PASSED: "
            "Valid retirement state restored"
        )

        if verified_steps != 9:

            raise RuntimeError(
                "Unexpected demonstration step count"
            )

        print()

        print("=" * 60)

        print(
            "CONTROLLED HISTORICAL AUDIT "
            "FAILURE DEMONSTRATION PASSED"
        )

        print("Unauthorized approval: REJECTED")

        print("Unauthorized rejection: REJECTED")

        print("Unauthorized retirement: REJECTED")

        print("Expected failure exit code: 1")

        print("All failure exit codes verified: 1")

        print("All recovery exit codes verified: 0")

        print(
            f"Verified demonstration steps: "
            f"{verified_steps}/9"
        )

        print("=" * 60)

    finally:

        fixture.doCleanups()


if __name__ == "__main__":

    try:

        demonstrate()

    except Exception as exc:

        print(
            "CONTROLLED HISTORICAL AUDIT "
            "FAILURE DEMONSTRATION FAILED"
        )

        print(f"ERROR: {exc}")

        sys.exit(1)

    sys.exit(0)
