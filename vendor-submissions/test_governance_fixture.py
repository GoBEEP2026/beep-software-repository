
"""
Validate reusable fictional production governance evidence.

All records are generated in temporary storage.
No authoritative repository records are modified.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from governance_test_fixture import (
    create_governance_fixture,
    REPOSITORY_ROOT,
    HOME_ID,
    HOME_VERSION,
    REVIEW_RECORD,
    REVIEWER,
    GOVERNANCE_AUTHORITY,
)

from validate_reference_integrity import (
    validate_reference_integrity,
)

from validate_reference_approval import (
    validate_reference_approval,
)

from validate_approval_records import (
    validate_approval_records,
)

from validate_reference_audit import (
    validate_audit,
)

from validate_technical_review import (
    validate_review_fingerprint,
)

from validate_technical_review_records import (
    validate_technical_review_records,
)

from validate_review_identifiers import (
    validate_review_identifiers,
)


class TestGovernanceFixture(unittest.TestCase):

    def setUp(self):

        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.root = Path(
            self.temporary_directory.name
        )

        self.fixture = create_governance_fixture(
            self.root
        )

        self.registry = self.load_json(
            self.fixture["registry_path"]
        )

        self.audit = self.load_json(
            self.fixture["audit_path"]
        )

        self.identifiers = self.load_json(
            self.fixture["identifier_registry_path"]
        )

        self.home = self.registry[
            "reference_homes"
        ][0]

        self.audit_record = self.audit[
            "records"
        ][0]

    @staticmethod
    def load_json(path):

        return json.loads(
            Path(path).read_text(
                encoding="utf-8"
            )
        )

    def test_fixture_outside_repository(self):

        self.assertFalse(
            self.root.resolve().is_relative_to(
                REPOSITORY_ROOT.resolve()
            )
        )

    def test_fixture_rejects_repository_location(self):

        with self.assertRaisesRegex(
            ValueError,
            "inside the live repository",
        ):

            create_governance_fixture(
                REPOSITORY_ROOT
            )

    def test_required_governance_files_exist(self):

        for key in (
            "registry_path",
            "audit_path",
            "identifier_registry_path",
            "review_document",
            "approval_document",
        ):

            with self.subTest(file=key):

                self.assertTrue(
                    self.fixture[key].is_file()
                )

    def test_reference_home_identity(self):

        self.assertEqual(
            len(self.registry["reference_homes"]),
            1,
        )

        self.assertEqual(
            self.home["test_home_id"],
            HOME_ID,
        )

        self.assertEqual(
            self.home["test_home_version"],
            HOME_VERSION,
        )

    def test_reference_home_approval_status(self):

        self.assertEqual(
            self.registry["registry_status"],
            "APPROVED",
        )

        self.assertEqual(
            self.home["status"],
            "APPROVED",
        )

        self.assertEqual(
            self.home["approval"]["approved_by"],
            GOVERNANCE_AUTHORITY,
        )

    def test_reference_file_hashes(self):

        for entry in self.home["reference_files"]:

            path = (
                self.fixture["registry_path"].parent
                / entry["filename"]
            )

            actual_hash = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

            self.assertEqual(
                actual_hash,
                entry["sha256"],
            )

    def test_reference_integrity_validator(self):

        errors = validate_reference_integrity(
            self.fixture["registry_path"]
        )

        self.assertEqual(errors, [])

    def test_technical_review_fingerprint(self):

        errors = validate_review_fingerprint(
            self.home
        )

        self.assertEqual(errors, [])

    def test_completed_review_metadata(self):

        review = self.home["review"]

        self.assertEqual(
            review["review_status"],
            "COMPLETED",
        )

        self.assertEqual(
            review["review_recommendation"],
            "RECOMMEND_APPROVAL",
        )

        self.assertEqual(
            review["review_record"],
            REVIEW_RECORD,
        )

        self.assertEqual(
            review["reviewer"],
            REVIEWER,
        )

    def test_technical_review_document_validator(self):

        errors = validate_technical_review_records(
            self.fixture["registry_path"],
            self.fixture["approvals_directory"],
        )

        self.assertEqual(errors, [])

    def test_review_document_actual_checksum(self):

        actual_hash = hashlib.sha256(
            self.fixture[
                "review_document"
            ].read_bytes()
        ).hexdigest()

        self.assertEqual(
            actual_hash,
            self.audit_record[
                "technical_review_sha256"
            ],
        )

        self.assertEqual(
            actual_hash,
            self.fixture[
                "review_document_sha256"
            ],
        )

    def test_audit_fingerprint_matches_registry(self):

        self.assertEqual(
            self.audit_record[
                "reviewed_content_sha256"
            ],
            self.home["review"][
                "reviewed_content_sha256"
            ],
        )

    def test_identifier_registry_validator(self):

        errors = validate_review_identifiers(
            self.fixture[
                "identifier_registry_path"
            ]
        )

        self.assertEqual(errors, [])

    def test_identifier_reservation_matches_review(self):

        reservations = self.identifiers[
            "reservations"
        ]

        self.assertEqual(
            len(reservations),
            1,
        )

        reservation = reservations[0]

        self.assertEqual(
            reservation["review_record_id"],
            self.home["review"]["review_record"],
        )

        self.assertEqual(
            reservation["reference_home_id"],
            self.home["test_home_id"],
        )

        self.assertEqual(
            reservation["reference_home_version"],
            self.home["test_home_version"],
        )

        self.assertEqual(
            reservation["assigned_reviewer"],
            self.home["review"]["reviewer"],
        )

    def test_governance_chronology(self):

        reservation = self.identifiers[
            "reservations"
        ][0]

        assignment_date = reservation[
            "assignment_date"
        ]

        review_date = self.home["review"][
            "review_date"
        ]

        approval_date = self.home["approval"][
            "approval_date"
        ]

        self.assertLessEqual(
            assignment_date,
            review_date,
        )

        self.assertLessEqual(
            review_date,
            approval_date,
        )

        self.assertEqual(
            approval_date,
            self.audit_record["decision_date"],
        )

    def test_current_audit_schema(self):

        self.assertEqual(
            self.audit["audit_schema_version"],
            "1.1.0",
        )

        errors = validate_audit(
            self.fixture["audit_path"]
        )

        self.assertEqual(errors, [])

    def test_reference_approval_validator(self):

        errors = validate_reference_approval(
            registry_path=self.fixture[
                "registry_path"
            ],
            audit_path=self.fixture[
                "audit_path"
            ],
        )

        self.assertEqual(errors, [])

    def test_board_approval_document_validator(self):

        errors = validate_approval_records(
            registry_path=self.fixture[
                "registry_path"
            ],
            approvals_directory=self.fixture[
                "approvals_directory"
            ],
        )

        self.assertEqual(errors, [])

    def test_modified_reference_file_rejected(self):

        path = self.fixture[
            "reference_paths"
        ][0]

        with path.open("ab") as file:

            file.write(
                b"\n<!-- Fictional test modification -->\n"
            )

        errors = validate_reference_integrity(
            self.fixture["registry_path"]
        )

        self.assertTrue(
            any(
                "SHA-256 mismatch" in error
                for error in errors
            ),
            errors,
        )

    def test_missing_review_document_rejected(self):

        self.fixture[
            "review_document"
        ].unlink()

        errors = validate_technical_review_records(
            self.fixture["registry_path"],
            self.fixture["approvals_directory"],
        )

        self.assertTrue(
            any(
                "Missing technical review document"
                in error
                for error in errors
            ),
            errors,
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
