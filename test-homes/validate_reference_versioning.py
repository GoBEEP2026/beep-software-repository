import json
import re
import sys
from pathlib import Path


VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
)


def is_valid_version(version):
    """Validate the MAJOR.MINOR.PATCH version format."""

    return (
        isinstance(version, str)
        and VERSION_PATTERN.fullmatch(version) is not None
    )


def validate_reference_versioning(registry_path):
    """Validate reference-home version identifiers."""

    errors = []

    try:
        registry = json.loads(
            Path(registry_path).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"Unable to read reference registry: {exc}"]

    if not isinstance(registry, dict):
        return ["Reference registry must be a JSON object"]

    homes = registry.get("reference_homes")

    if not isinstance(homes, list):
        return ["Registry must contain a reference_homes array"]

    for index, home in enumerate(homes):
        if not isinstance(home, dict):
            errors.append(
                f"Malformed reference home at index {index}"
            )
            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")

        if not is_valid_version(version):
            errors.append(
                f"{home_id}: Invalid semantic version: {version!r}. "
                "Expected MAJOR.MINOR.PATCH format."
            )

    return errors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python validate_reference_versioning.py "
            "<reference-registry>"
        )
        sys.exit(2)

    validation_errors = validate_reference_versioning(sys.argv[1])

    if validation_errors:
        print("REFERENCE HOME VERSION VALIDATION FAILED")

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print("REFERENCE HOME VERSION VALIDATION PASSED")
    sys.exit(0)
