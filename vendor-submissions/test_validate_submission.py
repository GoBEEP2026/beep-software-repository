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


    def update_results(self, change):
        path = self.folder / "results.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
        return validate_submission(self.folder)

    def test_incorrect_energy_total(self):
        def change(data):
            data["results"]["annual_energy"]["total_site_kwh"] = 15000

        errors = self.update_results(change)

        self.assertTrue(
            any("Annual energy total mismatch" in e for e in errors)
        )

    def test_negative_energy_value(self):
        def change(data):
            data["results"]["annual_energy"]["heating_kwh"] = -100

        errors = self.update_results(change)

        self.assertTrue(
            any("Invalid or missing annual energy value" in e
                for e in errors)
        )

    def test_missing_energy_end_use(self):
        def change(data):
            del data["results"]["annual_energy"]["cooling_kwh"]

        errors = self.update_results(change)

        self.assertTrue(
            any("cooling_kwh" in e for e in errors)
        )

    def test_invalid_eri_score(self):
        def change(data):
            data["results"]["eri_score"] = "invalid"

        errors = self.update_results(change)

        self.assertTrue(
            any("Invalid or missing eri_score" in e for e in errors)
        )

    def test_missing_design_load(self):
        def change(data):
            del data["results"]["design_loads"]["heating_btuh"]

        errors = self.update_results(change)

        self.assertTrue(
            any("heating_btuh" in e for e in errors)
        )
       
    def update_component_map(self, change):
        path = self.folder / "component-map.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
        return validate_submission(self.folder)

    def test_nonexistent_wall_id(self):
        def change(data):
            data["component_mappings"][0][
                "vendor_component_id"
            ] = "WALL-DOES-NOT-EXIST"

        errors = self.update_component_map(change)

        self.assertTrue(
            any("Expected one HPXML wall" in e for e in errors)
        )

    def test_duplicate_wall_mapping(self):
        def change(data):
            data["component_mappings"].append(
                data["component_mappings"][0].copy()
            )

        errors = self.update_component_map(change)

        self.assertTrue(
            any("Duplicate reference component ID" in e
                for e in errors)
        )
        self.assertTrue(
            any("Duplicate vendor component ID" in e
                for e in errors)
        )

    def test_incorrect_wall_area(self):
        def change(data):
            data["component_mappings"][0][
                "properties"
            ]["area_ft2"] = 250

        errors = self.update_component_map(change)

        self.assertTrue(
            any("Component geometry mismatch" in e
                for e in errors)
        )

    def test_incorrect_wall_azimuth(self):
        def change(data):
            data["component_mappings"][0][
                "properties"
            ]["azimuth_degrees"] = 90

        errors = self.update_component_map(change)

        self.assertTrue(
            any("Component geometry mismatch" in e
                for e in errors)
        )

    def test_unsupported_component_type(self):
        def change(data):
            data["component_mappings"][0][
                "component_type"
            ] = "Roof"

        errors = self.update_component_map(change)

        self.assertTrue(
            any("Unsupported component type" in e
                for e in errors)
        )

    def generate_test_hashes(self):
        import hashlib

        manifest_path = self.folder / "manifest.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        for entry in manifest["files"]:
            filename = entry["filename"]
            entry["sha256"] = hashlib.sha256(
                (self.folder / filename).read_bytes()
            ).hexdigest()

        manifest["manifest_status"] = "CHECKSUMS_GENERATED"

        manifest_path.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

    def test_valid_checksums(self):
        self.generate_test_hashes()

        errors = validate_submission(self.folder)

        self.assertEqual(errors, [])

    def test_modified_file_detected(self):
        self.generate_test_hashes()

        path = self.folder / "building.xml"
        path.write_bytes(path.read_bytes() + b"\n")

        errors = validate_submission(self.folder)

        self.assertTrue(
            any("SHA-256 checksum mismatch: building.xml" in e
                for e in errors)
        )

    def test_missing_checksum_rejected(self):
        self.generate_test_hashes()

        path = self.folder / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))

        manifest["files"][0]["sha256"] = None

        path.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        errors = validate_submission(self.folder)

        self.assertTrue(
            any("Missing SHA-256 checksum" in e for e in errors)
        )

    def test_invalid_checksum_format_rejected(self):
        self.generate_test_hashes()

        path = self.folder / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))

        manifest["files"][0]["sha256"] = "INVALID-HASH"

        path.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        errors = validate_submission(self.folder)

        self.assertTrue(
            any("Invalid SHA-256 checksum" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
