import sys
from datetime import date
from pathlib import Path

from validate_reference_audit import (
    CURRENT_SCHEMA_VERSION,
    TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    load_audit_registry,
)

from validate_audit_append_only import (
    validate_append_only_data,
)

from validate_approval_audit_consistency import (
    build_reference_home_lookup,
    validate_approval_record_match,
)

from validate_retirement_audit_consistency import (
    PRESERVED_REVIEW_FIELDS,
    validate_retirement_audit_consistency_data,
)

from validate_technical_review import (
    validate_review_fingerprint,
)

from validate_technical_review_history import (
    validate_historical_review_transition,
)


REVIEW_MATCHED_FIELDS = {
    "reviewer": "reviewer",
    "technical_review_record": "review_record",
    "technical_review_date": "review_date",
    "reviewed_content_sha256": (
        "reviewed_content_sha256"
    ),
}


AUTHORIZED_TRANSITIONS = {
    "APPROVED": {
        ("UNDER_REVIEW", "APPROVED"),
    },
    "REJECTED": {
        ("UNDER_REVIEW", "UNDER_REVIEW"),
        ("UNDER_REVIEW", "DEVELOPMENT"),
    },
    "RETIRED": {
        ("APPROVED", "RETIRED"),
    },
}


def get_home_key(record):

    return (
        record["reference_home_id"],
        record["reference_home_version"],
    )


def get_new_audit_records(
    previous_audit,
    current_audit,
):

    return current_audit["records"][
        len(previous_audit["records"]):
    ]


def validate_decision_transition(
    record,
    previous_home,
    current_home,
):

    if previous_home is None:

        return [
            "Audit decision requires a previously "
            "registered reference home version"
        ]

    if current_home is None:

        return [
            "Audit decision references a missing "
            "current reference home version"
        ]

    decision = record["decision"]

    transition = (
        previous_home["status"],
        current_home["status"],
    )

    if transition not in (
        AUTHORIZED_TRANSITIONS[decision]
    ):

        return [
            f"Unauthorized {decision} audit decision "
            f"for lifecycle transition "
            f"{transition[0]} to {transition[1]}"
        ]

    return []


def validate_previous_review(
    record,
    previous_home,
    require_recommendation=False,
):

    errors = []

    review = previous_home.get("review")

    if not isinstance(review, dict):

        return [
            "Missing previously accepted "
            "technical review metadata"
        ]

    if review.get("review_status") != "COMPLETED":

        return [
            "Decision requires a previously "
            "accepted COMPLETED technical review"
        ]

    errors.extend(
        validate_review_fingerprint(
            previous_home
        )
    )

    if (
        require_recommendation
        and review.get("review_recommendation")
        != "RECOMMEND_APPROVAL"
    ):

        errors.append(
            "Decision requires a previously "
            "accepted RECOMMEND_APPROVAL"
        )

    for audit_field, review_field in (
        REVIEW_MATCHED_FIELDS.items()
    ):

        if (
            record.get(audit_field)
            != review.get(review_field)
        ):

            errors.append(
                "Historical technical review "
                f"evidence mismatch: {audit_field}"
            )

    if not errors:

        if (
            date.fromisoformat(
                record["decision_date"]
            )
            < date.fromisoformat(
                review["review_date"]
            )
        ):

            errors.append(
                "Audit decision cannot precede "
                "the previously accepted "
                "technical review completion date"
            )

    return errors


def validate_new_approval(
    record,
    previous_home,
    current_home,
):

    errors = []

    errors.extend(
        validate_previous_review(
            record,
            previous_home,
            require_recommendation=True,
        )
    )

    errors.extend(
        validate_historical_review_transition(
            previous_home,
            current_home,
        )
    )

    errors.extend(
        validate_approval_record_match(
            current_home,
            record,
        )
    )

    return errors


