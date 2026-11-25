
"""
B.E.E.P. Controlled Production Governance Demonstrations.

All fictional production evidence is created in temporary
directories. Authoritative repository records are not modified.

Successful demonstrations do not establish actual reference
home approval or vendor software certification.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

from pathlib import Path

from governance_test_fixture import (
    create_governance_fixture,
)

from validate_submission import (
    REQUIRED_FILES,
    validate_submission,
)


FOLDER = Path(__file__).resolve().parent

EXPECTED_DEMONSTRATIONS = 9

PARTIAL_INPUT_ERROR = (
    "Production governance requires either "
    "all four explicit governance paths "
    "or all authoritative repository defaults"
)


def require(condition, message):

    if not condition:
        raise RuntimeError(message)


def read_json(path):

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def write_json(path, data):

    path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )


def prepare_submission(directory):

    directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    for filename in REQUIRED_FILES:

        shutil.copy2(
            FOLDER / filename,
            directory / filename,
        )


def prepare_production_submission(directory):

    submission_path = (
        directory / "submission.json"
    )

    submission = read_json(submission_path)

    submission["software"]["engine_version"] = (
        "1.0.0"
    )

    write_json(
        submission_path,
        submission,
    )

    results_path = directory / "results.json"

    results = read_json(results_path)

    results["calculation_status"] = "COMPLETED"

    write_json(
        results_path,
        results,
    )

    manifest_path = directory / "manifest.json"

    manifest = read_json(manifest_path)

    for entry in manifest["files"]:

        filename = entry["filename"]

        require(
            filename in REQUIRED_FILES
            and filename != "manifest.json",
            f"Unexpected manifest filename: {filename}",
        )

        entry["sha256"] = hashlib.sha256(
            (directory / filename).read_bytes()
        ).hexdigest()

    manifest["manifest_status"] = (
        "CHECKSUMS_GENERATED"
    )

    write_json(
        manifest_path,
        manifest,
    )


def run_cli(directory, production=False):

    command = [
        sys.executable,
        str(FOLDER / "validate_submission.py"),
        str(directory),
    ]

    if production:
        command.append("--production")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    output = (
        result.stdout
        + "\n"
        + result.stderr
    )

    print(output)

    return result.returncode, output


def require_acceptance(errors):

    require(
        errors == [],
        f"Unexpected validation errors: {errors}",
    )


def require_rejection(errors, expected_control):

    require(
        bool(errors),
        "Invalid production evidence was accepted",
    )

    require(
        any(
            error.startswith(expected_control)
            for error in errors
        ),
        (
            f"Expected control: {expected_control}\n"
            f"Actual errors: {errors}"
        ),
    )

    for error in errors:
        print(f"  EXPECTED ERROR: {error}")


def demonstrate():

    passed = 0

    print(
        "B.E.E.P. CONTROLLED PRODUCTION "
        "GOVERNANCE DEMONSTRATIONS"
    )

    print(
        "FICTIONAL TEST EVIDENCE ONLY"
    )

    with tempfile.TemporaryDirectory(
        prefix="beep-production-demo-"
    ) as temporary_directory:

        root = Path(temporary_directory)

        submission_directory = (
            root / "submission"
        )

        prepare_submission(
            submission_directory
        )

        # Demonstration 1:
        # Development CLI acceptance.

        returncode, output = run_cli(
            submission_directory
        )

        require(
            returncode == 0,
            "Development CLI validation failed",
        )

        require(
            "B.E.E.P. SUBMISSION VALIDATION PASSED"
            in output
            and "Validation mode: DEVELOPMENT"
            in output
            and "Production governance controls not evaluated."
            in output,
            "Incorrect development CLI reporting",
        )

        passed += 1

        print(
            "PASS 1: Development sample accepted"
        )

        # Demonstration 2:
        # Production CLI rejection.

        returncode, output = run_cli(
            submission_directory,
            production=True,
        )

        require(
            returncode == 1,
            "Unexpected production CLI exit code",
        )

        require(
            "B.E.E.P. SUBMISSION VALIDATION FAILED"
            in output
            and "COMPLETED calculation status"
            in output
            and "Traceback" not in output
            and "B.E.E.P. SUBMISSION VALIDATION PASSED"
            not in output,
            "Incorrect production rejection reporting",
        )

        passed += 1

        print(
            "PASS 2: Development sample rejected "
            "in production mode"
        )

        # Prepare complete fictional production evidence.

        prepare_production_submission(
            submission_directory
        )

        fixture = create_governance_fixture(
            root / "governance"
        )

        governance_inputs = {
            "registry_path": fixture[
                "registry_path"
            ],
            "audit_path": fixture[
                "audit_path"
            ],
            "identifier_registry_path": fixture[
                "identifier_registry_path"
            ],
            "approvals_directory": fixture[
                "approvals_directory"
            ],
        }

        def validate():

            return validate_submission(
                submission_directory,
                production=True,
                **governance_inputs,
            )

        # Demonstration 3:
        # Valid fictional production acceptance.

        require_acceptance(validate())

        passed += 1

        print(
            "PASS 3: Complete fictional production "
            "submission accepted"
        )

        # Demonstration 4:
        # Modified reference home file.

        registry = read_json(
            fixture["registry_path"]
        )

        reference_filename = registry[
            "reference_homes"
        ][0]["reference_files"][0]["filename"]

        require(
            Path(reference_filename).name
            == reference_filename
            and reference_filename not in (".", ".."),
            "Unsafe reference filename",
        )

        reference_path = (
            fixture["registry_path"].parent
            / reference_filename
        )

        original_reference = (
            reference_path.read_bytes()
        )

        try:

            reference_path.write_bytes(
                original_reference
                + b"\n<!-- CONTROLLED MODIFICATION -->\n"
            )

            require_rejection(
                validate(),
                "Reference file integrity:",
            )

        finally:

            reference_path.write_bytes(
                original_reference
            )

        require_acceptance(validate())

        passed += 1

        print(
            "PASS 4: Modified reference file rejected"
        )

        # Demonstration 5:
        # Missing Board approval document.

        approval_path = fixture[
            "approval_document"
        ]

        original_approval = (
            approval_path.read_bytes()
        )

        try:

            approval_path.unlink()

            errors = validate()

            require_rejection(
                errors,
                "Board authorization:",
            )

            require(
                any(
                    error.startswith(
                        "Approval supporting records:"
                    )
                    for error in errors
                ),
                "Missing supporting-record rejection",
            )

        finally:

            approval_path.write_bytes(
                original_approval
            )

        require_acceptance(validate())

        passed += 1

        print(
            "PASS 5: Missing Board approval rejected"
        )

        # Demonstration 6:
        # Modified technical review evidence.

        review_path = fixture[
            "review_document"
        ]

        original_review = (
            review_path.read_bytes()
        )

        try:

            review_path.write_bytes(
                original_review
                + b"\nCONTROLLED EVIDENCE MODIFICATION\n"
            )

            require_rejection(
                validate(),
                "Audit review evidence:",
            )

        finally:

            review_path.write_bytes(
                original_review
            )

        require_acceptance(validate())

        passed += 1

        print(
            "PASS 6: Modified technical review "
            "evidence rejected"
        )

        # Demonstration 7:
        # Missing identifier reservation.

        identifier_path = fixture[
            "identifier_registry_path"
        ]

        original_identifiers = (
            identifier_path.read_bytes()
        )

        try:

            identifiers = read_json(
                identifier_path
            )

            identifiers["reservations"] = []

            write_json(
                identifier_path,
                identifiers,
            )

            require_rejection(
                validate(),
                "Review assignment consistency:",
            )

        finally:

            identifier_path.write_bytes(
                original_identifiers
            )

        require_acceptance(validate())

        passed += 1

        print(
            "PASS 7: Missing identifier "
            "reservation rejected"
        )

        # Demonstration 8:
        # Incomplete governance configuration.

        errors = validate_submission(
            submission_directory,
            production=True,
            registry_path=fixture[
                "registry_path"
            ],
        )

        require(
            errors == [PARTIAL_INPUT_ERROR],
            (
                "Incomplete governance configuration "
                f"not correctly rejected: {errors}"
            ),
        )

        passed += 1

        print(
            "PASS 8: Incomplete governance "
            "configuration rejected"
        )

        # Demonstration 9:
        # Restored valid production evidence.

        require_acceptance(validate())

        passed += 1

        print(
            "PASS 9: Restored production "
            "evidence accepted"
        )

    require(
        passed == EXPECTED_DEMONSTRATIONS,
        (
            "Incorrect demonstration count: "
            f"{passed}/{EXPECTED_DEMONSTRATIONS}"
        ),
    )

    print()

    print(
        "ALL CONTROLLED PRODUCTION GOVERNANCE "
        "DEMONSTRATIONS PASSED"
    )

    print(
        f"Verified demonstrations: "
        f"{passed}/{EXPECTED_DEMONSTRATIONS}"
    )

    print(
        "Temporary fictional evidence removed."
    )

    print(
        "No actual reference home approval "
        "or software certification established."
    )


if __name__ == "__main__":

    try:

        demonstrate()

    except Exception as exc:

        print(
            "CONTROLLED PRODUCTION GOVERNANCE "
            "DEMONSTRATIONS FAILED"
        )

        print(
            f"ERROR: {type(exc).__name__}: {exc}"
        )

        sys.exit(1)

    sys.exit(0)
