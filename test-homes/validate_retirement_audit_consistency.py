import sys
from datetime import date
from pathlib import Path

from validate_reference_audit import (
    AUDIT_FILE,
    GOVERNANCE_AUTHORITY,
    load_audit_registry,
)

from validate_approval_audit_consistency import (
    REFERENCE_REGISTRY_FILE,
    build_reference_home_lookup,
    validate_approval_audit_consistency_data,
)


PRESERVED_REVIEW_FIELDS = (
    "reviewer",
    "technical_review_record",
    "technical_review_date",
    "technical_review_sha256",
    "reviewed_content_sha256",
)


def build_lifecycle_audit_lookup(audit):
    """
    Group original approval and retirement
    decisions by reference home and version.

    Preserve each decision's position in the
    append-only audit registry.
    """

    lookup = {}

    for index, record in enumerate(
        audit["records"]
    ):

        decision = record["decision"]

        if decision not in (
            "APPROVED",
            "RETIRED",
        ):

            continue

        key = (
            record["reference_home_id"],
            record["reference_home_version"],
        )

        decisions = lookup.setdefault(
            key,
            {
                "APPROVED": [],
                "RETIRED": [],
            },
        )

        decisions[decision].append(
            (index, record)
        )

    return lookup


def validate_retirement_chronology(
    approval_entry,
    retirement_entry,
):
    """
    Require retirement to follow the original
    approval in both date and audit ordering.

    Same-day decisions are permitted when
    the approval appears first.
    """

    errors = []

    approval_index, approval = approval_entry

    retirement_index, retirement = retirement_entry

    approval_date = date.fromisoformat(
        approval["decision_date"]
    )

    retirement_date = date.fromisoformat(
        retirement["decision_date"]
    )

    if retirement_date < approval_date:

        errors.append(
            "Retirement decision date cannot "
            "precede original approval date"
        )

    if retirement_index <= approval_index:

        errors.append(
            "Retirement audit decision must "
            "appear after the original "
            "APPROVED audit decision"
        )

    return errors


def validate_retirement_evidence(
    approval,
    retirement,
):
    """
    Preserve original technical review evidence
    while requiring an independent retirement
    decision under B.E.E.P. Board authority.
    """

    errors = []

    if (
        retirement["approval_authority"]
        != GOVERNANCE_AUTHORITY
    ):

        errors.append(
            "Invalid retirement approval authority"
        )

    if (
        retirement["record_id"].casefold()
        == approval["record_id"].casefold()
    ):

        errors.append(
            "Retirement requires an independent "
            "audit record identifier"
        )

    if (
        retirement[
            "board_resolution_reference"
        ].strip().casefold()
        == approval[
            "board_resolution_reference"
        ].strip().casefold()
    ):

        errors.append(
            "Retirement requires an independent "
            "Board resolution reference"
        )

    for field in PRESERVED_REVIEW_FIELDS:

        if retirement[field] != approval[field]:

            errors.append(
                "Retirement technical review "
                f"evidence mismatch: {field}"
            )

    return errors


def validate_retired_home(
    home,
    decisions,
):
    """
    Require exactly one original approval
    and exactly one retirement decision
    for a retired reference home version.
    """

    errors = []

    approvals = decisions.get(
        "APPROVED",
        [],
    )

    retirements = decisions.get(
        "RETIRED",
        [],
    )

    if not approvals:

        errors.append(
            "Retired reference home is missing "
            "its original APPROVED audit decision"
        )

    elif len(approvals) != 1:

        errors.append(
            "Retired reference home has multiple "
            "original APPROVED audit decisions"
        )

    if not retirements:

        errors.append(
            "Missing RETIRED audit decision"
        )

    elif len(retirements) != 1:

        errors.append(
            "Multiple RETIRED audit decisions "
            "for the same reference home version"
        )

    if errors:

        return errors

    approval_entry = approvals[0]

    retirement_entry = retirements[0]

    errors.extend(
        validate_retirement_chronology(
            approval_entry,
            retirement_entry,
        )
    )

    errors.extend(
        validate_retirement_evidence(
            approval_entry[1],
            retirement_entry[1],
        )
    )

    return errors


