import json
import re
import sys
from datetime import date
from pathlib import Path


REGISTRY_FILE = (
    Path(__file__).resolve().parent
    / "reference-review-identifier-registry.json"
)

SCHEMA_VERSION = "1.0.0"

REGISTRY_NAME = (
    "B.E.E.P. Technical Review Identifier "
    "Reservation Registry"
)

GOVERNANCE_AUTHORITY = (
    "B.E.E.P. Board of Directors"
)

IDENTIFIER_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_-]*"
)

VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)"
)

EXPECTED_POLICY = {
    "uniqueness_scope": "REPOSITORY_WIDE",
    "reservation_trigger": "REVIEW_ASSIGNMENT",
    "reservation_duration": "PERMANENT",
    "identifier_reuse_allowed": False,
    "identifier_reassignment_allowed": False,
    "historical_modification_allowed": False,
    "historical_deletion_allowed": False,
    "append_only": True,
}

REQUIRED_RESERVATION_FIELDS = {
    "review_record_id",
    "reference_home_id",
    "reference_home_version",
    "assigned_reviewer",
    "assignment_date",
}


def is_valid_identifier(value):
    """
    Validate a technical review or reference
    home identifier.
    """

    return (
        isinstance(value, str)
        and IDENTIFIER_PATTERN.fullmatch(value)
        is not None
    )


def is_valid_version(value):
    """
    Validate a canonical semantic version.
    """

    return (
        isinstance(value, str)
        and VERSION_PATTERN.fullmatch(value)
        is not None
    )


def is_valid_assignment_date(value):
    """
    Validate a canonical ISO calendar date.
    """

    if not isinstance(value, str):
        return False

    try:
        parsed_date = date.fromisoformat(value)

    except ValueError:
        return False

    return parsed_date.isoformat() == value


def is_valid_reviewer(value):
    """
    Reject missing, empty, multiline, or
    placeholder reviewer names.
    """

    if not isinstance(value, str):
        return False

    if not value.strip():
        return False

    if value != value.strip():
        return False

    if len(value.splitlines()) != 1:
        return False

    if value.casefold() in {
        "pending",
        "required",
        "unknown",
        "none",
        "n/a",
        "tbd",
        "todo",
        "placeholder",
        "to be determined",
    }:
        return False

    if re.fullmatch(r"\[.*\]", value):
        return False

    return True


def reject_duplicate_json_keys(pairs):
    """
    Reject duplicate JSON object keys.
    """

    result = {}

    for key, value in pairs:

        if key in result:
            raise ValueError(
                f"Duplicate JSON key: {key}"
            )

        result[key] = value

    return result


def load_identifier_registry(registry_path):
    """
    Load the identifier reservation registry.
    """

    registry_path = Path(registry_path)

    return json.loads(
        registry_path.read_text(
            encoding="utf-8"
        ),
        object_pairs_hook=reject_duplicate_json_keys,
    )


def validate_reservation_policy(policy):
    """
    Enforce the permanent reservation policy.
    """

    if not isinstance(policy, dict):
        return [
            "Reservation policy must be an object"
        ]

    errors = []

    for field, expected in EXPECTED_POLICY.items():

        if field not in policy:

            errors.append(
                f"Missing reservation policy field: "
                f"{field}"
            )

            continue

        actual = policy[field]

        if (
            type(actual) is not type(expected)
            or actual != expected
        ):

            errors.append(
                f"Invalid reservation policy field: "
                f"{field}. Expected: {expected}"
            )

    unexpected_fields = (
        set(policy) - set(EXPECTED_POLICY)
    )

    for field in sorted(unexpected_fields):

        errors.append(
            f"Unexpected reservation policy field: "
            f"{field}"
        )

    return errors


