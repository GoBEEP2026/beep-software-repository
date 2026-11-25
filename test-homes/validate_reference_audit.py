import json
import re
import sys
from datetime import date
from pathlib import Path


AUDIT_FILE = (
    Path(__file__).resolve().parent
    / "reference-approval-audit.json"
)

LEGACY_SCHEMA_VERSION = "1.0.0"

CURRENT_SCHEMA_VERSION = "1.1.0"

SUPPORTED_SCHEMA_VERSIONS = {
    LEGACY_SCHEMA_VERSION,
    CURRENT_SCHEMA_VERSION,
}

REPOSITORY_NAME = (
    "BEEP Software Consistency Repository"
)

AUDIT_STATUS = "DEVELOPMENT"

AUDIT_DESCRIPTION = (
    "Append-only audit records for "
    "reference-home review and approval decisions."
)

GOVERNANCE_AUTHORITY = (
    "B.E.E.P. Board of Directors"
)

VALID_DECISIONS = {
    "APPROVED",
    "REJECTED",
    "RETIRED",
}

IDENTIFIER_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_-]*"
)

VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)"
)

SHA256_PATTERN = re.compile(
    r"[0-9a-f]{64}"
)

PLACEHOLDER_VALUES = {
    "pending",
    "required",
    "unknown",
    "none",
    "n/a",
    "tbd",
    "todo",
    "placeholder",
    "to be determined",
    "not yet completed",
    "yyyy-mm-dd",
}

REQUIRED_REGISTRY_FIELDS = {
    "audit_schema_version",
    "repository",
    "audit_status",
    "description",
    "records",
}

LEGACY_RECORD_FIELDS = {
    "record_id",
    "reference_home_id",
    "reference_home_version",
    "decision",
    "reviewer",
    "approval_authority",
    "evidence",
    "pull_request",
    "board_resolution_reference",
    "decision_date",
}

TECHNICAL_REVIEW_EVIDENCE_FIELDS = {
    "technical_review_record",
    "technical_review_date",
    "technical_review_sha256",
    "reviewed_content_sha256",
}

CURRENT_RECORD_FIELDS = (
    LEGACY_RECORD_FIELDS
    | TECHNICAL_REVIEW_EVIDENCE_FIELDS
)


def reject_duplicate_json_keys(pairs):

    result = {}

    for key, value in pairs:

        if key in result:

            raise ValueError(
                f"Duplicate JSON key: {key}"
            )

        result[key] = value

    return result


def load_audit_registry(path=AUDIT_FILE):

    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )


def is_valid_identifier(value):

    return (
        isinstance(value, str)
        and IDENTIFIER_PATTERN.fullmatch(value)
        is not None
    )


def is_valid_version(value):

    return (
        isinstance(value, str)
        and VERSION_PATTERN.fullmatch(value)
        is not None
    )


def is_valid_sha256(value):

    return (
        isinstance(value, str)
        and SHA256_PATTERN.fullmatch(value)
        is not None
    )


def is_valid_date(value):

    if not isinstance(value, str):

        return False

    try:

        parsed = date.fromisoformat(value)

        return parsed.isoformat() == value

    except ValueError:

        return False


def is_valid_text(value):

    if not isinstance(value, str):

        return False

    if not value.strip():

        return False

    if value != value.strip():

        return False

    if len(value.splitlines()) != 1:

        return False

    if value.casefold() in PLACEHOLDER_VALUES:

        return False

    if re.fullmatch(r"\[.*\]", value):

        return False

    return True


def validate_technical_review_evidence(record):

    errors = []

    decision = record.get("decision")

    missing_fields = (
        TECHNICAL_REVIEW_EVIDENCE_FIELDS
        - record.keys()
    )

    if missing_fields:

        for field in sorted(missing_fields):

            errors.append(
                f"Missing {field}"
            )

        return errors

    evidence_values = [
        record[field]
        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS
    ]

    all_null = all(
        value is None
        for value in evidence_values
    )

    any_null = any(
        value is None
        for value in evidence_values
    )

    if decision == "REJECTED" and all_null:

        return errors

    if any_null:

        if decision == "REJECTED":

            errors.append(
                "REJECTED audit decisions require "
                "either complete technical review "
                "evidence or all-null evidence"
            )

        else:

            errors.append(
                f"{decision} audit decisions require "
                "complete technical review evidence"
            )

        return errors

    if not is_valid_identifier(
        record.get("technical_review_record")
    ):

        errors.append(
            "Invalid technical review record identifier"
        )

    review_date = record.get(
        "technical_review_date"
    )

    if not is_valid_date(review_date):

        errors.append(
            "Invalid technical review completion date"
        )

    if not is_valid_sha256(
        record.get("technical_review_sha256")
    ):

        errors.append(
            "Invalid technical review document "
            "SHA-256 checksum"
        )

    if not is_valid_sha256(
        record.get("reviewed_content_sha256")
    ):

        errors.append(
            "Invalid reviewed content "
            "SHA-256 fingerprint"
        )

    decision_date = record.get("decision_date")

    if (
        is_valid_date(review_date)
        and is_valid_date(decision_date)
        and review_date > decision_date
    ):

        errors.append(
            "Audit decision date cannot precede "
            "the technical review completion date"
        )

    return errors


