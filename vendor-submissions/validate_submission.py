from jsonschema import Draft202012Validator
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import importlib.util


# Locate trusted repository governance validators.
REPOSITORY_ROOT = (
    Path(__file__).resolve().parent.parent
)

TEST_HOMES_DIRECTORY = (
    REPOSITORY_ROOT / "test-homes"
)

if str(TEST_HOMES_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(TEST_HOMES_DIRECTORY),
    )

from validate_production_governance import (
    validate_production_governance,
)


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


def validate_file_integrity(manifest, folder):
    errors = []
    folder = Path(folder)

    entries = manifest.get("files")

    if not isinstance(entries, list):
        return ["Invalid manifest file inventory"]

    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("Invalid manifest file entry")
            continue

        filename = entry.get("filename")
        expected_hash = entry.get("sha256")

        if not isinstance(filename, str) or not filename:
            errors.append("Invalid manifest filename")
            continue

        if filename not in REQUIRED_FILES or filename == "manifest.json":
            errors.append(f"Unexpected manifest filename: {filename}")
            continue

        file_path = folder / filename

        if not file_path.is_file():
            errors.append(f"Missing file for checksum: {filename}")
            continue

        # Development samples may not yet have generated hashes.
        if expected_hash is None:
            if manifest.get("manifest_status") != "DEVELOPMENT_SAMPLE":
                errors.append(f"Missing SHA-256 checksum: {filename}")
            continue

        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(c not in "0123456789abcdef" for c in expected_hash)
        ):
            errors.append(f"Invalid SHA-256 checksum: {filename}")
            continue

        actual_hash = hashlib.sha256(
            file_path.read_bytes()
        ).hexdigest()

        if actual_hash != expected_hash:
            errors.append(f"SHA-256 checksum mismatch: {filename}")

    return errors



def validate_json_schemas(documents, folder):
  
    errors = []

    # Locate schemas relative to this validator script,
    # not the temporary vendor submission directory.
    schema_folder = (
        Path(__file__).resolve().parent.parent / "schemas"
    )


    schema_files = {
        "submission.json": "submission.schema.json",
        "results.json": "results.schema.json",
        "component-map.json": "component-map.schema.json",
        "manifest.json": "manifest.schema.json",
    }

    for filename, schema_filename in schema_files.items():
        schema_path = schema_folder / schema_filename

        try:
            with schema_path.open(encoding="utf-8") as f:
                schema = json.load(f)

            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)

            validation_errors = sorted(
                validator.iter_errors(documents[filename]),
                key=lambda error: str(list(error.absolute_path))
            )

            for error in validation_errors:
                location = ".".join(
                    str(part) for part in error.absolute_path
                ) or "root"

                errors.append(
                    f"Schema validation error in "
                    f"{filename} at {location}: {error.message}"
                )

        except (OSError, ValueError) as exc:
            errors.append(
                f"Unable to load schema {schema_filename}: {exc}"
            )

    return errors



def validate_reference_approval_metadata(
    registry_path,
    audit_path=None,
):

    """
    Run the B.E.E.P. reference-home approval validator
    against the selected registry.
    """

    validator_path = (
        Path(__file__).resolve().parent.parent
        / "test-homes"
        / "validate_reference_approval.py"
    )

    spec = importlib.util.spec_from_file_location(
        "beep_reference_approval",
        validator_path
    )

    if spec is None or spec.loader is None:
        return ["Unable to load reference approval validator"]

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

   
    return module.validate_reference_approval(
        registry_path=registry_path,
        audit_path=audit_path,
    )