def validate_new_rejection(
    record,
    previous_home,
    current_home,
):

    errors = []

    errors.extend(
        validate_review_fingerprint(
            previous_home
        )
    )

    errors.extend(
        validate_historical_review_transition(
            previous_home,
            current_home,
        )
    )

    review = previous_home.get("review")

    if not isinstance(review, dict):

        return errors + [
            "Missing previously accepted "
            "technical review metadata"
        ]

    evidence_is_null = all(
        record[field] is None
        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS
    )

    if evidence_is_null:

        if review.get("review_status") == "COMPLETED":

            errors.append(
                "REJECTED decision must preserve "
                "previously accepted completed "
                "technical review evidence"
            )

    else:

        errors.extend(
            validate_previous_review(
                record,
                previous_home,
                require_recommendation=False,
            )
        )

    if (
        current_home["status"] == "UNDER_REVIEW"
        and previous_home["review"].get(
            "review_status"
        ) == "COMPLETED"
        and current_home.get("review")
        != previous_home.get("review")
    ):

        errors.append(
            "Controlled rejection cannot modify "
            "an active completed technical review"
        )

    return errors


def validate_new_retirement(
    record,
    previous_home,
    current_home,
    previous_records,
):

    errors = []

    errors.extend(
        validate_previous_review(
            record,
            previous_home,
            require_recommendation=True,
        )
    )

    errors.extend(
        validate_historical_review_transition(
            previous_home,
            current_home,
        )
    )

    previous_metadata = {
        field: value
        for field, value in previous_home.items()
        if field != "status"
    }

    current_metadata = {
        field: value
        for field, value in current_home.items()
        if field != "status"
    }

    if previous_metadata != current_metadata:

        errors.append(
            "Retirement cannot modify previously "
            "approved reference home metadata"
        )

    original_approvals = [
        historical_record
        for historical_record in previous_records
        if (
            historical_record["decision"]
            == "APPROVED"
            and get_home_key(historical_record)
            == get_home_key(record)
        )
    ]

    if len(original_approvals) != 1:

        errors.append(
            "Retirement requires exactly one "
            "previously accepted APPROVED "
            "audit decision"
        )

        return errors

    original_approval = original_approvals[0]

    errors.extend(
        validate_approval_record_match(
            previous_home,
            original_approval,
        )
    )

    for field in PRESERVED_REVIEW_FIELDS:

        if record[field] != original_approval[field]:

            errors.append(
                "Retirement historical evidence "
                f"mismatch: {field}"
            )

    if (
        date.fromisoformat(
            record["decision_date"]
        )
        < date.fromisoformat(
            original_approval["decision_date"]
        )
    ):

        errors.append(
            "Retirement cannot precede "
            "previously accepted approval"
        )

    return errors


def validate_rejection_resolution(
    record,
    earlier_records,
):

    errors = []

    resolution = record[
        "board_resolution_reference"
    ].strip().casefold()

    for earlier_record in earlier_records:

        if (
            get_home_key(earlier_record)
            != get_home_key(record)
        ):

            continue

        if (
            earlier_record[
                "board_resolution_reference"
            ].strip().casefold()
            == resolution
        ):

            errors.append(
                "REJECTED decision requires an "
                "independent Board resolution "
                "reference for this home version"
            )

            break

    return errors


def validate_new_decisions(
    previous_homes,
    current_homes,
    previous_records,
    new_records,
):

    errors = []

    earlier_records = list(previous_records)

    for record in new_records:

        key = get_home_key(record)

        home_id, version = key

        prefix = (
            f"{home_id}/{version}: "
            f"{record['record_id']}"
        )

        previous_home = previous_homes.get(key)

        current_home = current_homes.get(key)

        decision_errors = (
            validate_decision_transition(
                record,
                previous_home,
                current_home,
            )
        )

        if not decision_errors:

            decision = record["decision"]

            if decision == "APPROVED":

                decision_errors.extend(
                    validate_new_approval(
                        record,
                        previous_home,
                        current_home,
                    )
                )

            elif decision == "REJECTED":

                decision_errors.extend(
                    validate_new_rejection(
                        record,
                        previous_home,
                        current_home,
                    )
                )

                decision_errors.extend(
                    validate_rejection_resolution(
                        record,
                        earlier_records,
                    )
                )

            elif decision == "RETIRED":

                decision_errors.extend(
                    validate_new_retirement(
                        record,
                        previous_home,
                        current_home,
                        previous_records,
                    )
                )

        errors.extend(
            f"{prefix}: {error}"
            for error in decision_errors
        )

        earlier_records.append(record)

    return errors


