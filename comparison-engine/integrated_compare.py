import importlib.util
import json
import sys
from pathlib import Path

from component_matcher import match_components


def load_parser():
    path = (
        Path(__file__).resolve().parent.parent
        / "hpxml-parser"
        / "advanced_parser.py"
    )

    spec = importlib.util.spec_from_file_location(
        "advanced_parser", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare_walls(walls_a, walls_b):
    matching = match_components(walls_a, walls_b)
    differences = []

    for match in matching["matches"]:
        a = walls_a[match["vendor_a_index"]]
        b = walls_b[match["vendor_b_index"]]

        for field in ("nominal_r_value", "assembly_r_value"):
            if a.get(field) != b.get(field):
                differences.append({
                    "component_a": match["vendor_a_id"],
                    "component_b": match["vendor_b_id"],
                    "field": field,
                    "value_a": a.get(field),
                    "value_b": b.get(field)
                })

    return {
        "matched": len(matching["matches"]),
        "differences": differences,
        "ambiguous": matching["ambiguous"],
        "unmatched_a": matching["unmatched_a"],
        "unmatched_b": matching["unmatched_b"]
    }


def compare_files(file_a, file_b):
    parser = load_parser()

    data_a = parser.parse_hpxml(file_a)
    data_b = parser.parse_hpxml(file_b)

    return {
        "building_a": data_a["building"],
        "building_b": data_b["building"],
        "walls": compare_walls(
            data_a["walls"],
            data_b["walls"]
        )
    }


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python integrated_compare.py "
            "vendor_a.xml vendor_b.xml"
        )
        sys.exit(1)

    result = compare_files(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
