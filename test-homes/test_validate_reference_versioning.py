import json
import tempfile
import unittest
from pathlib import Path


from validate_reference_versioning import (
    is_valid_version,
    parse_version,
    get_version_change_type,
    validate_reference_versioning,
)



class TestReferenceVersioning(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.registry_path = (
            Path(self.temp_dir.name) / "registry.json"
        )

    def write_registry(self, registry):
        self.registry_path.write_text(
            json.dumps(registry),
            encoding="utf-8",
        )

    def test_valid_semantic_versions(self):
        versions = [
            "1.0.0",
            "1.1.0",
            "1.0.1",
            "2.0.0",
            "10.12.3",
            "0.0.0",
        ]

        for version in versions:
            with self.subTest(version=version):
                self.assertTrue(is_valid_version(version))

    def test_invalid_semantic_versions(self):
        versions = [
            "1",
            "1.0",
            "1.0.0.0",
            "v1.0.0",
            "01.0.0",
            "1.01.0",
            "1.0.01",
            "1.0.0-beta",
            "1.0.0+build",
            "-1.0.0",
            "1.0.-1",
            " 1.0.0",
            "1.0.0 ",
            "",
            None,
            100,
            [],
            {},
        ]

        for version in versions:
            with self.subTest(version=version):
                self.assertFalse(is_valid_version(version))

    def test_valid_registry_accepted(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.0",
                }
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertEqual(errors, [])

    def test_invalid_registry_version_rejected(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0",
                }
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Invalid semantic version" in error
                for error in errors
            )
        )

    def test_missing_version_rejected(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                }
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Invalid semantic version" in error
                for error in errors
            )
        )

    def test_malformed_registry_rejected(self):
        for registry in (
            [],
            {},
            {"reference_homes": None},
            {"reference_homes": [None]},
        ):
            with self.subTest(registry=registry):
                self.write_registry(registry)

                errors = validate_reference_versioning(
                    self.registry_path
                )

                self.assertTrue(errors)

    def test_missing_registry_file_rejected(self):
        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Unable to read reference registry" in error
                for error in errors
            )
        )

    def test_invalid_json_rejected(self):
        self.registry_path.write_text(
            "{invalid json",
            encoding="utf-8",
        )

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Unable to read reference registry" in error
                for error in errors
            )
        )

    def test_parse_semantic_version(self):
        self.assertEqual(
            parse_version("1.2.3"),
            (1, 2, 3),
        )

    def test_parse_invalid_version_rejected(self):
        with self.assertRaises(ValueError):
            parse_version("1.0")

    def test_major_version_progression(self):
        self.assertEqual(
            get_version_change_type("1.2.3", "2.0.0"),
            "MAJOR",
        )

    def test_minor_version_progression(self):
        self.assertEqual(
            get_version_change_type("1.2.3", "1.3.0"),
            "MINOR",
        )

    def test_patch_version_progression(self):
        self.assertEqual(
            get_version_change_type("1.2.3", "1.2.4"),
            "PATCH",
        )

    def test_invalid_version_progression_rejected(self):
        invalid_transitions = [
            ("1.0.0", "3.0.0"),
            ("1.0.0", "1.2.0"),
            ("1.0.0", "1.0.5"),
            ("1.0.0", "1.0.0"),
            ("2.0.0", "1.0.0"),
            ("1.2.3", "2.2.3"),
            ("1.2.3", "1.3.3"),
            ("1.0", "2.0.0"),
            ("1.0.0", "2.0"),
            (None, "1.0.0"),
            ("1.0.0", None),
        ]

        for parent, proposed in invalid_transitions:
            with self.subTest(
                parent=parent,
                proposed=proposed,
            ):
                self.assertIsNone(
                    get_version_change_type(
                        parent,
                        proposed,
                    )
                )




if __name__ == "__main__":
    unittest.main()
