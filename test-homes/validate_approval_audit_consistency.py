import sys
from pathlib import Path

from validate_reference_audit import (
    AUDIT_FILE,
    GOVERNANCE_AUTHORITY,
    load_audit_registry,
    validate_live_audit_data,
)

from validate_review_identifiers import (
    is_valid_identifier,
    is_valid_version,
)

from validate_technical_review import (
    validate_review_fingerprint,
)


REFERENCE_REGISTRY_FILE = (
    Path(__file__).resolve().parent
    / "reference-home-registry.json"
)

VALID_STATUSES = {
    "DEVELOPMENT",
    "UNDER_REVIEW",
    "APPROVED",
    "RETIRED",
}

APPROVAL_REQUIRED_STATUSES = {
    "APPROVED",
    "RETIRED",
}

APPROVAL_MATCHED_FIELDS = {
    "approval_record": "record_id",
    "approved_by": "approval_authority",
    "approval_date": "decision_date",
    "board_resolution_reference":
        "board_resolution_reference",
}

REVIEW_MATCHED_FIELDS = {
    "reviewer": "reviewer",
    "review_record": "technical_review_record",
    "review_date": "technical_review_date",
    "reviewed_content_sha256":
        "reviewed_content_sha256",
}


def build_reference_home_lookup(registry):
    """
    Build a reference home lookup using the
    exact home identifier and semantic version.

    Reject malformed entries and duplicate
    home-version combinations.
    """

    if not isinstance(registry, dict):

        return {}, [
            "Reference registry must be an object"
        ]

    homes = registry.get("reference_homes")

    if not isinstance(homes, list) or not homes:

        return {}, [
            "Reference registry has no valid home entries"
        ]

    lookup = {}

    errors = []

    for index, home in enumerate(
        homes,
        start=1,
    ):

        if not isinstance(home, dict):

            errors.append(
                f"Home {index}: "
                "Invalid reference home entry"
            )

            continue

        home_id = home.get("test_home_id")

        version = home.get("test_home_version")

        if not is_valid_identifier(home_id):

            errors.append(
                f"Home {index}: "
                "Invalid reference home identifier"
            )

            continue

        if not is_valid_version(version):

            errors.append(
                f"Home {index}: "
                "Invalid reference home version"
            )

            continue

        key = (home_id, version)

        prefix = f"{home_id}/{version}"

        if key in lookup:

            errors.append(
                f"{prefix}: Duplicate reference "
                "home version"
            )

            continue

        status = home.get("status")

        if (
            not isinstance(status, str)
            or status not in VALID_STATUSES
        ):

            errors.append(
                f"{prefix}: Invalid reference "
                "home lifecycle status"
            )

            continue

        lookup[key] = home

    return lookup, errors


def build_approved_audit_lookup(audit):
    """
    Group schema-validated APPROVED audit
    decisions by exact home identifier
    and version.

    Historical REJECTED and RETIRED decisions
    are not treated as original approvals.
    """

    lookup = {}

    for record in audit["records"]:

        if record["decision"] != "APPROVED":

            continue

        key = (
            record["reference_home_id"],
            record["reference_home_version"],
        )

        lookup.setdefault(
            key,
            [],
        ).append(record)

    return lookup


def validate_approved_home_evidence(home):
    """
    Validate the approval authority and
    completed technical review evidence
    retained by an APPROVED or RETIRED home.
    """

    errors = []

    approval = home.get("approval")

    if not isinstance(approval, dict):

        errors.append(
            "Missing approval metadata"
        )

    else:

        if (
            approval.get("approved_by")
            != GOVERNANCE_AUTHORITY
        ):

            errors.append(
                "Invalid reference home "
                "approval authority"
            )

    review = home.get("review")

    if not isinstance(review, dict):

        errors.append(
            "Missing technical review metadata"
        )

        return errors

    if review.get("review_status") != "COMPLETED":

        errors.append(
            "Approved or retired reference home "
            "requires COMPLETED technical review"
        )

    if (
        review.get("review_recommendation")
        != "RECOMMEND_APPROVAL"
    ):

        errors.append(
            "Approved or retired reference home "
            "requires RECOMMEND_APPROVAL"
        )

    errors.extend(
        validate_review_fingerprint(home)
    )

    return errors


