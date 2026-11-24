import sys
from datetime import date
from pathlib import Path

from validate_review_identifiers import (
    REGISTRY_FILE,
    is_valid_identifier,
    is_valid_version,
    load_identifier_registry,
    validate_identifier_registry_data,
)

from validate_technical_review import (
    validate_review_fingerprint,
)

from validate_technical_review_registry import (
    load_review_registry,
)


REFERENCE_REGISTRY_FILE = (
    Path(__file__).resolve().parent
    / "reference-home-registry.json"
)


ACTIVE_REVIEW_STATUSES = {
    "IN_PROGRESS",
    "COMPLETED",
}


def validate_review_assignment(
    home,
    reservations_by_id,
):
    """
    Verify that an active or completed technical
    review has a matching permanent identifier
    reservation.
    """

    errors = []

    if not isinstance(home, dict):

        return [
            "Reference home must be a JSON object"
        ]

    home_id = home.get("test_home_id")
    version = home.get("test_home_version")

    prefix = f"{home_id}/{version}"

    if not is_valid_identifier(home_id):

        errors.append(
            f"{prefix}: Invalid reference home identifier"
        )

    if not is_valid_version(version):

        errors.append(
            f"{prefix}: Invalid reference home version"
        )

    if errors:
        return errors

    review_errors = validate_review_fingerprint(
        home
    )

    if review_errors:
        return review_errors

    review = home["review"]

    review_status = review["review_status"]

    if review_status not in ACTIVE_REVIEW_STATUSES:

        return []

    record_id = review["review_record"]

    reservation = reservations_by_id.get(
        record_id.casefold()
    )

    if reservation is None:

        return [
            f"{prefix}: Technical review identifier "
            f"has no permanent reservation: {record_id}"
        ]

    if reservation["review_record_id"] != record_id:

        errors.append(
            f"{prefix}: Technical review identifier "
            "capitalization does not match "
            "the permanent reservation"
        )

    if reservation["reference_home_id"] != home_id:

        errors.append(
            f"{prefix}: Reserved technical review "
            "identifier belongs to a different "
            "reference home"
        )

    if reservation["reference_home_version"] != version:

        errors.append(
            f"{prefix}: Reserved technical review "
            "identifier belongs to a different "
            "reference home version"
        )

    if reservation["assigned_reviewer"] != review["reviewer"]:

        errors.append(
            f"{prefix}: Technical reviewer does not "
            "match the permanent identifier reservation"
        )

    if review_status == "COMPLETED":

        assignment_date = date.fromisoformat(
            reservation["assignment_date"]
        )

        review_date = date.fromisoformat(
            review["review_date"]
        )

        if review_date < assignment_date:

            errors.append(
                f"{prefix}: Technical review completion "
                "date cannot precede the identifier "
                "assignment date"
            )

    return errors


def validate_assignment_consistency_data(
    homes,
    identifier_registry,
):
    """
    Validate the relationship between all reference
    home versions and permanent identifier reservations.
    """

    errors = []

    registry_errors = (
        validate_identifier_registry_data(
            identifier_registry
        )
    )

    if registry_errors:

        return [
            f"Identifier registry: {error}"
            for error in registry_errors
        ]

    if not isinstance(homes, dict):

        return [
            "Reference home lookup must be a dictionary"
        ]

    if not homes:

        return [
            "Reference home registry must contain "
            "at least one reference home"
        ]

    reservations_by_id = {
        reservation["review_record_id"].casefold():
        reservation
        for reservation in identifier_registry[
            "reservations"
        ]
    }

    # Every reservation must refer to a registered
    # reference home and version, even when its
    # original review has been abandoned.

    for reservation in identifier_registry[
        "reservations"
    ]:

        reservation_key = (
            reservation["reference_home_id"],
            reservation["reference_home_version"],
        )

        if reservation_key not in homes:

            errors.append(
                "Permanent identifier reservation "
                f"{reservation['review_record_id']} "
                "references an unregistered "
                "reference home version"
            )

    used_identifiers = {}

    for key, home in homes.items():

        if not isinstance(home, dict):

            errors.append(
                "Reference home lookup contains "
                "a malformed reference home"
            )

            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")

        if (
            not isinstance(home_id, str)
            or not isinstance(version, str)
            or key != (home_id, version)
        ):

            errors.append(
                "Reference home lookup identity "
                "does not match reference home data"
            )

            continue

        assignment_errors = (
            validate_review_assignment(
                home,
                reservations_by_id,
            )
        )

        errors.extend(assignment_errors)

        review = home.get("review")

        if not isinstance(review, dict):

            continue

        review_status = review.get(
            "review_status"
        )

        if (
            not isinstance(review_status, str)
            or review_status not in ACTIVE_REVIEW_STATUSES
        ):

            continue

        record_id = review.get(
            "review_record"
        )

        if not is_valid_identifier(record_id):

            continue

        normalized_id = record_id.casefold()

        if normalized_id in used_identifiers:

            previous_key = used_identifiers[
                normalized_id
            ]

            errors.append(
                f"{key[0]}/{key[1]}: Technical review "
                f"identifier {record_id} is already "
                "referenced by "
                f"{previous_key[0]}/{previous_key[1]}"
            )

        else:

            used_identifiers[
                normalized_id
            ] = key

    return errors


def validate_review_assignment_consistency(
    reference_registry_path=None,
    identifier_registry_path=None,
):
    """
    Load both registries and validate permanent
    technical review assignment consistency.
    """

    if reference_registry_path is None:

        reference_registry_path = (
            REFERENCE_REGISTRY_FILE
        )

    if identifier_registry_path is None:

        identifier_registry_path = (
            REGISTRY_FILE
        )

    try:

        homes, errors = load_review_registry(
            reference_registry_path,
            "Current",
        )

        if errors:
            return errors

        identifier_registry = (
            load_identifier_registry(
                identifier_registry_path
            )
        )

        return validate_assignment_consistency_data(
            homes,
            identifier_registry,
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
    ) as exc:

        return [
            "Unable to validate technical review "
            f"assignment consistency: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) == 1:

        validation_errors = (
            validate_review_assignment_consistency()
        )

    elif len(sys.argv) == 3:

        validation_errors = (
            validate_review_assignment_consistency(
                sys.argv[1],
                sys.argv[2],
            )
        )

    else:

        print(
            "Usage: python "
            "validate_review_assignment_consistency.py "
            "[<reference-registry> <identifier-registry>]"
        )

        sys.exit(2)

    if validation_errors:

        print(
            "TECHNICAL REVIEW ASSIGNMENT "
            "CONSISTENCY VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "TECHNICAL REVIEW ASSIGNMENT "
        "CONSISTENCY VALIDATION PASSED"
    )

    sys.exit(0)
