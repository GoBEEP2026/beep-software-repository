import hashlib
import json
import re
from datetime import date



# Administrative fields are excluded from the
# technical content fingerprint.
EXCLUDED_FINGERPRINT_FIELDS = {
    "status",
    "review",
    "approval",
    "test_cycles",
}


def get_technical_content(home):
    """
    Extract reference-home technical content.

    Administrative review, approval, lifecycle,
    and test-cycle fields are excluded.

    All other fields are included by default.
    """

    if not isinstance(home, dict):
        raise ValueError(
            "Reference home must be a JSON object"
        )

    return {
        key: value
        for key, value in home.items()
        if key not in EXCLUDED_FINGERPRINT_FIELDS
    }


def calculate_technical_fingerprint(home):
    """
    Calculate a deterministic SHA-256 fingerprint
    of reference-home technical content.

    JSON object keys are sorted and formatting
    differences are removed before hashing.
    """

    technical_content = get_technical_content(home)

    canonical_content = json.dumps(
        technical_content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )

    return hashlib.sha256(
        canonical_content.encode("utf-8")
    ).hexdigest()



# Permitted technical review statuses for each
# reference-home lifecycle status.
ALLOWED_REVIEW_STATUSES = {
    "DEVELOPMENT": {
        "NOT_STARTED",
    },
    "UNDER_REVIEW": {
        "IN_PROGRESS",
        "COMPLETED",
    },
    "APPROVED": {
        "COMPLETED",
    },
    "RETIRED": {
        "COMPLETED",
    },
}


def validate_review_status(home):
    """
    Verify that technical review status is compatible
    with the reference-home lifecycle status.
    """

    if not isinstance(home, dict):
        return ["Reference home must be a JSON object"]

    errors = []

    home_id = home.get("test_home_id", "UNKNOWN")
    version = home.get("test_home_version", "UNKNOWN")
    prefix = f"{home_id}/{version}"

    lifecycle_status = home.get("status")

    if (
        not isinstance(lifecycle_status, str)
        or lifecycle_status not in ALLOWED_REVIEW_STATUSES
    ):
        return [
            f"{prefix}: Invalid reference home lifecycle status"
        ]

    review = home.get("review")

    if not isinstance(review, dict):
        return [
            f"{prefix}: Missing or invalid technical review metadata"
        ]

    review_status = review.get("review_status")

    if (
        not isinstance(review_status, str)
        or not review_status.strip()
    ):
        return [
            f"{prefix}: Missing or invalid technical review status"
        ]

    allowed_statuses = ALLOWED_REVIEW_STATUSES[
        lifecycle_status
    ]

    if review_status not in allowed_statuses:
        expected = ", ".join(sorted(allowed_statuses))

        errors.append(
            f"{prefix}: Technical review status "
            f"{review_status!r} is not permitted for "
            f"lifecycle status {lifecycle_status}. "
            f"Expected: {expected}"
        )

    return errors


REQUIRED_REVIEW_FIELDS = (
    "reviewer",
    "review_record",
    "review_status",
    "review_date",
    "review_findings",
    "review_recommendation",
    "conflict_of_interest_disclosure",
    "reviewed_content_sha256",
)

VALID_REVIEW_RECOMMENDATIONS = {
    "RECOMMEND_APPROVAL",
    "REVISIONS_REQUIRED",
}

REVIEW_RECORD_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
)

SHA256_PATTERN = re.compile(
    r"^[0-9a-f]{64}$"
)


def is_nonempty_review_string(value):
    return (
        isinstance(value, str)
        and bool(value.strip())
    )


def is_valid_review_date(value):
    if not isinstance(value, str):
        return False

    try:
        parsed = date.fromisoformat(value)

        return parsed.isoformat() == value

    except ValueError:
        return False


def validate_review_documentation(home):
    """
    Verify required technical review metadata
    based on the current technical review status.

    This validates documentation structure.
    It does not authenticate reviewer decisions.
    """

    errors = validate_review_status(home)

    if errors:
        return errors

    home_id = home.get("test_home_id", "UNKNOWN")
    version = home.get("test_home_version", "UNKNOWN")
    prefix = f"{home_id}/{version}"

    lifecycle_status = home["status"]
    review = home["review"]
    review_status = review["review_status"]

    # Require the complete review metadata structure.
    for field in REQUIRED_REVIEW_FIELDS:
        if field not in review:
            errors.append(
                f"{prefix}: Missing review field {field}"
            )

    if errors:
        return errors

    # Reviews that have not started must not contain
    # active or completed review information.
    if review_status == "NOT_STARTED":

        for field in REQUIRED_REVIEW_FIELDS:

            if field == "review_status":
                continue

            if review[field] is not None:
                errors.append(
                    f"{prefix}: {field} must be null "
                    "when review is NOT_STARTED"
                )

        return errors

    # Active and completed reviews require
    # reviewer identification and disclosure.
    for field in (
        "reviewer",
        "review_record",
        "conflict_of_interest_disclosure",
    ):
        if not is_nonempty_review_string(review[field]):
            errors.append(
                f"{prefix}: Missing or invalid {field}"
            )

    review_record = review["review_record"]

    if (
        is_nonempty_review_string(review_record)
        and not REVIEW_RECORD_PATTERN.fullmatch(
            review_record
        )
    ):
        errors.append(
            f"{prefix}: Invalid technical review "
            "record identifier"
        )

    # In-progress reviews cannot contain final
    # review completion information.
    if review_status == "IN_PROGRESS":

        for field in (
            "review_date",
            "review_recommendation",
            "reviewed_content_sha256",
        ):
            if review[field] is not None:
                errors.append(
                    f"{prefix}: {field} must be null "
                    "when review is IN_PROGRESS"
                )

        findings = review["review_findings"]

        if (
            findings is not None
            and not is_nonempty_review_string(findings)
        ):
            errors.append(
                f"{prefix}: Invalid review_findings"
            )

        return errors

    # Completed reviews require final documentation.
    if not is_valid_review_date(review["review_date"]):
        errors.append(
            f"{prefix}: Invalid technical review date. "
            "Expected YYYY-MM-DD"
        )

    if not is_nonempty_review_string(
        review["review_findings"]
    ):
        errors.append(
            f"{prefix}: Missing technical review findings"
        )

    recommendation = review["review_recommendation"]

    if (
        not isinstance(recommendation, str)
        or recommendation not in
        VALID_REVIEW_RECOMMENDATIONS
    ):
        errors.append(
            f"{prefix}: Invalid technical review "
            "recommendation"
        )

    fingerprint = review["reviewed_content_sha256"]

    if (
        not isinstance(fingerprint, str)
        or not SHA256_PATTERN.fullmatch(fingerprint)
    ):
        errors.append(
            f"{prefix}: Missing or invalid reviewed "
            "content SHA-256 fingerprint"
        )

    # Approved and retired versions must retain
    # a recommendation supporting approval.
    if lifecycle_status in ("APPROVED", "RETIRED"):

        if recommendation != "RECOMMEND_APPROVAL":
            errors.append(
                f"{prefix}: {lifecycle_status} reference "
                "homes require RECOMMEND_APPROVAL"
            )

    return errors
