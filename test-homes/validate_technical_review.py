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
