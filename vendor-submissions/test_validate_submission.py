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

    def update_json_file(self, filename, change):
        path = self.folder / filename
        data = json.loads(path.read_text(encoding="utf-8"))

        change(data)

        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

        return validate_submission(self.folder)

    def test_schema_missing_vendor_name(self):
        def change(data):
            del data["vendor"]["vendor_name"]

        errors = self.update_json_file(
            "submission.json", change
        )

        self.assertTrue(
            any("Schema validation error" in e
                and "vendor_name" in e for e in errors)
        )

    def test_schema_invalid_compliance_path(self):
        def change(data):
            data["test"]["compliance_path"] = "INVALID"

        errors = self.update_json_file(
            "submission.json", change
        )

        self.assertTrue(
            any("Schema validation error" in e
                and "compliance_path" in e for e in errors)
        )

    def test_schema_invalid_energy_type(self):
        def change(data):
            data["results"]["annual_energy"][
                "heating_kwh"
            ] = "3200"

        errors = self.update_json_file(
            "results.json", change
        )

        self.assertTrue(
            any("Schema validation error" in e
                and "heating_kwh" in e for e in errors)
        )

    def test_schema_negative_wall_area(self):
        def change(data):
            data["component_mappings"][0][
                "properties"
            ]["area_ft2"] = -200

        errors = self.update_json_file(
            "component-map.json", change
        )

        self.assertTrue(
            any("Schema validation error" in e
                and "area_ft2" in e for e in errors)
        )

    def test_schema_invalid_manifest_algorithm(self):
        def change(data):
            data["hash_algorithm"] = "MD5"

        errors = self.update_json_file(
            "manifest.json", change
        )

        self.assertTrue(
            any("Schema validation error" in e
                and "hash_algorithm" in e for e in errors)
        )

    def test_production_rejects_sample_data(self):
        errors = validate_submission(self.folder, production=True)

        self.assertTrue(
            any("COMPLETED calculation status" in e for e in errors)
        )

    def test_production_rejects_missing_engine_version(self):
        self.generate_test_hashes()

        submission_path = self.folder / "submission.json"
        submission = json.loads(
            submission_path.read_text(encoding="utf-8")
        )

        submission["software"]["engine_version"] = "not-specified"

        submission_path.write_text(
            json.dumps(submission, indent=2),
            encoding="utf-8"
        )

        errors = validate_submission(self.folder, production=True)

        self.assertTrue(
            any("valid engine_version" in e for e in errors)
        )

    def test_production_rejects_development_manifest(self):
        errors = validate_submission(self.folder, production=True)

        self.assertTrue(
            any("requires generated SHA-256 checksums" in e
                for e in errors)
        )

    def test_production_rejects_missing_checksum(self):
        self.generate_test_hashes()

        manifest_path = self.folder / "manifest.json"
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        manifest["files"][0]["sha256"] = None

        manifest_path.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        errors = validate_submission(self.folder, production=True)

        self.assertTrue(
            any("Missing production checksum" in e for e in errors)
        )


    def test_production_accepts_complete_submission(self):
        submission_path = self.folder / "submission.json"
        submission = json.loads(
            submission_path.read_text(encoding="utf-8")
        )
        submission["software"]["engine_version"] = "1.0.0"
        submission_path.write_text(
            json.dumps(submission, indent=2),
            encoding="utf-8"
        )

        results_path = self.folder / "results.json"
        results = json.loads(
            results_path.read_text(encoding="utf-8")
        )
        results["calculation_status"] = "COMPLETED"
        results_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8"
        )

        # Create a temporary approved reference registry.
        registry_source = (
            Path(__file__).resolve().parent.parent
            / "test-homes"
            / "reference-home-registry.json"
        )

        registry = json.loads(
            registry_source.read_text(encoding="utf-8")
        )

        registry["registry_status"] = "APPROVED"
        registry["reference_homes"][0]["status"] = "APPROVED"

        registry["reference_homes"][0]["approval"] = {
            "approved_by": "BEEP Test Approval Authority",
            "approval_date": "2026-11-17",
            "approval_record": "TEST-APPROVAL-001"
        }

        registry["reference_homes"][0]["test_cycles"] = [
            "TEST-CYCLE-001"
        ]

        registry_path = self.folder / "test-registry.json"
        registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8"
        )

        # Create a temporary approval document for this test.
        approvals_directory = self.folder / "approvals"

        approval_path = (
            approvals_directory
            / "BEEP-HOME-001"
            / "1.0.0"
            / "approval-record.md"
        )

        approval_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

       
        approval_path.write_text(
            "# B.E.E.P. Test Approval Record\n\n"
            "Reference Home ID: BEEP-HOME-001\n"
            "Reference Home Version: 1.0.0\n"
            "Approval Record ID: TEST-APPROVAL-001\n"
            "Approval Status: APPROVED\n"
            "Approval Authority: B.E.E.P. Board of Directors\n"
            "Board Resolution Reference: TEST-BOARD-RES-001\n"
            "Board Decision Date: 2026-11-17\n",
            encoding="utf-8"
        )


        self.generate_test_hashes()

        # Create a temporary approval audit record.
        audit_path = self.folder / "test-approval-audit.json"

        audit = {
            "audit_schema_version": "1.0.0",
            "repository": "BEEP Software Consistency Repository",
            "audit_status": "DEVELOPMENT",
            "records": [
                {
                    "record_id": "TEST-APPROVAL-001",
                    "reference_home_id": "BEEP-HOME-001",
                    "reference_home_version": "1.0.0",
                    "decision": "APPROVED",
                    "reviewer": "Test Technical Reviewer",
                    "approval_authority": "BEEP Test Approval Authority",
                    "evidence": "TEST-EVIDENCE-001",
                    "pull_request": "TEST-PR-001",
                    "decision_date": "2026-11-17",
                }
            ],
        }

        audit_path.write_text(
            json.dumps(audit, indent=2),
            encoding="utf-8",
        )

        
        
        errors = validate_submission(
            self.folder,
            production=True,
            registry_path=registry_path,
            approvals_directory=approvals_directory,
            audit_path=audit_path,
        )


        self.assertEqual(errors, [])

    def test_production_rejects_missing_approval_document(self):
        registry_source = (
            Path(__file__).resolve().parent.parent
            / "test-homes"
            / "reference-home-registry.json"
        )

        registry = json.loads(
            registry_source.read_text(encoding="utf-8")
        )

        # Set up a simulated approved reference home.
        registry["registry_status"] = "APPROVED"

        home = registry["reference_homes"][0]
        home["status"] = "APPROVED"

        home["approval"] = {
            "approved_by": "BEEP Test Approval Authority",
            "approval_date": "2026-11-17",
            "approval_record": "TEST-APPROVAL-001"
        }

        home["test_cycles"] = ["TEST-CYCLE-001"]

        registry_path = self.folder / "test-registry.json"

        registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8"
        )

        # Use an empty temporary approval directory.
        approvals_directory = self.folder / "empty-approvals"
        approvals_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        errors = validate_submission(
            self.folder,
            production=True,
            registry_path=registry_path,
            approvals_directory=approvals_directory
        )

        self.assertTrue(
            any("Missing approval document" in e for e in errors),
            f"Actual validation errors: {errors}"
        )


    def test_unknown_reference_home_rejected(self):
        def change(data):
            data["test"]["test_home_id"] = "UNKNOWN-HOME"

        errors = self.update_json_file("submission.json", change)

        self.assertTrue(
            any("not uniquely registered" in e for e in errors)
        )

    def test_incorrect_reference_home_version_rejected(self):
        def change(data):
            data["test"]["test_home_version"] = "99.0.0"

        errors = self.update_json_file("submission.json", change)

        self.assertTrue(
            any("not uniquely registered" in e for e in errors)
        )

    def test_unauthorized_reference_compliance_path(self):
        def change(data):
            data["test"]["compliance_path"] = "OTHER"

        errors = self.update_json_file("submission.json", change)

        self.assertTrue(
            any("Compliance path not authorized" in e
                for e in errors)
        )

    def test_unapproved_reference_home_rejected_in_production(self):
        errors = validate_submission(
            self.folder,
            production=True
        )

        self.assertTrue(
            any("Reference home is not approved" in e
                for e in errors)
        )

    def test_duplicate_reference_home_registry_entry(self):
        registry_source = (
            Path(__file__).resolve().parent.parent
            / "test-homes"
            / "reference-home-registry.json"
        )

        registry = json.loads(
            registry_source.read_text(encoding="utf-8")
        )

        registry["reference_homes"].append(
            registry["reference_homes"][0].copy()
        )

        registry_path = self.folder / "duplicate-registry.json"
        registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8"
        )

        errors = validate_submission(
            self.folder,
            registry_path=registry_path
        )

        self.assertTrue(
            any("not uniquely registered" in e for e in errors)
        )

    def test_production_rejects_incomplete_approval(self):
        registry_source = (
            Path(__file__).resolve().parent.parent
            / "test-homes"
            / "reference-home-registry.json"
        )

        registry = json.loads(
            registry_source.read_text(encoding="utf-8")
        )

        # Claim the registry and home are approved.
        registry["registry_status"] = "APPROVED"
        registry["reference_homes"][0]["status"] = "APPROVED"

        # Deliberately provide incomplete approval data.
        registry["reference_homes"][0]["approval"] = {
            "approved_by": None,
            "approval_date": None,
            "approval_record": None
        }

        registry["reference_homes"][0]["test_cycles"] = []

        registry_path = self.folder / "incomplete-approval.json"

        registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8"
        )

        errors = validate_submission(
            self.folder,
            production=True,
            registry_path=registry_path
        )

        
        self.assertTrue(
            any("Missing approval authority" in e for e in errors),
            f"Actual validation errors: {errors}"
        )


        
        self.assertTrue(
            any("Invalid approval date" in e for e in errors),
            f"Actual validation errors: {errors}"
        )


        
        self.assertTrue(
            any("Missing approval record" in e for e in errors),
            f"Actual validation errors: {errors}"
        )


       
        self.assertTrue(
            any("No assigned test cycles" in e for e in errors),
            f"Actual validation errors: {errors}"
        )



if __name__ == "__main__":
    unittest.main()
