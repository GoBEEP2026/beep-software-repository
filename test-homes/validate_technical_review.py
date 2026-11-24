import hashlib
import json


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
