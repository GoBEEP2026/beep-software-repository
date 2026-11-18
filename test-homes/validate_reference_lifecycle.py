import json
import sys
from pathlib import Path


def validate_reference_lifecycle(previous_registry_path, current_registry_path):
    """
    Compare previous and proposed reference-home registries.

    Future checks will enforce approved-version immutability
    and authorized lifecycle transitions.
    """

    errors = []

    for label, path in (
        ("previous", previous_registry_path),
        ("current", current_registry_path),
    ):
        try:
            registry = json.loads(
                Path(path).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(
                f"Unable to read {label} registry: {exc}"
            )
            continue

        if not isinstance(registry, dict):
            errors.append(
                f"{label.capitalize()} registry must be a JSON object"
            )
            continue

        if not isinstance(registry.get("reference_homes"), list):
            errors.append(
                f"{label.capitalize()} registry must contain "
                "a reference_homes array"
            )

    return errors


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python validate_reference_lifecycle.py "
            "<previous-registry> <current-registry>"
        )
        sys.exit(2)

    validation_errors = validate_reference_lifecycle(
        sys.argv[1],
        sys.argv[2],
    )

    if validation_errors:
        print("REFERENCE HOME LIFECYCLE VALIDATION FAILED")

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print("REFERENCE HOME LIFECYCLE VALIDATION PASSED")
    sys.exit(0)
