import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

FOLDER = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location(
    "validate_submission",
    FOLDER / "validate_submission.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

validate_submission = module.validate_submission


class TestVendorSubmissionValidator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

        for filename in [
            "submission.json",
            "building.xml",
            "results.json",
            "component-map.json",
            "manifest.json",
        ]:
            shutil.copy2(FOLDER / filename, self.folder / filename)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_submission(self):
        errors = validate_submission(self.folder)
        self.assertEqual(errors, [])

    def test_missing_file(self):
        (self.folder / "results.json").unlink()

        errors = validate_submission(self.folder)

        self.assertTrue(
            any("Missing required file" in e for e in errors)
        )

    def test_invalid_json(self):
        (self.folder / "results.json").write_text(
            "{invalid json",
            encoding="utf-8"
        )

        errors = validate_submission(self.folder)

        self.assertTrue(
            any("Invalid JSON" in e for e in errors)
        )

    def test_mismatched_submission_id(self):
        path = self.folder / "results.json"

        data = json.loads(path.read_text(encoding="utf-8"))
        data["submission_id"] = "WRONG-ID"

        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

        errors = validate_submission(self.folder)

        self.assertTrue(
            any("Mismatched submission_id" in e for e in errors)
        )

    def test_mismatched_test_home_id(self):
        path = self.folder / "results.json"

        data = json.loads(path.read_text(encoding="utf-8"))
        data["test_home_id"] = "WRONG-HOME"

        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

        errors = validate_submission(self.folder)

        self.assertTrue(
            any("Mismatched test_home_id" in e for e in errors)
        )

    def test_invalid_xml(self):
        (self.folder / "building.xml").write_text(
            "<HPXML><Building>",
            encoding="utf-8"
        )

        errors = validate_submission(self.folder)

        self.assertTrue(
            any("Invalid XML" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
