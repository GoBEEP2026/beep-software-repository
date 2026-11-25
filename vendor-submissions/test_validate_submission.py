import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from governance_test_fixture import (
    create_governance_fixture,
)

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


    def test_production_accepts_complete_submission(self):

        submission_path = self.folder / "submission.json"

        submission = json.loads(
            submission_path.read_text(
                encoding="utf-8"
            )
        )

        submission["software"]["engine_version"] = "1.0.0"

        submission_path.write_text(
            json.dumps(submission, indent=2),
            encoding="utf-8",
        )

        results_path = self.folder / "results.json"

        results = json.loads(
            results_path.read_text(
                encoding="utf-8"
            )
        )

        results["calculation_status"] = "COMPLETED"

        results_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )

        # Create isolated fictional governance evidence.
        # These records do not represent an actual
        # technical review or Board approval.

        governance_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            governance_directory.cleanup
        )

        fixture = create_governance_fixture(
            Path(governance_directory.name)
        )

        # Generate actual vendor submission checksums.

        self.generate_test_hashes()

        # Validate the complete production submission
        # against the fictional governance evidence.

        
        errors = validate_submission(
            self.folder,
            production=True,
            registry_path=fixture["registry_path"],
            approvals_directory=fixture[
                "approvals_directory"
            ],
            audit_path=fixture["audit_path"],
            identifier_registry_path=fixture[
                "identifier_registry_path"
            ],
        )


        self.assertEqual(errors, [])

    
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

   
    def test_production_rejects_missing_approval_document(self):

        # Prepare an otherwise valid production submission.

        submission_path = self.folder / "submission.json"

        submission = json.loads(
            submission_path.read_text(
                encoding="utf-8"
            )
        )

        submission["software"]["engine_version"] = "1.0.0"

        submission_path.write_text(
            json.dumps(submission, indent=2),
            encoding="utf-8",
        )

        results_path = self.folder / "results.json"

        results = json.loads(
            results_path.read_text(
                encoding="utf-8"
            )
        )

        results["calculation_status"] = "COMPLETED"

        results_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )

        self.generate_test_hashes()

        # Create complete isolated fictional
        # governance evidence.

        governance_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            governance_directory.cleanup
        )

        fixture = create_governance_fixture(
            Path(governance_directory.name)
        )

        governance_inputs = {
            "registry_path": fixture["registry_path"],
            "approvals_directory": fixture[
                "approvals_directory"
            ],
            "audit_path": fixture["audit_path"],
            "identifier_registry_path": fixture[
                "identifier_registry_path"
            ],
        }

        # Confirm the complete production submission
        # passes before removing approval evidence.

        baseline_errors = validate_submission(
            self.folder,
            production=True,
            **governance_inputs,
        )

        self.assertEqual(
            baseline_errors,
            [],
        )

        # Deliberately remove the Board approval document.

        fixture["approval_document"].unlink()

        # Validate the same production submission
        # with missing approval documentation.

        errors = validate_submission(
            self.folder,
            production=True,
            **governance_inputs,
        )

        self.assertTrue(
            any(
                "Missing approval document" in e
                for e in errors
            ),
            f"Actual validation errors: {errors}",
        )

        self.assertTrue(
            any(
                e.startswith("Board authorization:")
                for e in errors
            ),
            f"Actual validation errors: {errors}",
        )

        self.assertTrue(
            any(
                e.startswith("Approval supporting records:")
                for e in errors
            ),
            f"Actual validation errors: {errors}",
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

        # Prepare an otherwise valid production submission.

        submission_path = self.folder / "submission.json"

        submission = json.loads(
            submission_path.read_text(
                encoding="utf-8"
            )
        )

        submission["software"]["engine_version"] = "1.0.0"

        submission_path.write_text(
            json.dumps(submission, indent=2),
            encoding="utf-8",
        )

        results_path = self.folder / "results.json"

        results = json.loads(
            results_path.read_text(
                encoding="utf-8"
            )
        )

        results["calculation_status"] = "COMPLETED"

        results_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )

        self.generate_test_hashes()

        # Create complete isolated fictional
        # governance evidence.

        governance_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            governance_directory.cleanup
        )

        fixture = create_governance_fixture(
            Path(governance_directory.name)
        )

        governance_inputs = {
            "registry_path": fixture["registry_path"],
            "approvals_directory": fixture[
                "approvals_directory"
            ],
            "audit_path": fixture["audit_path"],
            "identifier_registry_path": fixture[
                "identifier_registry_path"
            ],
        }

        # Confirm the complete production submission
        # passes before modifying approval metadata.

        baseline_errors = validate_submission(
            self.folder,
            production=True,
            **governance_inputs,
        )

        self.assertEqual(
            baseline_errors,
            [],
        )

        # Load the isolated reference home registry.

        registry_path = fixture["registry_path"]

        registry = json.loads(
            registry_path.read_text(
                encoding="utf-8"
            )
        )

        home = registry["reference_homes"][0]

        # Deliberately invalidate approval metadata
        # while retaining the claimed APPROVED status.

        home["approval"]["approved_by"] = None
        home["approval"]["approval_date"] = None
        home["approval"]["approval_record"] = None

        home["test_cycles"] = []

        registry_path.write_text(
            json.dumps(registry, indent=2),
            encoding="utf-8",
        )

        # Validate the same production submission
        # against the incomplete approval metadata.

        errors = validate_submission(
            self.folder,
            production=True,
            **governance_inputs,
        )

        expected_errors = (
            "Missing approval authority",
            "Invalid approval date",
            "Missing approval record",
            "No assigned test cycles",
        )

        for expected_error in expected_errors:

            with self.subTest(
                expected_error=expected_error
            ):

                self.assertTrue(
                    any(
                        e.startswith(
                            "Reference approval metadata:"
                        )
                        and expected_error in e
                        for e in errors
                    ),
                    f"Actual validation errors: {errors}",
                )

    def verify_partial_governance_inputs_rejected(
        self,
        supplied_paths,
    ):

        # Prepare an otherwise valid production submission.

        submission_path = self.folder / "submission.json"

        submission = json.loads(
            submission_path.read_text(
                encoding="utf-8"
            )
        )

        submission["software"]["engine_version"] = "1.0.0"

        submission_path.write_text(
            json.dumps(submission, indent=2),
            encoding="utf-8",
        )

        results_path = self.folder / "results.json"

        results = json.loads(
            results_path.read_text(
                encoding="utf-8"
            )
        )

        results["calculation_status"] = "COMPLETED"

        results_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )

        self.generate_test_hashes()

        # Create complete isolated fictional
        # governance evidence.

        governance_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            governance_directory.cleanup
        )

        fixture = create_governance_fixture(
            Path(governance_directory.name)
        )

        governance_inputs = {
            "registry_path": fixture["registry_path"],
            "audit_path": fixture["audit_path"],
            "identifier_registry_path": fixture[
                "identifier_registry_path"
            ],
            "approvals_directory": fixture[
                "approvals_directory"
            ],
        }

        # Establish successful production validation
        # using all four governance inputs.

        baseline_errors = validate_submission(
            self.folder,
            production=True,
            **governance_inputs,
        )

        self.assertEqual(
            baseline_errors,
            [],
        )

        # Test every combination containing the
        # specified number of explicit paths.

        from itertools import combinations

        for selected_paths in combinations(
            governance_inputs,
            supplied_paths,
        ):

            with self.subTest(
                selected_paths=selected_paths
            ):

                partial_inputs = {
                    key: governance_inputs[key]
                    for key in selected_paths
                }

                errors = validate_submission(
                    self.folder,
                    production=True,
                    **partial_inputs,
                )

                self.assertIn(
                    "Production governance requires either "
                    "all four explicit governance paths "
                    "or all authoritative repository defaults",
                    errors,
                )


    def test_production_rejects_one_governance_path(self):

        self.verify_partial_governance_inputs_rejected(
            1
        )


    def test_production_rejects_two_governance_paths(self):

        self.verify_partial_governance_inputs_rejected(
            2
        )


    def test_production_rejects_three_governance_paths(self):

        self.verify_partial_governance_inputs_rejected(
            3
        )


if __name__ == "__main__":
    unittest.main()