def validate_required_decisions(
    previous_homes,
    current_homes,
    new_records,
):

    errors = []

    for key, current_home in current_homes.items():

        previous_home = previous_homes.get(key)

        previous_status = (
            previous_home["status"]
            if previous_home is not None
            else None
        )

        current_status = current_home["status"]

        required_decision = None

        if (
            current_status == "APPROVED"
            and previous_status != "APPROVED"
        ):

            required_decision = "APPROVED"

        elif (
            current_status == "RETIRED"
            and previous_status != "RETIRED"
        ):

            required_decision = "RETIRED"

        if required_decision is None:

            continue

        matching_records = [
            record
            for record in new_records
            if (
                get_home_key(record) == key
                and record["decision"]
                == required_decision
            )
        ]

        if len(matching_records) != 1:

            errors.append(
                f"{key[0]}/{key[1]}: "
                f"Lifecycle transition requires "
                f"exactly one newly appended "
                f"{required_decision} audit decision"
            )

    return errors


def validate_audit_decision_history_data(
    previous_registry,
    current_registry,
    previous_audit,
    current_audit,
):

    errors = []

    errors.extend(
        validate_append_only_data(
            previous_audit,
            current_audit,
        )
    )

    previous_homes, previous_errors = (
        build_reference_home_lookup(
            previous_registry
        )
    )

    current_homes, current_errors = (
        build_reference_home_lookup(
            current_registry
        )
    )

    errors.extend(
        f"Historical reference registry: {error}"
        for error in previous_errors
    )

    errors.extend(
        f"Current reference registry: {error}"
        for error in current_errors
    )

    if errors:

        return errors

    errors.extend(
        validate_retirement_audit_consistency_data(
            current_registry,
            current_audit,
        )
    )

    if (
        previous_audit["audit_schema_version"]
        == CURRENT_SCHEMA_VERSION
    ):

        errors.extend(
            f"Historical decision consistency: {error}"
            for error in (
                validate_retirement_audit_consistency_data(
                    previous_registry,
                    previous_audit,
                )
            )
        )

    else:

        for key, home in previous_homes.items():

            if home["status"] in (
                "APPROVED",
                "RETIRED",
            ):

                errors.append(
                    f"{key[0]}/{key[1]}: "
                    "Legacy audit migration cannot "
                    "bypass historical approval "
                    "or retirement validation"
                )

    if errors:

        return errors

    for key in previous_homes:

        if key not in current_homes:

            errors.append(
                f"{key[0]}/{key[1]}: "
                "Previously registered reference "
                "home version cannot be removed"
            )

    new_records = get_new_audit_records(
        previous_audit,
        current_audit,
    )

    errors.extend(
        validate_new_decisions(
            previous_homes,
            current_homes,
            previous_audit["records"],
            new_records,
        )
    )

    errors.extend(
        validate_required_decisions(
            previous_homes,
            current_homes,
            new_records,
        )
    )

    return errors


def validate_audit_decision_history(
    previous_registry_path,
    current_registry_path,
    previous_audit_path,
    current_audit_path,
):

    try:

        paths = [
            Path(previous_registry_path),
            Path(current_registry_path),
            Path(previous_audit_path),
            Path(current_audit_path),
        ]

        for path in paths:

            if path.is_symlink():

                return [
                    "Historical decision registry "
                    f"cannot be a symbolic link: {path}"
                ]

        registries = [
            load_audit_registry(path)
            for path in paths
        ]

        return validate_audit_decision_history_data(
            *registries
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
            "Unable to validate historical "
            f"audit decisions: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) != 5:

        print(
            "Usage: python "
            "validate_audit_decision_history.py "
            "<previous-reference-registry> "
            "<current-reference-registry> "
            "<previous-audit-registry> "
            "<current-audit-registry>"
        )

        sys.exit(2)

    validation_errors = (
        validate_audit_decision_history(
            sys.argv[1],
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
        )
    )

    if validation_errors:

        print(
            "HISTORICAL AUDIT DECISION "
            "AUTHORIZATION VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "HISTORICAL AUDIT DECISION "
        "AUTHORIZATION VALIDATION PASSED"
    )

    sys.exit(0)
