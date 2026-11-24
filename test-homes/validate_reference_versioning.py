import json
import re
import sys
from datetime import date
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



def validate_linear_version_history(homes):
    """Require a single sequential history for each home."""

    errors = []
    grouped_homes = {}

    for home in homes:
        if not isinstance(home, dict):
            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")

        if not isinstance(home_id, str) or not home_id.strip():
            continue

        if not is_valid_version(version):
            continue

        grouped_homes.setdefault(home_id, []).append(home)

    for home_id, records in grouped_homes.items():
        seen_versions = set()

        for record in records:
            version = record["test_home_version"]

            if version in seen_versions:
                errors.append(
                    f"{home_id}/{version}: Duplicate "
                    "reference home version"
                )

            seen_versions.add(version)

        try:
            ordered_records = sorted(
                records,
                key=lambda record: parse_version(
                    record["test_home_version"]
                ),
            )
        except ValueError:
            errors.append(
                f"{home_id}: Unable to order semantic versions"
            )
            continue

        for index in range(1, len(ordered_records)):
            previous = ordered_records[index - 1]
            current = ordered_records[index]

            previous_version = previous["test_home_version"]
            current_version = current["test_home_version"]
            parent = current.get("parent_version")

            if parent != previous_version:
                errors.append(
                    f"{home_id}/{current_version}: "
                    "Parent must be the immediate predecessor "
                    f"{previous_version}"
                )

            if get_version_change_type(
                previous_version,
                current_version,
            ) is None:
                errors.append(
                    f"{home_id}/{current_version}: "
                    "Invalid sequential version increment "
                    f"from {previous_version}"
                )

    return errors



def validate_historical_versions(previous_homes, current_homes):
    """Preserve previously registered reference-home versions."""

    errors = []

    def build_version_index(homes, registry_name):
        index = {}

        if not isinstance(homes, list):
            errors.append(
                f"{registry_name}: Invalid reference homes array"
            )
            return index

        for home in homes:
            if not isinstance(home, dict):
                errors.append(
                    f"{registry_name}: Malformed reference home"
                )
                continue

            home_id = home.get("test_home_id")
            version = home.get("test_home_version")

            if (
                not isinstance(home_id, str)
                or not home_id.strip()
                or not is_valid_version(version)
            ):
                errors.append(
                    f"{registry_name}: Invalid reference home identity"
                )
                continue

            key = (home_id, version)

            if key in index:
                errors.append(
                    f"{registry_name}: Duplicate version "
                    f"{home_id}/{version}"
                )
                continue

            index[key] = home

        return index

    previous_index = build_version_index(
        previous_homes,
        "Previous registry",
    )

    current_index = build_version_index(
        current_homes,
        "Current registry",
    )

    for key, previous_home in previous_index.items():
        home_id, version = key

        if key not in current_index:
            errors.append(
                f"{home_id}/{version}: Previously registered "
                "version cannot be deleted or renumbered"
            )
            continue

        current_home = current_index[key]

        previous_parent = previous_home.get("parent_version")
        current_parent = current_home.get("parent_version")

        if previous_parent != current_parent:
            errors.append(
                f"{home_id}/{version}: Historical parent "
                "version cannot be changed"
            )

    return errors



