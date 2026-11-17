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




    return errors


def validate_component_mappings(document, xml_path):
    errors = []

    mappings = document.get("component_mappings")
    if not isinstance(mappings, list):
        return ["Missing or invalid component_mappings"]

    tree = ET.parse(xml_path)
    root = tree.getroot()

    walls = {}

    for wall in root.findall(".//{*}Wall"):
        identifier = wall.find("{*}SystemIdentifier")

        if identifier is None:
            continue

        wall_id = identifier.get("id")
        if not wall_id:
            continue

        walls.setdefault(wall_id, []).append(wall)

    reference_ids = set()
    vendor_ids = set()

    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            errors.append(f"Invalid component mapping at index {index}")
            continue

        reference_id = mapping.get("reference_component_id")
        vendor_id = mapping.get("vendor_component_id")
        component_type = mapping.get("component_type")

        if not isinstance(reference_id, str) or not reference_id:
            errors.append(f"Missing reference component ID at index {index}")
            continue

        if not isinstance(vendor_id, str) or not vendor_id:
            errors.append(f"Missing vendor component ID at index {index}")
            continue

        if reference_id in reference_ids:
            errors.append(f"Duplicate reference component ID: {reference_id}")

        if vendor_id in vendor_ids:
            errors.append(f"Duplicate vendor component ID: {vendor_id}")

        reference_ids.add(reference_id)
        vendor_ids.add(vendor_id)

        if component_type != "Wall":
            errors.append(
                f"Unsupported component type: {component_type}"
            )
            continue

        matches = walls.get(vendor_id, [])

        if len(matches) != 1:
            errors.append(
                f"Expected one HPXML wall for {vendor_id}; "
                f"found {len(matches)}"
            )
            continue

        wall = matches[0]
        properties = mapping.get("properties")

        if not isinstance(properties, dict):
            errors.append(f"Missing mapping properties: {vendor_id}")
            continue

        for xml_field, map_field in [
            ("Area", "area_ft2"),
            ("Azimuth", "azimuth_degrees"),
        ]:
            xml_element = wall.find(f"{{*}}{xml_field}")
            mapped_value = properties.get(map_field)

            try:
                xml_value = float(xml_element.text)
                mapped_value = float(mapped_value)

                if not (
                    math.isfinite(xml_value)
                    and math.isfinite(mapped_value)
                    and math.isclose(
                        xml_value,
                        mapped_value,
                        rel_tol=1e-6,
                        abs_tol=0.01
                    )
                ):
                    errors.append(
                        f"Component geometry mismatch: "
                        f"{vendor_id} {map_field}"
                    )

            except (TypeError, ValueError, AttributeError):
                errors.append(
                    f"Invalid component geometry: "
                    f"{vendor_id} {map_field}"
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

    
    # Validate energy modeling results
    errors.extend(
        validate_energy_results(documents["results.json"])
    )

    # Validate component mappings against submitted HPXML
    errors.extend(
        validate_component_mappings(
            documents["component-map.json"],
            folder / "building.xml"
        )
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
    print("Energy results validation completed.")
    print("Schema, component, and hash checks pending.")
