import json
import sys
from pathlib import Path

from validate_technical_review import (
    validate_review_fingerprint,
)

from validate_technical_review_history import (
    validate_historical_review_transition,
)


def load_review_registry(registry_path, label):
    """
    Load a reference-home registry and create
    a lookup indexed by home ID and version.
    """

    errors = []
    homes = {}

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

        return {}, [
            f"Unable to read {label} registry: {exc}"
        ]

    if not isinstance(registry, dict):
        return {}, [
            f"{label} registry must be a JSON object"
        ]

    reference_homes = registry.get(
        "reference_homes"
    )

    if not isinstance(reference_homes, list):
        return {}, [
            f"{label} registry must contain "
            "a reference_homes array"
        ]

    for index, home in enumerate(reference_homes):

        if not isinstance(home, dict):
            errors.append(
                f"{label} registry contains malformed "
                f"reference home at index {index}"
            )
            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")

        if (
            not isinstance(home_id, str)
            or not home_id.strip()
            or not isinstance(version, str)
            or not version.strip()
        ):
            errors.append(
                f"{label} registry contains missing "
                f"or invalid home identity at index {index}"
            )
            continue

        key = (home_id, version)

        if key in homes:
            errors.append(
                f"{label} registry contains duplicate "
                f"reference home version: "
                f"{home_id}/{version}"
            )
            continue

        homes[key] = home

    return homes, errors


def validate_current_review_registry(registry_path):
    """
    Validate technical review documentation and
    fingerprints for every current reference home.
    """

    homes, errors = load_review_registry(
        registry_path,
        "Current",
    )

    if errors:
        return errors

    if not homes:
        return [
            "Current registry must contain "
            "at least one reference home"
        ]

    for home in homes.values():
        errors.extend(
            validate_review_fingerprint(home)
        )

    return errors


def validate_historical_review_registry(
    previous_registry_path,
    current_registry_path,
):
    """
    Compare all reference-home versions against
    the previous accepted registry.

    Validate new reference homes and protect
    historical technical review information.
    """

    previous_homes, previous_errors = (
        load_review_registry(
            previous_registry_path,
            "Previous",
        )
    )

    current_homes, current_errors = (
        load_review_registry(
            current_registry_path,
            "Current",
        )
    )

    errors = previous_errors + current_errors

    if errors:
        return errors

    if not current_homes:
        errors.append(
            "Current registry must contain "
            "at least one reference home"
        )

    # Previously registered versions cannot
    # disappear from the proposed registry.
    for key in previous_homes:

        if key not in current_homes:
            errors.append(
                f"{key[0]}/{key[1]}: Previously registered "
                "reference home version cannot be removed"
            )

    for key, current_home in current_homes.items():

        prefix = f"{key[0]}/{key[1]}"

        previous_home = previous_homes.get(key)

        # Newly registered versions must begin
        # in DEVELOPMENT with no active review.
        if previous_home is None:

            errors.extend(
                validate_review_fingerprint(
                    current_home
                )
            )

            if current_home.get("status") != "DEVELOPMENT":
                errors.append(
                    f"{prefix}: New reference home "
                    "must begin in DEVELOPMENT"
                )

            continue

        # Existing versions must comply with
        # historical technical review safeguards.
        errors.extend(
            validate_historical_review_transition(
                previous_home,
                current_home,
            )
        )

    return errors


if __name__ == "__main__":

    if len(sys.argv) == 2:

        validation_name = (
            "CURRENT TECHNICAL REVIEW REGISTRY"
        )

        validation_errors = (
            validate_current_review_registry(
                sys.argv[1]
            )
        )

    elif (
        len(sys.argv) == 4
        and sys.argv[1] == "--historical"
    ):

        validation_name = (
            "HISTORICAL TECHNICAL REVIEW REGISTRY"
        )

        validation_errors = (
            validate_historical_review_registry(
                sys.argv[2],
                sys.argv[3],
            )
        )

    else:

        print(
            "Usage: python "
            "validate_technical_review_registry.py "
            "<current-registry>"
        )

        print(
            "   or: python "
            "validate_technical_review_registry.py "
            "--historical "
            "<previous-registry> <current-registry>"
        )

        sys.exit(2)

    if validation_errors:

        print(
            f"{validation_name} VALIDATION FAILED"
        )

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        f"{validation_name} VALIDATION PASSED"
    )

    sys.exit(0)
