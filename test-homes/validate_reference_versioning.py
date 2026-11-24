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

def parse_version(version):
    """Convert a valid semantic version into integers."""

    if not is_valid_version(version):
        raise ValueError(f"Invalid semantic version: {version!r}")

    return tuple(int(part) for part in version.split("."))


def get_version_change_type(parent_version, new_version):
    """Identify a valid major, minor, or patch increment."""

    if not is_valid_version(parent_version):
        return None

    if not is_valid_version(new_version):
        return None

    major, minor, patch = parse_version(parent_version)
    proposed = parse_version(new_version)

    if proposed == (major + 1, 0, 0):
        return "MAJOR"

    if proposed == (major, minor + 1, 0):
        return "MINOR"

    if proposed == (major, minor, patch + 1):
        return "PATCH"

    return None


def validate_parent_versions(homes):
    """Validate reference-home parent-version relationships."""

    errors = []
    registered_versions = set()

    for home in homes:
        if not isinstance(home, dict):
            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")

        if (
            isinstance(home_id, str)
            and home_id.strip()
            and is_valid_version(version)
        ):
            registered_versions.add((home_id, version))

    for home in homes:
        if not isinstance(home, dict):
            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")
        parent = home.get("parent_version")

        if not isinstance(home_id, str) or not home_id.strip():
            continue

        if not is_valid_version(version):
            continue

        if version == "1.0.0":
            if parent is not None:
                errors.append(
                    f"{home_id}/{version}: Initial version "
                    "must not have a parent version"
                )
            continue

        if not is_valid_version(parent):
            errors.append(
                f"{home_id}/{version}: Missing or invalid "
                "parent version"
            )
            continue

        if (home_id, parent) not in registered_versions:
            errors.append(
                f"{home_id}/{version}: Parent version "
                f"{parent} does not exist for this home"
            )
            continue

        if get_version_change_type(parent, version) is None:
            errors.append(
                f"{home_id}/{version}: Invalid version "
                f"progression from parent {parent}"
            )

    return errors





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

    # Require an initial version of 1.0.0 for each home.
    home_versions = {}

    for home in homes:
        if not isinstance(home, dict):
            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")

        if not isinstance(home_id, str) or not home_id.strip():
            errors.append(
                "Reference home has a missing or invalid ID"
            )
            continue

        if not is_valid_version(version):
            continue

        home_versions.setdefault(home_id, set()).add(version)

    
    for home_id, versions in home_versions.items():
        if "1.0.0" not in versions:
            errors.append(
                f"{home_id}: Initial reference home version "
                "must be 1.0.0"
            )

    # Validate parent-version relationships.
    errors.extend(validate_parent_versions(homes))


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
