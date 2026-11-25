import json
import sys
from pathlib import Path

from validate_reference_integrity import (
    validate_reference_integrity,
)

from validate_reference_approval import (
    validate_reference_approval,
)

from validate_approval_records import (
    validate_approval_records,
)

from validate_board_authorization import (
    validate_board_authorization,
)

from validate_reference_audit import (
    validate_audit,
)

from validate_technical_review_registry import (
    validate_current_review_registry,
)

from validate_technical_review_records import (
    validate_technical_review_records,
)

from validate_review_approval_chronology import (
    validate_registry_approval_chronology,
)

from validate_review_identifiers import (
    validate_review_identifiers,
    is_valid_identifier,
    is_valid_version,
)

from validate_review_assignment_consistency import (
    validate_review_assignment_consistency,
)

from validate_review_document_reservations import (
    validate_review_document_reservations,
)

from validate_audit_review_evidence import (
    validate_audit_review_evidence,
)

from validate_audit_review_reservations import (
    validate_audit_review_reservations,
)

from validate_approval_audit_consistency import (
    validate_approval_audit_consistency,
)

from validate_retirement_audit_consistency import (
    validate_retirement_audit_consistency,
)


TEST_HOMES_DIRECTORY = (
    Path(__file__).resolve().parent
)

REPOSITORY_ROOT = (
    TEST_HOMES_DIRECTORY.parent
)

REFERENCE_REGISTRY_FILE = (
    TEST_HOMES_DIRECTORY
    / "reference-home-registry.json"
)

AUDIT_REGISTRY_FILE = (
    TEST_HOMES_DIRECTORY
    / "reference-approval-audit.json"
)

IDENTIFIER_REGISTRY_FILE = (
    TEST_HOMES_DIRECTORY
    / "reference-review-identifier-registry.json"
)

APPROVALS_DIRECTORY = (
    REPOSITORY_ROOT / "approvals"
)


def reject_duplicate_json_keys(pairs):
    """Reject ambiguous JSON object keys."""

    result = {}

    for key, value in pairs:

        if key in result:
            raise ValueError(
                f"Duplicate JSON key: {key}"
            )

        result[key] = value

    return result


def validate_safe_path(
    path,
    directory=False,
):
    """Reject missing paths and symbolic links."""

    path = Path(path).absolute()

    for candidate in (
        path,
        *path.parents,
    ):

        if candidate.is_symlink():
            raise ValueError(
                f"Symbolic links are prohibited: "
                f"{candidate}"
            )

    if directory:

        if not path.is_dir():
            raise ValueError(
                f"Missing governance directory: "
                f"{path}"
            )

    elif not path.is_file():

        raise ValueError(
            f"Missing governance file: {path}"
        )

    return path.resolve()


def load_governance_json(path):
    """Read governance JSON without duplicate keys."""

    data = json.loads(
        Path(path).read_text(
            encoding="utf-8"
        ),
        object_pairs_hook=(
            reject_duplicate_json_keys
        ),
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Governance JSON must be an object: "
            f"{path}"
        )

    return data


def run_governance_check(
    label,
    validator,
    *args,
    **kwargs,
):
    """
    Execute an existing governance validator.

    Unexpected validation exceptions must never
    result in production acceptance.
    """

    try:

        errors = validator(
            *args,
            **kwargs,
        )

        if (
            not isinstance(errors, list)
            or any(
                not isinstance(error, str)
                for error in errors
            )
        ):
            return [
                f"{label}: Invalid validator "
                "response"
            ]

        return [
            f"{label}: {error}"
            for error in errors
        ]

    except Exception as exc:

        return [
            f"{label}: Validation could not "
            f"complete ({type(exc).__name__}): "
            f"{exc}"
        ]


def validate_governance_board_records(
    registry,
    approvals_directory,
):
    """
    Validate Board authorization documents for
    all APPROVED and RETIRED reference homes.
    """

    errors = []

    homes = registry.get(
        "reference_homes"
    )

    if not isinstance(homes, list) or not homes:
        return [
            "Reference registry must contain "
            "at least one reference home"
        ]

    for home in homes:

        if not isinstance(home, dict):
            errors.append(
                "Malformed reference home"
            )
            continue

        home_id = home.get(
            "test_home_id"
        )

        version = home.get(
            "test_home_version"
        )

        if (
            not is_valid_identifier(home_id)
            or not is_valid_version(version)
        ):
            errors.append(
                "Invalid reference home identity"
            )
            continue

        if home.get("status") not in (
            "APPROVED",
            "RETIRED",
        ):
            continue

        prefix = f"{home_id}/{version}"

        record_path = (
            approvals_directory
            / home_id
            / version
            / "approval-record.md"
        )

        try:

            record_path = validate_safe_path(
                record_path
            )

            if not record_path.is_relative_to(
                approvals_directory
            ):
                raise ValueError(
                    "Approval document is outside "
                    "the trusted approvals directory"
                )

        except (
            OSError,
            ValueError,
            RuntimeError,
        ) as exc:

            errors.append(
                f"{prefix}: {exc}"
            )
            continue

        errors.extend(
            run_governance_check(
                prefix,
                validate_board_authorization,
                record_path,
            )
        )

    return errors