def validate_reservation(reservation):
    """
    Validate an individual immutable identifier
    reservation record.
    """

    if not isinstance(reservation, dict):
        return [
            "Identifier reservation must be an object"
        ]

    errors = []

    missing_fields = (
        REQUIRED_RESERVATION_FIELDS
        - set(reservation)
    )

    unexpected_fields = (
        set(reservation)
        - REQUIRED_RESERVATION_FIELDS
    )

    for field in sorted(missing_fields):

        errors.append(
            f"Missing reservation field: {field}"
        )

    for field in sorted(unexpected_fields):

        errors.append(
            f"Unexpected reservation field: {field}"
        )

    if errors:
        return errors

    if not is_valid_identifier(
        reservation["review_record_id"]
    ):

        errors.append(
            "Invalid technical review record identifier"
        )

    if not is_valid_identifier(
        reservation["reference_home_id"]
    ):

        errors.append(
            "Invalid reference home identifier"
        )

    if not is_valid_version(
        reservation["reference_home_version"]
    ):

        errors.append(
            "Invalid reference home semantic version"
        )

    if not is_valid_reviewer(
        reservation["assigned_reviewer"]
    ):

        errors.append(
            "Invalid assigned reviewer"
        )

    if not is_valid_assignment_date(
        reservation["assignment_date"]
    ):

        errors.append(
            "Invalid review assignment date"
        )

    return errors


def validate_identifier_registry_data(registry):
    """
    Validate registry metadata, reservation
    policy, individual reservations, and
    repository-wide identifier uniqueness.
    """

    if not isinstance(registry, dict):
        return [
            "Identifier registry must be an object"
        ]

    errors = []

    expected_metadata = {
        "registry_schema_version": SCHEMA_VERSION,
        "registry_status": "DEVELOPMENT",
        "registry_name": REGISTRY_NAME,
        "governance_authority": GOVERNANCE_AUTHORITY,
    }

    allowed_fields = (
        set(expected_metadata)
        | {"reservation_policy", "reservations"}
    )

    for field in sorted(
        set(registry) - allowed_fields
    ):

        errors.append(
            f"Unexpected registry field: {field}"
        )

    for field, expected in (
        expected_metadata.items()
    ):

        if registry.get(field) != expected:

            errors.append(
                f"Invalid registry field: {field}. "
                f"Expected: {expected}"
            )

    errors.extend(
        validate_reservation_policy(
            registry.get("reservation_policy")
        )
    )

    reservations = registry.get("reservations")

    if not isinstance(reservations, list):

        errors.append(
            "Identifier reservations must be a list"
        )

        return errors

    seen_identifiers = set()

    for index, reservation in enumerate(
        reservations,
        start=1,
    ):

        reservation_errors = (
            validate_reservation(reservation)
        )

        for error in reservation_errors:

            errors.append(
                f"Reservation {index}: {error}"
            )

        if not isinstance(reservation, dict):
            continue

        record_id = reservation.get(
            "review_record_id"
        )

        if not is_valid_identifier(record_id):
            continue

        normalized_id = record_id.casefold()

        if normalized_id in seen_identifiers:

            errors.append(
                f"Duplicate technical review record "
                f"identifier: {record_id}"
            )

        else:

            seen_identifiers.add(normalized_id)

    return errors


def validate_review_identifiers(
    registry_path=None,
):
    """
    Load and validate the technical review
    identifier reservation registry.
    """

    if registry_path is None:
        registry_path = REGISTRY_FILE

    try:

        registry = load_identifier_registry(
            registry_path
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        RecursionError,
    ) as exc:

        return [
            f"Unable to load identifier "
            f"reservation registry: {exc}"
        ]

    return validate_identifier_registry_data(
        registry
    )


if __name__ == "__main__":

    if len(sys.argv) > 2:

        print(
            "Usage: python "
            "validate_review_identifiers.py "
            "[registry-path]"
        )

        sys.exit(2)

    registry_path = (
        sys.argv[1]
        if len(sys.argv) == 2
        else None
    )

    validation_errors = (
        validate_review_identifiers(
            registry_path
        )
    )

    if validation_errors:

        print(
            "TECHNICAL REVIEW IDENTIFIER "
            "REGISTRY VALIDATION FAILED"
        )

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "TECHNICAL REVIEW IDENTIFIER "
        "REGISTRY VALIDATION PASSED"
    )

    sys.exit(0)
