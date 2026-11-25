import sys
from pathlib import Path

from validate_reference_audit import (
    AUDIT_DESCRIPTION,
    AUDIT_STATUS,
    CURRENT_SCHEMA_VERSION,
    LEGACY_SCHEMA_VERSION,
    REPOSITORY_NAME,
    REQUIRED_REGISTRY_FIELDS,
    load_audit_registry,
    validate_audit_data,
)


AUDIT_FILE = (
    Path(__file__).resolve().parent
    / "reference-approval-audit.json"
)


def validate_registry_metadata(audit):

    errors = []

    if not isinstance(audit, dict):

        return [
            "Audit registry must be a JSON object"
        ]

    missing_fields = (
        REQUIRED_REGISTRY_FIELDS - audit.keys()
    )

    unexpected_fields = (
        audit.keys() - REQUIRED_REGISTRY_FIELDS
    )

    for field in sorted(missing_fields):

        errors.append(
            f"Missing audit registry field: {field}"
        )

    for field in sorted(unexpected_fields):

        errors.append(
            f"Unexpected audit registry field: {field}"
        )

    if audit.get("repository") != REPOSITORY_NAME:

        errors.append(
            "Invalid audit repository name"
        )

    if audit.get("audit_status") != AUDIT_STATUS:

        errors.append(
            "Unsupported audit status"
        )

    if audit.get("description") != AUDIT_DESCRIPTION:

        errors.append(
            "Invalid audit registry description"
        )

    return errors


def validate_schema_transition(previous, current):

    errors = []

    previous_version = previous.get(
        "audit_schema_version"
    )

    current_version = current.get(
        "audit_schema_version"
    )

    if previous_version == current_version:

        return errors

    if (
        previous_version == LEGACY_SCHEMA_VERSION
        and current_version == CURRENT_SCHEMA_VERSION
    ):

        if previous.get("records") != []:

            errors.append(
                "Audit schema migration requires "
                "an empty historical audit registry"
            )

        if current.get("records") != []:

            errors.append(
                "Audit schema migration cannot "
                "introduce audit records"
            )

        return errors

    if (
        previous_version == CURRENT_SCHEMA_VERSION
        and current_version == LEGACY_SCHEMA_VERSION
    ):

        return [
            "Audit schema downgrade is prohibited"
        ]

    return [
        "Unauthorized audit schema transition: "
        f"{previous_version} to {current_version}"
    ]


def validate_preserved_metadata(previous, current):

    errors = []

    previous_metadata = {
        key: value
        for key, value in previous.items()
        if key not in {
            "records",
            "audit_schema_version",
        }
    }

    current_metadata = {
        key: value
        for key, value in current.items()
        if key not in {
            "records",
            "audit_schema_version",
        }
    }

    if previous_metadata != current_metadata:

        errors.append(
            "Historical audit registry metadata "
            "cannot be modified"
        )

    return errors


def validate_preserved_records(
    previous_records,
    current_records,
):

    errors = []

    if not isinstance(previous_records, list):

        return [
            "Previous audit records must be an array"
        ]

    if not isinstance(current_records, list):

        return [
            "Current audit records must be an array"
        ]

    if len(current_records) < len(previous_records):

        errors.append(
            "Audit history cannot remove existing records"
        )

    for index, previous_record in enumerate(
        previous_records
    ):

        if index >= len(current_records):

            break

        if previous_record != current_records[index]:

            errors.append(
                f"Audit record {index + 1} "
                "was modified or reordered"
            )

    return errors


def validate_append_only_data(previous, current):

    errors = []

    if (
        not isinstance(previous, dict)
        or not isinstance(current, dict)
    ):

        return [
            "Audit histories must be JSON objects"
        ]

    previous_errors = validate_audit_data(previous)

    current_errors = validate_audit_data(current)

    errors.extend(
        f"Historical audit: {error}"
        for error in previous_errors
    )

    errors.extend(
        f"Current audit: {error}"
        for error in current_errors
    )

    errors.extend(
        f"Historical audit: {error}"
        for error in validate_registry_metadata(
            previous
        )
    )

    errors.extend(
        f"Current audit: {error}"
        for error in validate_registry_metadata(
            current
        )
    )

    errors.extend(
        validate_schema_transition(
            previous,
            current,
        )
    )

    errors.extend(
        validate_preserved_metadata(
            previous,
            current,
        )
    )

    errors.extend(
        validate_preserved_records(
            previous.get("records"),
            current.get("records"),
        )
    )

    return errors


def validate_append_only(
    previous_path,
    current_path=AUDIT_FILE,
):

    """
    Verify that previously recorded audit decisions
    and registry metadata remain protected.

    Permit only explicitly authorized schema
    migrations.
    """

    try:

        previous_path = Path(previous_path)

        current_path = Path(current_path)

        if previous_path.is_symlink():

            return [
                "Historical audit file cannot "
                "be a symbolic link"
            ]

        if current_path.is_symlink():

            return [
                "Current audit file cannot "
                "be a symbolic link"
            ]

        previous = load_audit_registry(
            previous_path
        )

        current = load_audit_registry(
            current_path
        )

        return validate_append_only_data(
            previous,
            current,
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        RuntimeError,
    ) as exc:

        return [
            f"Unable to load audit history: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage: python validate_audit_append_only.py "
            "<previous-audit-file>"
        )

        sys.exit(2)

    validation_errors = validate_append_only(
        sys.argv[1]
    )

    if validation_errors:

        print(
            "APPEND-ONLY AUDIT VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "APPEND-ONLY AUDIT VALIDATION PASSED"
    )

    sys.exit(0)
