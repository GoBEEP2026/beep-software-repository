import json
import sys
from datetime import date
from pathlib import Path

from validate_technical_review import (
    validate_review_fingerprint,
    is_valid_review_date,
)


def validate_review_approval_chronology(home):
    """
    Verify that Board approval does not predate
    the completed technical review.

    Applies to APPROVED and RETIRED versions.
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

    status = home.get("status")

    if status not in (
        "DEVELOPMENT",
        "UNDER_REVIEW",
        "APPROVED",
        "RETIRED",
    ):
        return [
            f"{prefix}: Invalid reference home "
            "lifecycle status"
        ]

    # Development and active review versions
    # are not yet subject to approval chronology.
    if status in (
        "DEVELOPMENT",
        "UNDER_REVIEW",
    ):
        return []

    # Approved and retired versions must retain
    # a valid completed technical review.
    errors = validate_review_fingerprint(home)

    if errors:
        return errors

    approval = home.get("approval")

    if not isinstance(approval, dict):
        return [
            f"{prefix}: Missing or invalid "
            "approval metadata"
        ]

    review_date = home["review"].get(
        "review_date"
    )

    approval_date = approval.get(
        "approval_date"
    )

    if not is_valid_review_date(review_date):
        errors.append(
            f"{prefix}: Missing or invalid "
            "technical review date"
        )

    if not is_valid_review_date(approval_date):
        errors.append(
            f"{prefix}: Missing or invalid "
            "Board approval date"
        )

    if errors:
        return errors

    parsed_review_date = date.fromisoformat(
        review_date
    )

    parsed_approval_date = date.fromisoformat(
        approval_date
    )

    if parsed_approval_date < parsed_review_date:
        errors.append(
            f"{prefix}: Board approval date "
            "cannot precede the technical review date"
        )

        errors.append(
            f"{prefix}: Technical review date: "
            f"{review_date}"
        )

        errors.append(
            f"{prefix}: Board approval date: "
            f"{approval_date}"
        )

    return errors


def validate_registry_approval_chronology(
    registry_path=None,
):
    """
    Validate review and approval chronology
    for every registered reference-home version.
    """

    if registry_path is None:
        registry_path = (
            Path(__file__).resolve().parent
            / "reference-home-registry.json"
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
            f"Unable to read reference registry: {exc}"
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
            validate_review_approval_chronology(
                home
            )
        )

    return errors


if __name__ == "__main__":

    if len(sys.argv) > 2:
        print(
            "Usage: python "
            "validate_review_approval_chronology.py "
            "[registry-path]"
        )

        sys.exit(2)

    registry_path = (
        sys.argv[1]
        if len(sys.argv) == 2
        else None
    )

    validation_errors = (
        validate_registry_approval_chronology(
            registry_path
        )
    )

    if validation_errors:

        print(
            "REVIEW AND APPROVAL CHRONOLOGY "
            "VALIDATION FAILED"
        )

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "REVIEW AND APPROVAL CHRONOLOGY "
        "VALIDATION PASSED"
    )

    sys.exit(0)
