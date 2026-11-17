import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def local_name(tag):
    return tag.split("}")[-1]


def child(element, name):
    """Find a direct child by local XML name."""
    for item in element:
        if local_name(item.tag) == name:
            return item
    return None


def value(element, path):
    """Read a nested element value."""
    current = element

    for name in path.split("/"):
        if current is None:
            return None
        current = child(current, name)

    if current is not None and current.text:
        return current.text.strip()

    return None


def elements(root, name):
    """Find elements matching an XML name."""
    return [
        item for item in root.iter()
        if local_name(item.tag) == name
    ]



def extract_components(root, name, fields):
    """Extract individual components with their own properties."""
    results = []

    for item in elements(root, name):
        identifier = child(item, "SystemIdentifier")

        record = {
            "id": identifier.get("id") if identifier is not None else None
        }

        for field, path in fields.items():
            record[field] = value(item, path)

        results.append(record)

    return results



def parse_hpxml(file_path):
    root = ET.parse(file_path).getroot()

    return {
        "building": {
            "conditioned_floor_area": [
                value(x, "ConditionedFloorArea")
                for x in elements(root, "BuildingConstruction")
            ],
            "conditioned_volume": [
                value(x, "ConditionedBuildingVolume")
                for x in elements(root, "BuildingConstruction")
            ],
        },
        "walls": extract_components(root, "Wall", {
            "area": "Area",
            "azimuth": "Azimuth",
            "assembly_r_value": "Insulation/AssemblyEffectiveRValue",
            "nominal_r_value": "Insulation/NominalRValue",
        }),
        "windows": extract_components(root, "Window", {
            "area": "Area",
            "u_factor": "UFactor",
            "shgc": "SHGC",
        }),
        "roofs": extract_components(root, "Roof", {
            "area": "Area",
            "insulation_r_value": "Insulation/AssemblyEffectiveRValue",
        }),
        "heating_systems": extract_components(root, "HeatingSystem", {
            "type": "HeatingSystemType",
            "capacity": "HeatingCapacity",
        }),
        "cooling_systems": extract_components(root, "CoolingSystem", {
            "type": "CoolingSystemType",
            "capacity": "CoolingCapacity",
        }),
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python advanced_parser.py filename.xml")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    try:
        result = parse_hpxml(file_path)
        print(json.dumps(result, indent=2))
    except (ET.ParseError, OSError) as error:
        print(f"Unable to parse HPXML: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
