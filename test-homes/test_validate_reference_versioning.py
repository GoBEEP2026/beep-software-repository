import json
import tempfile
import unittest
from pathlib import Path




from validate_reference_versioning import (
    is_valid_version,
    parse_version,
    get_version_change_type,
    validate_parent_versions,
    validate_linear_version_history,
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


    def test_initial_version_accepted(self):
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

    def test_missing_initial_version_rejected(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "2.0.0",
                }
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Initial reference home version must be 1.0.0"
                in error
                for error in errors
            )
        )

    def test_zero_initial_version_rejected(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "0.0.0",
                }
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Initial reference home version must be 1.0.0"
                in error
                for error in errors
            )
        )

    
    
    def test_multiple_versions_with_initial_accepted(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": version,
                    "parent_version": parent,
                }
                for version, parent in (
                    ("1.0.0", None),
                    ("1.0.1", "1.0.0"),
                    ("1.1.0", "1.0.1"),
                    ("2.0.0", "1.1.0"),
                )
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertEqual(errors, [])





    def test_initial_version_required_for_each_home(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-001",
                    "test_home_version": "1.0.0",
                },
                {
                    "test_home_id": "BEEP-HOME-002",
                    "test_home_version": "1.1.0",
                },
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "BEEP-HOME-002: Initial reference home "
                "version must be 1.0.0" in error
                for error in errors
            )
        )

    def test_invalid_reference_home_id_rejected(self):
        for home_id in (None, "", " ", 123, [], {}):
            with self.subTest(home_id=home_id):
                self.write_registry({
                    "reference_homes": [
                        {
                            "test_home_id": home_id,
                            "test_home_version": "1.0.0",
                        }
                    ]
                })

                errors = validate_reference_versioning(
                    self.registry_path
                )

                self.assertTrue(
                    any(
                        "missing or invalid ID" in error
                        for error in errors
                    )
                )



    def test_initial_version_without_parent_accepted(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
                "parent_version": None,
            }
        ]

        self.assertEqual(validate_parent_versions(homes), [])

    def test_initial_version_with_parent_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
                "parent_version": "0.0.0",
            }
        ]

        errors = validate_parent_versions(homes)

        self.assertTrue(
            any(
                "Initial version must not have a parent version"
                in error
                for error in errors
            )
        )

    def test_valid_parent_version_chain_accepted(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": version,
                "parent_version": parent,
            }
            for version, parent in (
                ("1.0.0", None),
                ("1.0.1", "1.0.0"),
                ("1.1.0", "1.0.1"),
                ("2.0.0", "1.1.0"),
            )
        ]

        self.assertEqual(validate_parent_versions(homes), [])

    def test_missing_parent_version_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
            },
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.1",
            },
        ]

        errors = validate_parent_versions(homes)

        self.assertTrue(
            any(
                "Missing or invalid parent version" in error
                for error in errors
            )
        )

    def test_nonexistent_parent_version_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
            },
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.2",
                "parent_version": "1.0.1",
            },
        ]

        errors = validate_parent_versions(homes)

        self.assertTrue(
            any(
                "Parent version 1.0.1 does not exist" in error
                for error in errors
            )
        )

    def test_invalid_parent_progression_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
            },
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "3.0.0",
                "parent_version": "1.0.0",
            },
        ]

        errors = validate_parent_versions(homes)

        self.assertTrue(
            any(
                "Invalid version progression from parent"
                in error
                for error in errors
            )
        )

    def test_parent_from_different_home_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-001",
                "test_home_version": "1.0.0",
            },
            {
                "test_home_id": "BEEP-HOME-002",
                "test_home_version": "1.0.1",
                "parent_version": "1.0.0",
            },
        ]

        errors = validate_parent_versions(homes)

        self.assertTrue(
            any(
                "Parent version 1.0.0 does not exist"
                in error
                for error in errors
            )
        )

    def test_self_referencing_parent_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
            },
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.1",
                "parent_version": "1.0.1",
            },
        ]

        errors = validate_parent_versions(homes)

        self.assertTrue(
            any(
                "Invalid version progression from parent"
                in error
                for error in errors
            )
        )



    def test_registry_rejects_missing_parent(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.0",
                },
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.1",
                },
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Missing or invalid parent version" in error
                for error in errors
            )
        )

    def test_registry_rejects_skipped_version(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.0",
                },
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "3.0.0",
                    "parent_version": "1.0.0",
                },
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Invalid version progression from parent"
                in error
                for error in errors
            )
        )



    def test_registry_rejects_missing_parent(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.0",
                },
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.1",
                },
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Missing or invalid parent version" in error
                for error in errors
            )
        )

    def test_registry_rejects_skipped_version(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.0",
                },
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "3.0.0",
                    "parent_version": "1.0.0",
                },
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Invalid version progression from parent"
                in error
                for error in errors
            )
        )



    def test_valid_linear_version_history(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": version,
                "parent_version": parent,
            }
            for version, parent in (
                ("1.0.0", None),
                ("1.0.1", "1.0.0"),
                ("1.1.0", "1.0.1"),
                ("2.0.0", "1.1.0"),
            )
        ]

        self.assertEqual(
            validate_linear_version_history(homes),
            [],
        )

    def test_branching_version_history_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": version,
                "parent_version": parent,
            }
            for version, parent in (
                ("1.0.0", None),
                ("1.0.1", "1.0.0"),
                ("1.1.0", "1.0.0"),
            )
        ]

        errors = validate_linear_version_history(homes)

        self.assertTrue(
            any(
                "Parent must be the immediate predecessor"
                in error
                for error in errors
            )
        )

    def test_duplicate_version_history_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
                "parent_version": None,
            },
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
                "parent_version": None,
            },
        ]

        errors = validate_linear_version_history(homes)

        self.assertTrue(
            any(
                "Duplicate reference home version" in error
                for error in errors
            )
        )

    def test_linear_history_skipped_version_rejected(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.0",
                "parent_version": None,
            },
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": "1.0.3",
                "parent_version": "1.0.0",
            },
        ]

        errors = validate_linear_version_history(homes)

        self.assertTrue(
            any(
                "Invalid sequential version increment"
                in error
                for error in errors
            )
        )

    def test_numeric_version_ordering(self):
        homes = [
            {
                "test_home_id": "BEEP-HOME-TEST",
                "test_home_version": f"1.{minor}.0",
                "parent_version": (
                    None if minor == 0
                    else f"1.{minor - 1}.0"
                ),
            }
            for minor in reversed(range(11))
        ]

        self.assertEqual(
            validate_linear_version_history(homes),
            [],
        )

    def test_independent_home_version_histories(self):
        homes = [
            {
                "test_home_id": home_id,
                "test_home_version": version,
                "parent_version": parent,
            }
            for home_id in (
                "BEEP-HOME-001",
                "BEEP-HOME-002",
            )
            for version, parent in (
                ("1.0.0", None),
                ("1.0.1", "1.0.0"),
            )
        ]

        self.assertEqual(
            validate_linear_version_history(homes),
            [],
        )



    def test_registry_rejects_duplicate_versions(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.0",
                    "parent_version": None,
                },
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": "1.0.0",
                    "parent_version": None,
                },
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Duplicate reference home version" in error
                for error in errors
            )
        )

    def test_registry_rejects_branching_history(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": version,
                    "parent_version": parent,
                }
                for version, parent in (
                    ("1.0.0", None),
                    ("1.0.1", "1.0.0"),
                    ("1.1.0", "1.0.0"),
                )
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Parent must be the immediate predecessor"
                in error
                for error in errors
            )
        )

    def test_registry_rejects_nonsequential_history(self):
        self.write_registry({
            "reference_homes": [
                {
                    "test_home_id": "BEEP-HOME-TEST",
                    "test_home_version": version,
                    "parent_version": parent,
                }
                for version, parent in (
                    ("1.0.0", None),
                    ("1.0.1", "1.0.0"),
                    ("1.0.3", "1.0.1"),
                )
            ]
        })

        errors = validate_reference_versioning(
            self.registry_path
        )

        self.assertTrue(
            any(
                "Invalid sequential version increment"
                in error
                for error in errors
            )
        )





if __name__ == "__main__":
    unittest.main()