def validate_legacy_record(record):

    """
    Preserve existing schema 1.0.0 validation
    during the controlled migration period.
    """

    errors = []

    record_id = record.get("record_id")

    if (
        not isinstance(record_id, str)
        or not record_id.strip()
    ):

        errors.append("Missing record ID")

    home_id = record.get("reference_home_id")

    if (
        not isinstance(home_id, str)
        or not home_id.strip()
    ):

        errors.append(
            "Missing reference home ID"
        )

    version = record.get(
        "reference_home_version"
    )

    if (
        not isinstance(version, str)
        or not re.fullmatch(
            r"\d+\.\d+\.\d+", version
        )
    ):

        errors.append(
            "Invalid reference home version"
        )

    decision = record.get("decision")

    if (
        not isinstance(decision, str)
        or decision not in VALID_DECISIONS
    ):

        errors.append("Invalid decision")

    for field in (
        "reviewer",
        "approval_authority",
        "evidence",
        "pull_request",
        "board_resolution_reference",
    ):

        value = record.get(field)

        if (
            not isinstance(value, str)
            or not value.strip()
        ):

            errors.append(f"Missing {field}")

    if not is_valid_date(
        record.get("decision_date")
    ):

        errors.append("Invalid decision date")

    return errors


def validate_current_record(record):

    errors = []

    missing_fields = (
        CURRENT_RECORD_FIELDS - record.keys()
    )

    unexpected_fields = (
        record.keys() - CURRENT_RECORD_FIELDS
    )

    for field in sorted(missing_fields):

        errors.append(f"Missing {field}")

    for field in sorted(unexpected_fields):

        errors.append(
            f"Unexpected audit record field: {field}"
        )

    if missing_fields:

        return errors

    if not is_valid_identifier(
        record.get("record_id")
    ):

        errors.append("Invalid audit record ID")

    if not is_valid_identifier(
        record.get("reference_home_id")
    ):

        errors.append(
            "Invalid reference home ID"
        )

    if not is_valid_version(
        record.get("reference_home_version")
    ):

        errors.append(
            "Invalid reference home version"
        )

    decision = record.get("decision")

    valid_decision = (
        isinstance(decision, str)
        and decision in VALID_DECISIONS
    )

    if not valid_decision:

        errors.append("Invalid decision")

    for field in (
        "reviewer",
        "evidence",
        "pull_request",
        "board_resolution_reference",
    ):

        if not is_valid_text(record.get(field)):

            errors.append(
                f"Missing or invalid {field}"
            )

    if (
        record.get("approval_authority")
        != GOVERNANCE_AUTHORITY
    ):

        errors.append(
            "Invalid approval authority"
        )

    if not is_valid_date(
        record.get("decision_date")
    ):

        errors.append(
            "Invalid decision date"
        )

    if valid_decision:

        errors.extend(
            validate_technical_review_evidence(
                record
            )
        )

    return errors


def validate_audit_data(audit):

    errors = []

    if not isinstance(audit, dict):

        return [
            "Audit log must be a JSON object"
        ]

    schema_version = audit.get(
        "audit_schema_version"
    )

    if (
        not isinstance(schema_version, str)
        or schema_version
        not in SUPPORTED_SCHEMA_VERSIONS
    ):

        return [
            "Invalid audit schema version"
        ]

    if audit.get("audit_status") != AUDIT_STATUS:

        errors.append(
            "Unsupported audit status"
        )

    if schema_version == CURRENT_SCHEMA_VERSION:

        missing_fields = (
            REQUIRED_REGISTRY_FIELDS
            - audit.keys()
        )

        unexpected_fields = (
            audit.keys()
            - REQUIRED_REGISTRY_FIELDS
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

        if audit.get("description") != AUDIT_DESCRIPTION:

            errors.append(
                "Invalid audit registry description"
            )

    records = audit.get("records")

    if not isinstance(records, list):

        return errors + [
            "Audit records must be an array"
        ]

    seen_ids = set()

    for index, record in enumerate(
        records, start=1
    ):

        prefix = f"Record {index}"

        if not isinstance(record, dict):

            errors.append(
                f"{prefix}: Must be an object"
            )

            continue

        if schema_version == LEGACY_SCHEMA_VERSION:

            record_errors = (
                validate_legacy_record(record)
            )

        else:

            record_errors = (
                validate_current_record(record)
            )

        errors.extend(
            f"{prefix}: {error}"
            for error in record_errors
        )

        record_id = record.get("record_id")

        if (
            isinstance(record_id, str)
            and record_id.strip()
        ):

            uniqueness_key = record_id

            if (
                schema_version
                == CURRENT_SCHEMA_VERSION
            ):

                uniqueness_key = (
                    record_id.casefold()
                )

            if uniqueness_key in seen_ids:

                errors.append(
                    f"{prefix}: Duplicate record ID"
                )

            else:

                seen_ids.add(uniqueness_key)

    return errors


def validate_audit(path=AUDIT_FILE):

    try:

        audit = load_audit_registry(path)

        return validate_audit_data(audit)

    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        RuntimeError,
    ) as exc:

        return [
            f"Unable to load audit log: {exc}"
        ]


if __name__ == "__main__":

    validation_errors = validate_audit()

    if validation_errors:

        print(
            "Reference approval audit "
            "validation FAILED"
        )

        for error in validation_errors:

            print(f"- {error}")

        sys.exit(1)

    print(
        "Reference approval audit "
        "validation PASSED"
    )

    sys.exit(0)
