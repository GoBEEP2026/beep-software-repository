import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def local_name(tag):
    """Remove the XML namespace from an element name."""
    return tag.split("}")[-1]


def find_values(root, element_name):
    """Find values for matching XML element names."""
    values = []

    for element in root.iter():
        if local_name(element.tag) == element_name:
            if element.text and element.text.strip():
                values.append(element.text.strip())

    return values


def parse_hpxml(file_path):
    """Extract selected building characteristics from HPXML."""

    tree = ET.parse(file_path)
    root = tree.getroot()

    fields = {
        "conditioned_floor_area": "ConditionedFloorArea",
        "conditioned_volume": "ConditionedBuildingVolume",
        "number_of_bedrooms": "NumberofBedrooms",
        "wall_assembly_r_value": "AssemblyEffectiveRValue",
        "insulation_r_value": "NominalRValue",
        "window_u_factor": "UFactor",
        "window_shgc": "SHGC",
        "heating_efficiency_afue": "AnnualFuelUtilizationEfficiency",
        "cooling_efficiency_seer": "SeasonalEnergyEfficiencyRatio",
    }

    results = {}

    for field_name, xml_element in fields.items():
        results[field_name] = find_values(root, xml_element)

    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python parser.py filename.xml")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    try:
        results = parse_hpxml(file_path)
        print(json.dumps(results, indent=2))

    except ET.ParseError as error:
        print(f"Invalid XML: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