def validate_reference_approval_records(
    registry_path,
    approvals_directory=None
):
    """
    Verify approval documents for production
    reference homes.
    """

    repository_root = Path(__file__).resolve().parent.parent

    validator_path = (
        repository_root
        / "test-homes"
        / "validate_approval_records.py"
    )

    spec = importlib.util.spec_from_file_location(
        "validate_approval_records",
        validator_path
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module.validate_approval_records(
        registry_path=registry_path,
        approvals_directory=approvals_directory
    )




def validate_reference_home(
    documents, production=False, registry_path=None
):
    errors = []

    if registry_path is None:
        registry_path = (
            Path(__file__).resolve().parent.parent
            / "test-homes"
            / "reference-home-registry.json"
        )

    registry_path = Path(registry_path)


    try:
        with registry_path.open(encoding="utf-8") as f:
            registry = json.load(f)
    except (OSError, ValueError) as exc:
        return [f"Unable to load reference home registry: {exc}"]

    submission = documents["submission.json"]
    test = submission.get("test", {})

    if not isinstance(test, dict):
        return ["Invalid submission test metadata"]

    home_id = test.get("test_home_id")
    home_version = test.get("test_home_version")
    compliance_path = test.get("compliance_path")

    homes = registry.get("reference_homes")

    if not isinstance(homes, list):
        return ["Invalid reference home registry"]

    matches = [
        home for home in homes
        if isinstance(home, dict)
        and home.get("test_home_id") == home_id
        and home.get("test_home_version") == home_version
    ]

    if len(matches) != 1:
        errors.append(
            f"Reference home/version not uniquely registered: "
            f"{home_id} / {home_version}"
        )
        return errors

    home = matches[0]

    approved_paths = home.get("approved_compliance_paths", [])

    if (
        not isinstance(approved_paths, list)
        or compliance_path not in approved_paths
    ):
        errors.append(
            f"Compliance path not authorized for reference home: "
            f"{compliance_path}"
        )

    if production:
        if registry.get("registry_status") != "APPROVED":
            errors.append(
                "Production requires an approved reference home registry"
            )

        if home.get("status") != "APPROVED":
            errors.append(
                f"Reference home is not approved for production: {home_id}"
            )

  



    return errors




def validate_production_requirements(documents):
    errors = []

    submission = documents["submission.json"]
    results = documents["results.json"]
    manifest = documents["manifest.json"]

    # Production submissions cannot use sample results.
    if results.get("calculation_status") != "COMPLETED":
        errors.append(
            "Production submission requires COMPLETED calculation status"
        )

    # Software and engine versions must be identified.
    software = submission.get("software", {})

    if not isinstance(software, dict):
        errors.append("Invalid software metadata")
    else:
        for field in ["product_version", "engine_version"]:
            value = software.get(field)

            if (
                not isinstance(value, str)
                or not value.strip()
                or value.strip().lower() in [
                    "not-specified",
                    "unknown",
                    "n/a",
                    "tbd"
                ]
            ):
                errors.append(
                    f"Production submission requires valid {field}"
                )

    # Production manifests require generated checksums.
    if manifest.get("manifest_status") != "CHECKSUMS_GENERATED":
        errors.append(
            "Production submission requires generated SHA-256 checksums"
        )

    entries = manifest.get("files", [])

    if not isinstance(entries, list):
        errors.append("Invalid production manifest inventory")
    else:
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append("Invalid production manifest entry")
                continue

            if not isinstance(entry.get("sha256"), str):
                errors.append(
                    f"Missing production checksum: {entry.get('filename')}"
                )

    return errors




def validate_submission(
    folder,
    production=False,
    registry_path=None,
    approvals_directory=None,
    audit_path=None,
    identifier_registry_path=None,
):



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


 
    # Verify submission file integrity
    errors.extend(
        validate_file_integrity(
            documents["manifest.json"],
            folder
        )
    )

    # Validate all JSON files against formal schemas
    errors.extend(
        validate_json_schemas(documents, folder)
    )

    
    # Verify reference home identity, version, and approval.
    
    errors.extend(
        validate_reference_home(
            documents,
            production=production,
            registry_path=registry_path
        )
    )


    if production:
        errors.extend(
            validate_production_requirements(documents)
        )

    
    # Enforce centralized governance controls
    # for production submissions.
    if production:

        governance_inputs = (
            registry_path,
            audit_path,
            identifier_registry_path,
            approvals_directory,
        )

        # Governance inputs must use either all
        # authoritative defaults or a complete
        # isolated set of explicitly supplied paths.
        if (
            any(path is not None for path in governance_inputs)
            and not all(
                path is not None for path in governance_inputs
            )
        ):
            errors.append(
                "Production governance requires either "
                "all four explicit governance paths "
                "or all authoritative repository defaults"
            )

        else:

            errors.extend(
                validate_production_governance(
                    registry_path=registry_path,
                    audit_path=audit_path,
                    identifier_registry_path=(
                        identifier_registry_path
                    ),
                    approvals_directory=(
                        approvals_directory
                    ),
                )
            )

    return errors




if __name__ == "__main__":

    folder = (
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).parent
    )

    
    production_mode = "--production" in sys.argv[1:]

    errors = validate_submission(
        folder,
        production=production_mode
    )


    if errors:
        print("B.E.E.P. SUBMISSION VALIDATION FAILED")
        for error in errors:
            print(f"  ERROR: {error}")
        sys.exit(1)

    print("B.E.E.P. SUBMISSION VALIDATION PASSED")
    print("Structure, energy results, and component mappings checked.")
    print("File integrity checks completed.")
    print("Full schema validation and production controls pending.")