def validate_approval_record_match(
    home,
    record,
):
    """
    Compare the original APPROVED audit
    decision against the approval and
    technical review metadata retained
    by the reference home.
    """

    errors = []

    approval = home.get("approval")

    review = home.get("review")

    if not isinstance(approval, dict):

        errors.append(
            "Missing approval metadata"
        )

    else:

        for home_field, audit_field in (
            APPROVAL_MATCHED_FIELDS.items()
        ):

            if (
                approval.get(home_field)
                != record[audit_field]
            ):

                errors.append(
                    "Approval audit metadata "
                    f"mismatch: {home_field}"
                )

    if not isinstance(review, dict):

        errors.append(
            "Missing technical review metadata"
        )

    else:

        for home_field, audit_field in (
            REVIEW_MATCHED_FIELDS.items()
        ):

            if (
                review.get(home_field)
                != record[audit_field]
            ):

                errors.append(
                    "Approval audit technical "
                    f"review mismatch: {home_field}"
                )

    return errors


def validate_home_to_audit(
    homes_by_key,
    approved_audits_by_key,
):
    """
    Forward validation.

    Every APPROVED or RETIRED reference
    home must retain exactly one matching
    original APPROVED audit decision.
    """

    errors = []

    for key, home in homes_by_key.items():

        if (
            home["status"]
            not in APPROVAL_REQUIRED_STATUSES
        ):

            continue

        home_id, version = key

        prefix = f"{home_id}/{version}"

        home_errors = (
            validate_approved_home_evidence(
                home
            )
        )

        errors.extend(
            f"{prefix}: {error}"
            for error in home_errors
        )

        records = approved_audits_by_key.get(
            key,
            [],
        )

        if not records:

            errors.append(
                f"{prefix}: Missing original "
                "APPROVED audit decision"
            )

            continue

        if len(records) != 1:

            errors.append(
                f"{prefix}: Multiple APPROVED "
                "audit decisions for the same "
                "reference home version"
            )

            continue

        match_errors = (
            validate_approval_record_match(
                home,
                records[0],
            )
        )

        errors.extend(
            f"{prefix}: {error}"
            for error in match_errors
        )

    return errors


def validate_audit_to_home(
    homes_by_key,
    approved_audits_by_key,
):
    """
    Reverse validation.

    Every APPROVED audit decision must
    reference an existing APPROVED or
    RETIRED reference home version.
    """

    errors = []

    for key, records in (
        approved_audits_by_key.items()
    ):

        home_id, version = key

        prefix = f"{home_id}/{version}"

        home = homes_by_key.get(key)

        if home is None:

            for record in records:

                errors.append(
                    f"{prefix}: APPROVED audit "
                    f"record {record['record_id']} "
                    "references an unregistered "
                    "reference home version"
                )

            continue

        if (
            home["status"]
            not in APPROVAL_REQUIRED_STATUSES
        ):

            for record in records:

                errors.append(
                    f"{prefix}: APPROVED audit "
                    f"record {record['record_id']} "
                    "references an ineligible "
                    "reference home status: "
                    f"{home['status']}"
                )

    return errors


def validate_approval_audit_consistency_data(
    registry,
    audit,
):
    """
    Validate reference home and approval
    audit consistency in both directions.

    Audit schema validation must succeed
    before audit records are accessed.
    """

    errors = []

    audit_errors = validate_live_audit_data(
        audit
    )

    errors.extend(
        f"Approval audit registry: {error}"
        for error in audit_errors
    )

    homes_by_key, registry_errors = (
        build_reference_home_lookup(
            registry
        )
    )

    errors.extend(
        f"Reference home registry: {error}"
        for error in registry_errors
    )

    if errors:

        return errors

    approved_audits_by_key = (
        build_approved_audit_lookup(
            audit
        )
    )

    errors.extend(
        validate_home_to_audit(
            homes_by_key,
            approved_audits_by_key,
        )
    )

    errors.extend(
        validate_audit_to_home(
            homes_by_key,
            approved_audits_by_key,
        )
    )

    return errors


def validate_approval_audit_consistency(
    registry_path=None,
    audit_path=None,
):
    """
    Load and cross-validate the reference
    home registry and approval audit registry.

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
            validate_approval_audit_consistency_data(
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
            "Unable to validate approval "
            f"audit consistency: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) not in {1, 3}:

        print(
            "Usage: python "
            "validate_approval_audit_consistency.py "
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
        validate_approval_audit_consistency(
            registry_path,
            audit_path,
        )
    )

    if validation_errors:

        print(
            "BIDIRECTIONAL APPROVAL AUDIT "
            "CONSISTENCY VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "BIDIRECTIONAL APPROVAL AUDIT "
        "CONSISTENCY VALIDATION PASSED"
    )

    sys.exit(0)
