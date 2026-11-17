import importlib.util
import json
import sys
from pathlib import Path


def load_parser():
    parser_path = (
        Path(__file__).resolve().parent.parent
        / "hpxml-parser"
        / "advanced_parser.py"
    )

    spec = importlib.util.spec_from_file_location(
        "advanced_parser", parser_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def flatten(data, prefix=""):
    """Convert nested dictionaries and lists into comparable fields."""
    results = {}

    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            results.update(flatten(value, path))

    elif isinstance(data, list):
        for index, value in enumerate(data):
            path = f"{prefix}[{index}]"
            results.update(flatten(value, path))

    else:
        results[prefix] = data

    return results


def compare_files(file_a, file_b):
    parser = load_parser()

    data_a = flatten(parser.parse_hpxml(file_a))
    data_b = flatten(parser.parse_hpxml(file_b))

    differences = []

    for field in sorted(set(data_a) | set(data_b)):
        value_a = data_a.get(field)
        value_b = data_b.get(field)

        if value_a != value_b:
            differences.append({
                "field": field,
                "vendor_a": value_a,
                "vendor_b": value_b,
                "status": "DIFFERENCE"
            })

    return {
        "total_fields": len(set(data_a) | set(data_b)),
        "differences_found": len(differences),
        "differences": differences
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: python compare.py vendor_a.xml vendor_b.xml")
        sys.exit(1)

    result = compare_files(sys.argv[1], sys.argv[2])

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
