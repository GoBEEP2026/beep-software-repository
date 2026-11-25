import sys
from datetime import date
from pathlib import Path

from validate_reference_audit import (
    AUDIT_FILE,
    TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    load_audit_registry,
    validate_live_audit_data,
)

from validate_review_identifiers import (
    REGISTRY_FILE,
    load_identifier_registry,
    validate_identifier_registry_data,
)


AUDIT_RESERVATION_MATCHED_FIELDS = {
    "technical_review_record":
        "review_record_id",
    "reference_home_id":
        "reference_home_id",
    "reference_home_version":
        "reference_home_version",
    "reviewer":
        "assigned_reviewer",
}


def build_reservation_lookup(identifier_registry):
    """
    Build a case-insensitive lookup from a
    validated permanent reservation registry.

    Exact identifier capitalization is checked
    separately during audit evidence validation.
    """

    return {
        reservation["review_record_id"].casefold():
            reservation
        for reservation in
        identifier_registry["reservations"]
    }


def validate_audit_reservation_chronology(
    record,
    reservation,
):
    """
    Verify the chronological sequence of
    reservation assignment, technical review
    completion, and Board decision.

    Both records must already have passed their
    respective schema validators.
    """

    assignment_date = date.fromisoformat(
        reservation["assignment_date"]
    )

    review_date = date.fromisoformat(
        record["technical_review_date"]
    )

    decision_date = date.fromisoformat(
        record["decision_date"]
    )

    errors = []

    if review_date < assignment_date:

        errors.append(
            "Technical review completion date "
            "cannot precede reservation "
            "assignment date"
        )

    if decision_date < review_date:

        errors.append(
            "Audit decision date cannot precede "
            "technical review completion date"
        )

    if decision_date < assignment_date:

        errors.append(
            "Audit decision date cannot precede "
            "reservation assignment date"
        )

    return errors


def validate_audit_record_reservation(
    record,
    reservations_by_id,
):
    """
    Verify that a schema-validated audit record
    references its original permanent technical
    review identifier reservation.

    Historical reservations remain valid even
    when a reference home's current review
    assignment has changed.
    """

    if all(
        record[field] is None
        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS
    ):

        if record["decision"] == "REJECTED":

            return []

        return [
            "Complete technical review evidence "
            "is required"
        ]

    if any(
        record[field] is None
        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS
    ):

        return [
            "Partial technical review evidence "
            "is not permitted"
        ]

    record_id = record["technical_review_record"]

    reservation = reservations_by_id.get(
        record_id.casefold()
    )

    if reservation is None:

        return [
            "Missing permanent technical review "
            f"identifier reservation: {record_id}"
        ]

    errors = []

    for audit_field, reservation_field in (
        AUDIT_RESERVATION_MATCHED_FIELDS.items()
    ):

        if (
            record[audit_field]
            != reservation[reservation_field]
        ):

            errors.append(
                "Audit technical review reservation "
                f"mismatch: {audit_field}"
            )

    errors.extend(
        validate_audit_reservation_chronology(
            record,
            reservation,
        )
    )

    return errors


def validate_audit_review_reservations_data(
    audit,
    identifier_registry,
):
    """
    Validate both registries before performing
    cross-registry technical review reservation
    matching.
    """

    errors = []

    audit_errors = validate_live_audit_data(
        audit
    )

    errors.extend(
        f"Approval audit registry: {error}"
        for error in audit_errors
    )

    reservation_errors = (
        validate_identifier_registry_data(
            identifier_registry
        )
    )

    errors.extend(
        f"Identifier reservation registry: {error}"
        for error in reservation_errors
    )

    if errors:

        return errors

    reservations_by_id = (
        build_reservation_lookup(
            identifier_registry
        )
    )

    for index, record in enumerate(
        audit["records"],
        start=1,
    ):

        record_id = record["record_id"]

        record_errors = (
            validate_audit_record_reservation(
                record,
                reservations_by_id,
            )
        )

        errors.extend(
            f"Record {index} ({record_id}): {error}"
            for error in record_errors
        )

    return errors


def validate_audit_review_reservations(
    audit_path=None,
    identifier_registry_path=None,
):
    """
    Load and validate the live approval audit
    registry against the permanent technical
    review identifier reservation registry.
    """

    if audit_path is None:

        audit_path = AUDIT_FILE

    if identifier_registry_path is None:

        identifier_registry_path = REGISTRY_FILE

    try:

        audit_path = Path(audit_path)

        identifier_registry_path = Path(
            identifier_registry_path
        )

        if audit_path.is_symlink():

            return [
                "Audit registry cannot be "
                "a symbolic link"
            ]

        if identifier_registry_path.is_symlink():

            return [
                "Identifier reservation registry "
                "cannot be a symbolic link"
            ]

        audit = load_audit_registry(
            audit_path
        )

        identifier_registry = (
            load_identifier_registry(
                identifier_registry_path
            )
        )

        return validate_audit_review_reservations_data(
            audit,
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
            "Unable to validate audit technical "
            f"review reservations: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) not in {1, 3}:

        print(
            "Usage: python "
            "validate_audit_review_reservations.py "
            "[audit-path identifier-registry-path]"
        )

        sys.exit(2)

    audit_path = (
        sys.argv[1]
        if len(sys.argv) == 3
        else None
    )

    identifier_registry_path = (
        sys.argv[2]
        if len(sys.argv) == 3
        else None
    )

    validation_errors = (
        validate_audit_review_reservations(
            audit_path,
            identifier_registry_path,
        )
    )

    if validation_errors:

        print(
            "AUDIT TECHNICAL REVIEW RESERVATION "
            "VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "AUDIT TECHNICAL REVIEW RESERVATION "
        "VALIDATION PASSED"
    )

    sys.exit(0)