def validate_production_governance(
    registry_path=None,
    audit_path=None,
    identifier_registry_path=None,
    approvals_directory=None,
):
    
    # Require a complete and consistent set of
    # governance inputs before assigning defaults.

    governance_inputs = (
        registry_path,
        audit_path,
        identifier_registry_path,
        approvals_directory,
    )

    if (
        any(path is not None for path in governance_inputs)
        and not all(
            path is not None for path in governance_inputs
        )
    ):
        return [
            "Production governance requires either "
            "all four explicit governance paths "
            "or all authoritative repository defaults"
        ]

    """
    Coordinate current-state governance controls.

    Default paths refer to authoritative repository
    governance files.

    Explicit path overrides are intended for
    trusted internal testing and administration.

    Vendor-controlled files must never determine
    these paths.

    This function performs read-only validation.
    """

    if registry_path is None:
        registry_path = REFERENCE_REGISTRY_FILE

    if audit_path is None:
        audit_path = AUDIT_REGISTRY_FILE

    if identifier_registry_path is None:
        identifier_registry_path = (
            IDENTIFIER_REGISTRY_FILE
        )

    if approvals_directory is None:
        approvals_directory = (
            APPROVALS_DIRECTORY
        )

    # Establish safe governance inputs before
    # executing the existing validators.

    try:

        registry_path = validate_safe_path(
            registry_path
        )

        audit_path = validate_safe_path(
            audit_path
        )

        identifier_registry_path = (
            validate_safe_path(
                identifier_registry_path
            )
        )

        approvals_directory = (
            validate_safe_path(
                approvals_directory,
                directory=True,
            )
        )

        registry = load_governance_json(
            registry_path
        )

        load_governance_json(
            audit_path
        )

        load_governance_json(
            identifier_registry_path
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        RuntimeError,
    ) as exc:

        return [
            f"Governance input validation: {exc}"
        ]

    errors = []

    # 1. Actual reference file integrity.

    errors.extend(
        run_governance_check(
            "Reference file integrity",
            validate_reference_integrity,
            registry_path,
        )
    )

    # 2. Reference approval metadata.

    errors.extend(
        run_governance_check(
            "Reference approval metadata",
            validate_reference_approval,
            registry_path=registry_path,
            audit_path=audit_path,
        )
    )

    # 3. Version-specific approval records.

    errors.extend(
        run_governance_check(
            "Approval supporting records",
            validate_approval_records,
            registry_path=registry_path,
            approvals_directory=(
                approvals_directory
            ),
        )
    )

    # 4. Board authorization.

    errors.extend(
        run_governance_check(
            "Board authorization",
            validate_governance_board_records,
            registry,
            approvals_directory,
        )
    )

    # 5. Current approval audit registry.

    errors.extend(
        run_governance_check(
            "Reference approval audit",
            validate_audit,
            audit_path,
        )
    )

    # 6. Current technical review registry.

    errors.extend(
        run_governance_check(
            "Technical review registry",
            validate_current_review_registry,
            registry_path,
        )
    )

    # 7. Technical review supporting documents.

    errors.extend(
        run_governance_check(
            "Technical review supporting records",
            validate_technical_review_records,
            registry_path,
            approvals_directory,
        )
    )

    # 8. Review and approval chronology.

    errors.extend(
        run_governance_check(
            "Review and approval chronology",
            validate_registry_approval_chronology,
            registry_path,
        )
    )

    # 9. Permanent identifier reservations.

    errors.extend(
        run_governance_check(
            "Review identifier reservations",
            validate_review_identifiers,
            identifier_registry_path,
        )
    )

    # 10. Reviewer assignment consistency.

    errors.extend(
        run_governance_check(
            "Review assignment consistency",
            validate_review_assignment_consistency,
            registry_path,
            identifier_registry_path,
        )
    )

    # 11. Supporting document reservations.

    errors.extend(
        run_governance_check(
            "Review document reservations",
            validate_review_document_reservations,
            identifier_registry_path,
            approvals_directory,
        )
    )

    # 12. Audit technical review evidence.

    errors.extend(
        run_governance_check(
            "Audit review evidence",
            validate_audit_review_evidence,
            audit_path,
            approvals_directory,
        )
    )

    # 13. Audit identifier reservations.

    errors.extend(
        run_governance_check(
            "Audit review reservations",
            validate_audit_review_reservations,
            audit_path,
            identifier_registry_path,
        )
    )

    # 14. Bidirectional approval consistency.

    errors.extend(
        run_governance_check(
            "Approval audit consistency",
            validate_approval_audit_consistency,
            registry_path,
            audit_path,
        )
    )

    # 15. Retirement audit consistency.

    errors.extend(
        run_governance_check(
            "Retirement audit consistency",
            validate_retirement_audit_consistency,
            registry_path,
            audit_path,
        )
    )

    return errors


if __name__ == "__main__":

    # Command-line execution uses authoritative
    # repository paths only.

    if len(sys.argv) != 1:

        print(
            "Usage: python "
            "validate_production_governance.py"
        )

        sys.exit(2)

    validation_errors = (
        validate_production_governance()
    )

    if validation_errors:

        print(
            "PRODUCTION GOVERNANCE "
            "VALIDATION FAILED"
        )

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "PRODUCTION GOVERNANCE "
        "VALIDATION PASSED"
    )

    print(
        "All 15 current-state governance "
        "controls passed."
    )

    sys.exit(0)