def validate_change_documentation(homes):
    """Validate required reference-home change documentation."""

    errors = []

    if not isinstance(homes, list):
        return ["Invalid reference homes array"]

    required_text_fields = (
        "description",
        "change_reason",
        "anticipated_impact",
    )

    for home in homes:
        if not isinstance(home, dict):
            errors.append("Malformed reference home")
            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")
        parent = home.get("parent_version")

        if (
            not isinstance(home_id, str)
            or not home_id.strip()
            or not is_valid_version(version)
        ):
            errors.append("Invalid reference home identity")
            continue

        label = f"{home_id}/{version}"

        history = home.get("version_history")

        if not isinstance(history, list) or not history:
            errors.append(
                f"{label}: Missing or invalid version history"
            )
            continue

        if any(
            not isinstance(entry, dict)
            for entry in history
        ):
            errors.append(
                f"{label}: Malformed version history entry"
            )
            continue

        matching_entries = [
            entry for entry in history
            if entry.get("version") == version
        ]

        if len(matching_entries) != 1:
            errors.append(
                f"{label}: Exactly one matching version "
                "history entry is required"
            )
            continue

        entry = matching_entries[0]

        if version == "1.0.0":
            expected_change_type = "INITIAL"
        else:
            expected_change_type = get_version_change_type(
                parent,
                version,
            )

        if (
            expected_change_type is None
            or entry.get("change_type") != expected_change_type
        ):
            errors.append(
                f"{label}: Change classification does not "
                "match semantic version progression"
            )

        for field in required_text_fields:
            value = entry.get(field)

            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"{label}: Missing or invalid {field}"
                )

        components = entry.get("affected_components")

        if (
            not isinstance(components, list)
            or not components
            or any(
                not isinstance(component, str)
                or not component.strip()
                for component in components
            )
        ):
            errors.append(
                f"{label}: Missing or invalid affected_components"
            )

        change_date = entry.get("change_date")

        legacy_initial_record = (
            home_id == "BEEP-HOME-001"
            and version == "1.0.0"
            and entry.get("change_type") == "INITIAL"
            and "change_date" in entry
            and change_date is None
        )

        if not legacy_initial_record:
            if (
                not isinstance(change_date, str)
                or re.fullmatch(
                    r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
                    change_date,
                ) is None
            ):
                errors.append(
                    f"{label}: Invalid change_date. "
                    "Expected YYYY-MM-DD format"
                )
            else:
                try:
                    date.fromisoformat(change_date)
                except ValueError:
                    errors.append(
                        f"{label}: Invalid change_date "
                        "calendar date"
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

    # Validate linear version history.
    errors.extend(validate_linear_version_history(homes))

    return errors


def validate_historical_registries(
    previous_registry_path,
    current_registry_path,
):
    """Compare previous and proposed reference registries."""

    errors = []
    registries = []

    for registry_name, registry_path in (
        ("Previous registry", previous_registry_path),
        ("Current registry", current_registry_path),
    ):
        try:
            registry = json.loads(
                Path(registry_path).read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(
                f"{registry_name}: Unable to read registry: {exc}"
            )
            continue

        if not isinstance(registry, dict):
            errors.append(
                f"{registry_name}: Registry must be a JSON object"
            )
            continue

        homes = registry.get("reference_homes")

        if not isinstance(homes, list):
            errors.append(
                f"{registry_name}: Missing or invalid "
                "reference_homes array"
            )
            continue

        registries.append(homes)

    if errors:
        return errors

    errors.extend(
        validate_historical_versions(
            registries[0],
            registries[1],
        )
    )

    return errors





if __name__ == "__main__":
    if len(sys.argv) == 2:
        validation_errors = validate_reference_versioning(
            sys.argv[1]
        )

        validation_name = "REFERENCE HOME VERSION"

    elif len(sys.argv) == 4 and sys.argv[1] == "--historical":
        previous_registry = sys.argv[2]
        current_registry = sys.argv[3]

        validation_errors = validate_reference_versioning(
            current_registry
        )

        validation_errors.extend(
            validate_historical_registries(
                previous_registry,
                current_registry,
            )
        )

        validation_name = "HISTORICAL REFERENCE HOME VERSION"

    else:
        print("Usage:")
        print(
            "  python validate_reference_versioning.py "
            "<reference-registry>"
        )
        print(
            "  python validate_reference_versioning.py "
            "--historical <previous-registry> "
            "<current-registry>"
        )
        sys.exit(2)

    if validation_errors:
        print(f"{validation_name} VALIDATION FAILED")

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print(f"{validation_name} VALIDATION PASSED")
    sys.exit(0)