def validate_home_to_retirement_audit(
    homes_by_key,
    lifecycle_audits_by_key,
):
    """
    Forward validation.

    Every RETIRED reference home must have
    exactly one valid retirement decision.
    """

    errors = []

    for key, home in homes_by_key.items():

        if home["status"] != "RETIRED":

            continue

        home_id, version = key

        prefix = f"{home_id}/{version}"

        decisions = lifecycle_audits_by_key.get(
            key,
            {},
        )

        retirement_errors = validate_retired_home(
            home,
            decisions,
        )

        errors.extend(
            f"{prefix}: {error}"
            for error in retirement_errors
        )

    return errors


def validate_retirement_audit_to_home(
    homes_by_key,
    lifecycle_audits_by_key,
):
    """
    Reverse validation.

    Every RETIRED audit decision must
    reference an existing RETIRED home.
    """

    errors = []

    for key, decisions in (
        lifecycle_audits_by_key.items()
    ):

        retirements = decisions["RETIRED"]

        if not retirements:

            continue

        home_id, version = key

        prefix = f"{home_id}/{version}"

        home = homes_by_key.get(key)

        if home is None:

            for index, record in retirements:

                errors.append(
                    f"{prefix}: RETIRED audit "
                    f"record {record['record_id']} "
                    "references an unregistered "
                    "reference home version"
                )

            continue

        if home["status"] != "RETIRED":

            for index, record in retirements:

                errors.append(
                    f"{prefix}: RETIRED audit "
                    f"record {record['record_id']} "
                    "references an ineligible "
                    "reference home status: "
                    f"{home['status']}"
                )

    return errors


def validate_retirement_audit_consistency_data(
    registry,
    audit,
):
    """
    Validate retirement consistency in both
    directions while preserving the original
    approval relationship.

    Existing approval and audit schema
    validation must succeed first.
    """

    approval_errors = (
        validate_approval_audit_consistency_data(
            registry,
            audit,
        )
    )

    if approval_errors:

        return [
            f"Original approval consistency: {error}"
            for error in approval_errors
        ]

    homes_by_key, registry_errors = (
        build_reference_home_lookup(
            registry
        )
    )

    if registry_errors:

        return registry_errors

    lifecycle_audits_by_key = (
        build_lifecycle_audit_lookup(
            audit
        )
    )

    errors = []

    errors.extend(
        validate_home_to_retirement_audit(
            homes_by_key,
            lifecycle_audits_by_key,
        )
    )

    errors.extend(
        validate_retirement_audit_to_home(
            homes_by_key,
            lifecycle_audits_by_key,
        )
    )

    return errors


def validate_retirement_audit_consistency(
    registry_path=None,
    audit_path=None,
):
    """
    Load and validate retirement decisions.

    Duplicate JSON keys and direct registry
    file symbolic links are prohibited.
    """

    if registry_path is None:

        registry_path = REFERENCE_REGISTRY_FILE

    if audit_path is None:

        audit_path = AUDIT_FILE

    try:

        registry_path = Path(registry_path)

        audit_path = Path(audit_path)

        if registry_path.is_symlink():

            return [
                "Reference home registry "
                "cannot be a symbolic link"
            ]

        if audit_path.is_symlink():

            return [
                "Audit registry cannot be "
                "a symbolic link"
            ]

        registry = load_audit_registry(
            registry_path
        )

        audit = load_audit_registry(
            audit_path
        )

        return (
            validate_retirement_audit_consistency_data(
                registry,
                audit,
            )
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
            "Unable to validate retirement "
            f"audit consistency: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) not in {1, 3}:

        print(
            "Usage: python "
            "validate_retirement_audit_consistency.py "
            "[reference-registry-path audit-path]"
        )

        sys.exit(2)

    registry_path = (
        sys.argv[1]
        if len(sys.argv) == 3
        else None
    )

    audit_path = (
        sys.argv[2]
        if len(sys.argv) == 3
        else None
    )

    validation_errors = (
        validate_retirement_audit_consistency(
            registry_path,
            audit_path,
        )
    )

    if validation_errors:

        print(
            "BIDIRECTIONAL RETIREMENT AUDIT "
            "CONSISTENCY VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "BIDIRECTIONAL RETIREMENT AUDIT "
        "CONSISTENCY VALIDATION PASSED"
    )

    sys.exit(0)
