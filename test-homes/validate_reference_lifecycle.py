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

    if errors:
        return errors

    previous = json.loads(
        Path(previous_registry_path).read_text(encoding="utf-8")
    )
    current = json.loads(
        Path(current_registry_path).read_text(encoding="utf-8")
    )

    allowed_transitions = {
        "DEVELOPMENT": {"DEVELOPMENT", "UNDER_REVIEW"},
        "UNDER_REVIEW": {
            "UNDER_REVIEW",
            "DEVELOPMENT",
            "APPROVED",
        },
        "APPROVED": {"APPROVED", "RETIRED"},
        "RETIRED": {"RETIRED"},
    }

    current_homes = {
        (home.get("test_home_id"), home.get("test_home_version")): home
        for home in current["reference_homes"]
        if isinstance(home, dict)
    }

    for previous_home in previous["reference_homes"]:
        if not isinstance(previous_home, dict):
            continue

        
        home_id = previous_home.get("test_home_id")
        version = previous_home.get("test_home_version")
        key = (home_id, version)

        current_home = current_homes.get(key)

        if current_home is None:
            errors.append(
                f"{home_id}/{version}: Approved version cannot be removed"
            )
            continue

        previous_status = previous_home.get("status")
        current_status = current_home.get("status")

        if current_status not in allowed_transitions.get(
            previous_status, set()
        ):
            errors.append(
                f"{home_id}/{version}: Invalid lifecycle transition "
                f"from {previous_status} to {current_status}"
            )

        # Apply immutability protections only to versions
        # that were already approved or retired.
        if previous_status not in ("APPROVED", "RETIRED"):
            continue

        # Retirement is permitted, but approved metadata is preserved.
        permitted_statuses = {"APPROVED", "RETIRED"}

        if current_home.get("status") not in permitted_statuses:
            errors.append(
                f"{home_id}/{version}: Approved version cannot "
                "return to development or review"
            )

        for field in (
            "reference_files",
            "approval",
            "test_home_version",
            "test_home_id",
        ):
            if current_home.get(field) != previous_home.get(field):
                errors.append(
                    f"{home_id}/{version}: Approved {field} "
                    "cannot be modified"
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
