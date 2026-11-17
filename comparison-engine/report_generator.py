import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from integrated_compare import compare_files


def generate_report(file_a, file_b, output_file):
    comparison = compare_files(file_a, file_b)
    walls = comparison["walls"]

    report = {
        "report_schema_version": "1.0",
        "repository": "B.E.E.P. Software Repository",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "reference_home": "BEEP-HOME-001",
        "comparison_type": "HPXML_INPUT",
        "vendor_a": {
            "file": Path(file_a).name
        },
        "vendor_b": {
            "file": Path(file_b).name
        },
        "summary": {
            "matched_walls": walls["matched"],
            "input_differences": len(
                walls["differences"]
            ),
            "ambiguous_matches": len(
                walls["ambiguous"]
            ),
            "unmatched_vendor_a": len(
                walls["unmatched_a"]
            ),
            "unmatched_vendor_b": len(
                walls["unmatched_b"]
            )
        },
        "wall_comparison": walls,
        "building_comparison": {
            "vendor_a": comparison["building_a"],
            "vendor_b": comparison["building_b"]
        },
        "review_status": "UNREVIEWED"
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    output_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    return report


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python report_generator.py "
            "vendor_a.xml vendor_b.xml report.json"
        )
        sys.exit(1)

    report = generate_report(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3]
    )

    print("Report generated successfully.")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
