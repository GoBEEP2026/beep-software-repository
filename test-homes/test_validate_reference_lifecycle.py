import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_reference_lifecycle import validate_reference_lifecycle


class TestReferenceLifecycle(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.folder = Path(self.temp_dir.name)

        self.previous_path = self.folder / "previous.json"
        self.current_path = self.folder / "current.json"

        self.home = {
            "test_home_id": "BEEP-HOME-001",
            "test_home_version": "1.0.0",
            "status": "APPROVED",
            "reference_files": [
                {
                    "filename": "sample-home.xml",
                    "sha256": "a" * 64
                }
            ],
            "approval": {
                "approved_by": "B.E.E.P. Board of Directors",
                "approval_date": "2026-11-17",
                "approval_record": "TEST-APPROVAL-001",
                "board_resolution_reference": "TEST-BOARD-RES-001"
            }
        }

    def validate(self, current_home):
        previous = {"reference_homes": [self.home]}
        current = {"reference_homes": [current_home]}

        self.previous_path.write_text(
            json.dumps(previous), encoding="utf-8"
        )
        self.current_path.write_text(
            json.dumps(current), encoding="utf-8"
        )

        return validate_reference_lifecycle(
            self.previous_path,
            self.current_path
        )

    def test_unchanged_approved_home_accepted(self):
        errors = self.validate(copy.deepcopy(self.home))
        self.assertEqual(errors, [])

    def test_removing_approved_home_rejected(self):
        self.previous_path.write_text(
            json.dumps({"reference_homes": [self.home]}),
            encoding="utf-8"
        )
        self.current_path.write_text(
            json.dumps({"reference_homes": []}),
            encoding="utf-8"
        )

        errors = validate_reference_lifecycle(
            self.previous_path,
            self.current_path
        )

        self.assertTrue(
            any("cannot be removed" in error for error in errors)
        )

    def test_modifying_approved_checksum_rejected(self):
        current = copy.deepcopy(self.home)
        current["reference_files"][0]["sha256"] = "b" * 64

        errors = self.validate(current)

        
        self.assertTrue(
            any(
                "Approved or retired reference home metadata cannot be modified"
                in error
                for error in errors
            )
        )



if __name__ == "__main__":
    unittest.main()
