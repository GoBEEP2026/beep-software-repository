import json
import tempfile
from pathlib import Path

from report_generator import generate_report


def run_tests():
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "comparison.json"

        report = generate_report(
            "test-homes/sample-home.xml",
            "test-homes/sample-home-vendor-b.xml",
            output
        )

        assert output.exists()

        saved = json.loads(
            output.read_text(encoding="utf-8")
        )

        assert saved["report_schema_version"] == "1.0"
        assert saved["reference_home"] == "BEEP-HOME-001"
        assert saved["review_status"] == "UNREVIEWED"
        assert "summary" in saved
        assert "wall_comparison" in saved

        assert saved["summary"] == report["summary"]

        print("PASS: JSON comparison report created.")
        print("PASS: Report structure validated.")
        print("PASS: Report remains unreviewed.")


if __name__ == "__main__":
    run_tests()
