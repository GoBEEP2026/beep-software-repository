import json
import re
import sys
from pathlib import Path

from validate_technical_review import (
    validate_review_fingerprint,
)


IDENTIFIER_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_-]*"
)

VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)"
)

REGISTRY_MATCHED_FIELDS = {
    "Reference Home ID": "test_home_id",
    "Reference Home Version": "test_home_version",
}

REVIEW_MATCHED_FIELDS = {
    "Technical Review Record ID": "review_record",
    "Technical Reviewer": "reviewer",
    "Technical Review Date": "review_date",
    "Technical Review Status": "review_status",
    "Review Findings": "review_findings",
    "Review Recommendation": "review_recommendation",
    "Conflict-of-Interest Disclosure":
        "conflict_of_interest_disclosure",
    "Reviewed Content SHA-256":
        "reviewed_content_sha256",
}

ADDITIONAL_REQUIRED_FIELDS = (
    "Review Scope",
    "Supporting Evidence",
)

REQUIRED_FIELDS = (
    tuple(REGISTRY_MATCHED_FIELDS)
    + tuple(REVIEW_MATCHED_FIELDS)
    + ADDITIONAL_REQUIRED_FIELDS
)

PLACEHOLDER_VALUES = {
    "required",
    "pending",
    "tbd",
    "todo",
    "placeholder",
    "yyyy-mm-dd",
    "not yet completed",
    "to be determined",
}


def is_valid_record_value(value):
    """
    Reject empty, multiline, and recognized
    placeholder metadata values.
    """

    if not isinstance(value, str):
        return False

    if not value.strip():
        return False

    if len(value.splitlines()) != 1:
        return False

    normalized = value.strip().casefold()

    if normalized in PLACEHOLDER_VALUES:
        return False

    if re.fullmatch(r"\[.*\]", normalized):
        return False

    return True


def extract_review_record_fields(content):
    """
    Extract required single-line metadata fields.

    Reject duplicate, missing, empty, and
    placeholder values.
    """

    if not isinstance(content, str):
        return {}, [
            "Technical review document must contain text"
        ]

    fields = {}
    errors = []

    for field in REQUIRED_FIELDS:

        pattern = re.compile(
            rf"^[ \t]*"
            rf"{re.escape(field)}:"
            rf"[ \t]*(.*)$",
            re.IGNORECASE,
        )

        matches = []

        for line in content.splitlines():
            match = pattern.fullmatch(line)

            if match:
                matches.append(
                    match.group(1).strip()
                )

        if not matches:
            errors.append(
                f"Missing required field: {field}"
            )
            continue

        if len(matches) != 1:
            errors.append(
                f"Duplicate required field: {field}"
            )
            continue

        value = matches[0]

        if not is_valid_record_value(value):
            errors.append(
                f"Invalid or placeholder value "
                f"for {field}"
            )
            continue

        fields[field] = value

    return fields, errors


def validate_review_record_content(home, content):
    """
    Verify document metadata against the registry.
    """

    if not isinstance(home, dict):
        return [
            "Reference home must be a JSON object"
        ]

    review = home.get("review")

    if not isinstance(review, dict):
        return [
            "Missing or invalid technical review metadata"
        ]

    fields, errors = extract_review_record_fields(
        content
    )

    expected_fields = {}

    for field, key in REGISTRY_MATCHED_FIELDS.items():
        expected_fields[field] = home.get(key)

    for field, key in REVIEW_MATCHED_FIELDS.items():
        expected_fields[field] = review.get(key)

    for field, expected in expected_fields.items():

        if not is_valid_record_value(expected):
            errors.append(
                f"Invalid registry value for {field}"
            )
            continue

        if field not in fields:
            continue

        if fields[field] != expected:
            errors.append(
                f"Technical review document "
                f"mismatched {field}"
            )

    if review.get("review_status") != "COMPLETED":
        errors.append(
            "Technical review record requires "
            "COMPLETED review status"
        )

    return errors


