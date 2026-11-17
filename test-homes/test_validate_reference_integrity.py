import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parent
    / "validate_reference_integrity.py"
)

spec = importlib.util.spec_from_file_location(
    "validate_reference_integrity",
    MODULE_PATH
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

validate_reference_integrity = module.validate_reference_integrity


class TestReferenceIntegrity(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

        self.xml_path = self.folder / "sample-home.xml"
        self.xml_path.write_text(
            "<HPXML><Building/></HPXML>",
            encoding="utf-8"
        )

        self.registry_path = (
            self.folder / "reference-home-registry.json"
        )

        self.registry = {
            "registry_version": "1.1.0",
            "registry_status": "DEVELOPMENT",
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-001",
                    "test_home_version": "1.0.0",
                    "status": "DEVELOPMENT",
                    "reference_files": [
                        {
                            "filename": "sample-home.xml",
                            "sha256": self.calculate_hash()
                        }
                    ]
                }
            ]
        }

        self.save_registry()

    def tearDown(self):
        self.temp_dir.cleanup()

    def calculate_hash(self):
        return hashlib.sha256(
            self.xml_path.read_bytes()
        ).hexdigest()

    def save_registry(self):
        self.registry_path.write_text(
            json.dumps(self.registry, indent=2),
            encoding="utf-8"
        )

    def get_errors(self):
        return validate_reference_integrity(
            self.registry_path
        )

    def test_valid_reference_file(self):
        self.assertEqual(self.get_errors(), [])

    def test_modified_reference_file_rejected(self):
        self.xml_path.write_text(
            "<HPXML><Building changed='true'/></HPXML>",
            encoding="utf-8"
        )

        errors = self.get_errors()

        self.assertTrue(
            any("SHA-256 mismatch" in e for e in errors)
        )

    def test_missing_reference_file_rejected(self):
        self.xml_path.unlink()

        errors = self.get_errors()

        self.assertTrue(
            any("Missing file" in e for e in errors)
        )

    def test_invalid_checksum_rejected(self):
        self.registry["reference_homes"][0][
            "reference_files"
        ][0]["sha256"] = "INVALID_HASH"

        self.save_registry()

        errors = self.get_errors()

        self.assertTrue(
            any("Invalid or missing SHA-256" in e for e in errors)
        )

    def test_duplicate_reference_file_rejected(self):
        entry = self.registry["reference_homes"][0][
            "reference_files"
        ][0].copy()

        self.registry["reference_homes"][0][
            "reference_files"
        ].append(entry)

        self.save_registry()

        errors = self.get_errors()

        self.assertTrue(
            any("Duplicate file" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
