import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_FILES = [
    "submission.json",
    "building.xml",
    "results.json",
    "component-map.json",
    "manifest.json",
]


def validate_energy_results(document):
    errors = []

    results = document.get("results")
    if not isinstance(results, dict):
        return ["Missing or invalid results object"]

    annual = results.get("annual_energy")
    if not isinstance(annual, dict):
        return ["Missing or invalid annual_energy object"]

    end_uses = [
        "heating_kwh",
        "cooling_kwh",
        "water_heating_kwh",
        "lighting_kwh",
        "appliances_kwh",
        "other_kwh",
    ]

    values = {}

    for field in ["total_site_kwh"] + end_uses:
        value = annual.get(field)

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            errors.append(
                f"Invalid or missing annual energy value: {field}"
            )
        else:
            values[field] = value

    if len(values) == len(end_uses) + 1:
        total = values["total_site_kwh"]
        calculated = sum(values[field] for field in end_uses)

        if not math.isclose(
            total, calculated, rel_tol=1e-6, abs_tol=0.01
        ):
            errors.append(
                f"Annual energy total mismatch: "
                f"reported={total}, calculated={calculated}"
            )

    eri = results.get("eri_score")
    if (
        isinstance(eri, bool)
        or not isinstance(eri, (int, float))
        or not math.isfinite(eri)
        or eri < 0
    ):
        errors.append("Invalid or missing eri_score")

    loads = results.get("design_loads")
    if not isinstance(loads, dict):
        errors.append("Missing or invalid design_loads")
    else:
        for field in ["heating_btuh", "cooling_btuh"]:
            value = loads.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                errors.append(
                    f"Invalid or missing design load: {field}"
                )

    # Validate energy modeling results
    errors.extend(
        validate_energy_results(documents["results.json"])
    )


    return errors



def validate_submission(folder):
    folder = Path(folder)
    errors = []

    # Check required files
    for filename in REQUIRED_FILES:
        if not (folder / filename).is_file():
            errors.append(f"Missing required file: {filename}")

    if errors:
        return errors

    # Load JSON files
    documents = {}
    for filename in REQUIRED_FILES:
        path = folder / filename

        if filename.endswith(".json"):
            try:
                with path.open(encoding="utf-8") as f:
                    documents[filename] = json.load(f)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"Invalid JSON in {filename}: {exc}")

    # Check XML syntax
    try:
        ET.parse(folder / "building.xml")
    except (ET.ParseError, OSError) as exc:
        errors.append(f"Invalid XML in building.xml: {exc}")

    if errors:
        return errors

    
    # Compare submission IDs and test home IDs
    for field in ("submission_id", "test_home_id"):
        values = {}

        for filename, document in documents.items():
            if filename == "submission.json" and field == "test_home_id":
                test_metadata = document.get("test", {})
                value = (
                    test_metadata.get("test_home_id")
                    if isinstance(test_metadata, dict)
                    else None
                )
            else:
                value = document.get(field)

            values[filename] = value


        if any(not isinstance(value, str) or not value.strip()
               for value in values.values()):
            errors.append(f"Missing or invalid {field}: {values}")
        elif len(set(values.values())) != 1:
            errors.append(f"Mismatched {field}: {values}")

    # Check that the manifest lists all payload files
    manifest = documents["manifest.json"]
    manifest_files = manifest.get("files", [])

    if not isinstance(manifest_files, list):
        errors.append("Manifest files must be a list")
    else:
        listed = [
            entry.get("filename")
            for entry in manifest_files
            if isinstance(entry, dict)
        ]

        for filename in REQUIRED_FILES:
            if filename == "manifest.json":
                continue

            if listed.count(filename) != 1:
                errors.append(
                    f"Manifest must list {filename} exactly once"
                )

    return errors


if __name__ == "__main__":
    folder = (
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).parent
    )

    errors = validate_submission(folder)

    if errors:
        print("B.E.E.P. SUBMISSION VALIDATION FAILED")
        for error in errors:
            print(f"  ERROR: {error}")
        sys.exit(1)

    print("B.E.E.P. SUBMISSION VALIDATION PASSED")
    print("Required files, JSON/XML syntax, and IDs verified.")
    print("Schema, energy, component, and hash checks pending.")