def get_review_record_path(home, approvals_directory):
    """
    Construct a safe version-specific document path.

    Reject unsafe identifiers and symbolic links.
    """

    if not isinstance(home, dict):
        raise ValueError(
            "Reference home must be a JSON object"
        )

    home_id = home.get("test_home_id")
    version = home.get("test_home_version")
    review = home.get("review")

    if (
        not isinstance(home_id, str)
        or not IDENTIFIER_PATTERN.fullmatch(home_id)
    ):
        raise ValueError(
            "Invalid reference home identifier"
        )

    if (
        not isinstance(version, str)
        or not VERSION_PATTERN.fullmatch(version)
    ):
        raise ValueError(
            "Invalid reference home version"
        )

    if not isinstance(review, dict):
        raise ValueError(
            "Missing technical review metadata"
        )

    record_id = review.get("review_record")

    if (
        not isinstance(record_id, str)
        or not IDENTIFIER_PATTERN.fullmatch(record_id)
    ):
        raise ValueError(
            "Invalid technical review record identifier"
        )

    root = Path(approvals_directory).absolute()

    record_path = (
        root
        / home_id
        / version
        / "technical-reviews"
        / f"{record_id}.md"
    )

    current_path = record_path

    while True:

        if current_path.is_symlink():
            raise ValueError(
                "Technical review document path "
                "cannot contain symbolic links"
            )

        if current_path == root:
            break

        current_path = current_path.parent

    if not record_path.resolve().is_relative_to(
        root.resolve()
    ):
        raise ValueError(
            "Technical review document path "
            "escapes approvals directory"
        )

    return record_path


def validate_technical_review_record(
    home,
    approvals_directory,
):
    """
    Validate supporting documentation for a
    completed technical review.
    """

    if not isinstance(home, dict):
        return [
            "Reference home must be a JSON object"
        ]

    home_id = home.get(
        "test_home_id", "UNKNOWN"
    )

    version = home.get(
        "test_home_version", "UNKNOWN"
    )

    prefix = f"{home_id}/{version}"

    errors = validate_review_fingerprint(home)

    if errors:
        return errors

    review = home["review"]

    if review["review_status"] != "COMPLETED":
        return []

    try:
        record_path = get_review_record_path(
            home,
            approvals_directory,
        )

        if not record_path.is_file():
            return [
                f"{prefix}: Missing technical review "
                f"document: {record_path}"
            ]

        content = record_path.read_text(
            encoding="utf-8"
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        RuntimeError,
    ) as exc:

        return [
            f"{prefix}: Unable to access technical "
            f"review document: {exc}"
        ]

    document_errors = validate_review_record_content(
        home,
        content,
    )

    return [
        f"{prefix}: {error}"
        for error in document_errors
    ]


def validate_technical_review_records(
    registry_path=None,
    approvals_directory=None,
):
    """
    Validate technical review documentation for
    every registered reference-home version.
    """

    repository_root = (
        Path(__file__).resolve().parent.parent
    )

    if registry_path is None:
        registry_path = (
            repository_root
            / "test-homes"
            / "reference-home-registry.json"
        )

    if approvals_directory is None:
        approvals_directory = (
            repository_root / "approvals"
        )

    try:
        registry = json.loads(
            Path(registry_path).read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
    ) as exc:

        return [
            f"Unable to load reference registry: {exc}"
        ]

    if not isinstance(registry, dict):
        return [
            "Reference registry must be a JSON object"
        ]

    homes = registry.get("reference_homes")

    if not isinstance(homes, list) or not homes:
        return [
            "Reference registry must contain "
            "at least one reference home"
        ]

    errors = []

    for home in homes:
        errors.extend(
            validate_technical_review_record(
                home,
                approvals_directory,
            )
        )

    return errors


if __name__ == "__main__":

    if len(sys.argv) > 3:
        print(
            "Usage: python "
            "validate_technical_review_records.py "
            "[registry-path] [approvals-directory]"
        )

        sys.exit(2)

    registry_path = (
        sys.argv[1]
        if len(sys.argv) >= 2
        else None
    )

    approvals_directory = (
        sys.argv[2]
        if len(sys.argv) == 3
        else None
    )

    validation_errors = (
        validate_technical_review_records(
            registry_path,
            approvals_directory,
        )
    )

    if validation_errors:

        print(
            "TECHNICAL REVIEW RECORD "
            "VALIDATION FAILED"
        )

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "TECHNICAL REVIEW RECORD "
        "VALIDATION PASSED"
    )

    sys.exit(0)
