import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from governance_test_fixture import (
    create_governance_fixture,
)

from validate_production_governance import (
    validate_production_governance,
    run_governance_check,
)


class TestProductionGovernance(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(
            self.temp_dir.cleanup
        )

        self.root = Path(
            self.temp_dir.name
        )

        self.fixture = create_governance_fixture(
            self.root
        )

        self.registry_path = self.fixture[
            "registry_path"
        ]

        self.audit_path = self.fixture[
            "audit_path"
        ]

        self.identifier_registry_path = self.fixture[
            "identifier_registry_path"
        ]

        self.approvals_directory = self.fixture[
            "approvals_directory"
        ]

        self.review_document = self.fixture[
            "review_document"
        ]

        self.approval_document = self.fixture[
            "approval_document"
        ]

    def validate(self):

        return validate_production_governance(
            registry_path=self.registry_path,
            audit_path=self.audit_path,
            identifier_registry_path=(
                self.identifier_registry_path
            ),
            approvals_directory=(
                self.approvals_directory
            ),
        )

    @staticmethod
    def read_json(path):

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    @staticmethod
    def write_json(path, data):

        path.write_text(
            json.dumps(
                data,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

    def assert_control_error(
        self,
        errors,
        control,
    ):

        self.assertTrue(
            any(
                error.startswith(
                    control + ":"
                )
                for error in errors
            ),
            f"Expected {control}. "
            f"Actual errors: {errors}",
        )

    # ------------------------------------------
    # VALID GOVERNANCE EVIDENCE
    # ------------------------------------------

    def test_valid_governance_evidence(self):

        self.assertEqual(
            self.validate(),
            [],
        )

    def test_validation_is_read_only(self):

        before = {
            path.relative_to(self.root):
                path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

        self.assertEqual(
            self.validate(),
            [],
        )

        after = {
            path.relative_to(self.root):
                path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

        self.assertEqual(
            before,
            after,
        )

    # ------------------------------------------
    # MISSING GOVERNANCE INPUTS
    # ------------------------------------------

    def test_missing_reference_registry(self):

        self.registry_path.unlink()

        self.assert_control_error(
            self.validate(),
            "Governance input validation",
        )

    def test_missing_audit_registry(self):

        self.audit_path.unlink()

        self.assert_control_error(
            self.validate(),
            "Governance input validation",
        )

    def test_missing_identifier_registry(self):

        self.identifier_registry_path.unlink()

        self.assert_control_error(
            self.validate(),
            "Governance input validation",
        )

    def test_missing_approvals_directory(self):

        self.approvals_directory = (
            self.root / "missing-approvals"
        )

        self.assert_control_error(
            self.validate(),
            "Governance input validation",
        )

    # ------------------------------------------
    # JSON INPUT PROTECTION
    # ------------------------------------------

    def test_malformed_reference_registry(self):

        self.registry_path.write_text(
            "{invalid json",
            encoding="utf-8",
        )

        self.assert_control_error(
            self.validate(),
            "Governance input validation",
        )

    def test_non_object_reference_registry(self):

        self.registry_path.write_text(
            "[]",
            encoding="utf-8",
        )

        self.assert_control_error(
            self.validate(),
            "Governance input validation",
        )

    def test_duplicate_reference_registry_keys(self):

        self.registry_path.write_text(
            '{"reference_homes": [], '
            '"reference_homes": []}',
            encoding="utf-8",
        )

        errors = self.validate()

        self.assert_control_error(
            errors,
            "Governance input validation",
        )

        self.assertTrue(
            any(
                "Duplicate JSON key" in error
                for error in errors
            ),
            errors,
        )

    def test_duplicate_audit_registry_keys(self):

        self.audit_path.write_text(
            '{"records": [], "records": []}',
            encoding="utf-8",
        )

        errors = self.validate()

        self.assert_control_error(
            errors,
            "Governance input validation",
        )

        self.assertTrue(
            any(
                "Duplicate JSON key" in error
                for error in errors
            ),
            errors,
        )

    # ------------------------------------------
    # REFERENCE FILE INTEGRITY
    # ------------------------------------------

    def test_modified_reference_file(self):

        registry = self.read_json(
            self.registry_path
        )

        filename = registry[
            "reference_homes"
        ][0]["reference_files"][0]["filename"]

        path = (
            self.registry_path.parent
            / filename
        )

        path.write_bytes(
            path.read_bytes()
            + b"\n<!-- Modified test file -->\n"
        )

        self.assert_control_error(
            self.validate(),
            "Reference file integrity",
        )

    def test_missing_reference_file(self):

        registry = self.read_json(
            self.registry_path
        )

        filename = registry[
            "reference_homes"
        ][0]["reference_files"][0]["filename"]

        path = (
            self.registry_path.parent
            / filename
        )

        path.unlink()

        self.assert_control_error(
            self.validate(),
            "Reference file integrity",
        )

    # ------------------------------------------
    # TECHNICAL REVIEW INTEGRITY
    # ------------------------------------------

    def test_invalid_technical_fingerprint(self):

        registry = self.read_json(
            self.registry_path
        )

        registry["reference_homes"][0][
            "review"
        ]["reviewed_content_sha256"] = "0" * 64

        self.write_json(
            self.registry_path,
            registry,
        )

        self.assert_control_error(
            self.validate(),
            "Technical review registry",
        )

    def test_missing_technical_review_document(self):

        self.review_document.unlink()

        self.assert_control_error(
            self.validate(),
            "Technical review supporting records",
        )

    def test_invalid_approval_chronology(self):

        registry = self.read_json(
            self.registry_path
        )

        registry["reference_homes"][0][
            "approval"
        ]["approval_date"] = "2026-01-01"

        self.write_json(
            self.registry_path,
            registry,
        )

        self.assert_control_error(
            self.validate(),
            "Review and approval chronology",
        )

    # ------------------------------------------
    # BOARD AUTHORIZATION
    # ------------------------------------------

    def test_missing_board_approval_document(self):

        self.approval_document.unlink()

        self.assert_control_error(
            self.validate(),
            "Board authorization",
        )

    def test_unauthorized_board_authority(self):

        content = self.approval_document.read_text(
            encoding="utf-8"
        )

        content = content.replace(
            "Approval Authority: "
            "B.E.E.P. Board of Directors",
            "Approval Authority: Unauthorized Person",
        )

        self.approval_document.write_text(
            content,
            encoding="utf-8",
        )

        self.assert_control_error(
            self.validate(),
            "Board authorization",
        )

    def test_missing_board_resolution(self):

        content = self.approval_document.read_text(
            encoding="utf-8"
        )

        content = "\n".join(
            line
            for line in content.splitlines()
            if not line.startswith(
                "Board Resolution Reference:"
            )
        )

        self.approval_document.write_text(
            content + "\n",
            encoding="utf-8",
        )

        self.assert_control_error(
            self.validate(),
            "Board authorization",
        )

    # ------------------------------------------
    # IDENTIFIER RESERVATIONS
    # ------------------------------------------

    def test_missing_identifier_reservation(self):

        registry = self.read_json(
            self.identifier_registry_path
        )

        registry["reservations"] = []

        self.write_json(
            self.identifier_registry_path,
            registry,
        )

        self.assert_control_error(
            self.validate(),
            "Review assignment consistency",
        )

    def test_mismatched_reserved_reviewer(self):

        registry = self.read_json(
            self.identifier_registry_path
        )

        registry["reservations"][0][
            "assigned_reviewer"
        ] = "Unauthorized Reviewer"

        self.write_json(
            self.identifier_registry_path,
            registry,
        )

        self.assert_control_error(
            self.validate(),
            "Review assignment consistency",
        )

    # ------------------------------------------
    # AUDIT EVIDENCE AND CONSISTENCY
    # ------------------------------------------

    def test_invalid_audit_schema(self):

        audit = self.read_json(
            self.audit_path
        )

        audit["audit_schema_version"] = "1.0.0"

        self.write_json(
            self.audit_path,
            audit,
        )

        self.assert_control_error(
            self.validate(),
            "Reference approval audit",
        )

    def test_modified_review_document_checksum(self):

        self.review_document.write_bytes(
            self.review_document.read_bytes()
            + b"\nModified supporting evidence.\n"
        )

        self.assert_control_error(
            self.validate(),
            "Audit review evidence",
        )

    def test_missing_original_approval_audit(self):

        audit = self.read_json(
            self.audit_path
        )

        audit["records"] = []

        self.write_json(
            self.audit_path,
            audit,
        )

        self.assert_control_error(
            self.validate(),
            "Approval audit consistency",
        )

    def test_mismatched_audit_review_reservation(self):

        audit = self.read_json(
            self.audit_path
        )

        audit["records"][0][
            "technical_review_record"
        ] = "UNRESERVED-REVIEW-001"

        self.write_json(
            self.audit_path,
            audit,
        )

        self.assert_control_error(
            self.validate(),
            "Audit review reservations",
        )

    # ------------------------------------------
    # SYMBOLIC LINK PROTECTION
    # ------------------------------------------

    def test_symbolic_link_reference_registry(self):

        target = (
            self.registry_path.parent
            / "actual-reference-registry.json"
        )

        self.registry_path.rename(target)

        self.registry_path.symlink_to(target)

        self.assert_control_error(
            self.validate(),
            "Governance input validation",
        )

    def test_symbolic_link_approval_document(self):

        target = (
            self.root
            / "external-approval-record.md"
        )

        self.approval_document.rename(target)

        self.approval_document.symlink_to(
            target
        )

        self.assert_control_error(
            self.validate(),
            "Board authorization",
        )

    def test_symbolic_link_approvals_directory(self):

        target = (
            self.root / "actual-approvals"
        )

        self.approvals_directory.rename(
            target
        )

        self.approvals_directory.symlink_to(
            target,
            target_is_directory=True,
        )

        self.assert_control_error(
            self.validate(),
            "Governance input validation",
        )

    # ------------------------------------------
    # FAIL-CLOSED VALIDATION
    # ------------------------------------------

    def test_validator_exception_fails_closed(self):

        with patch(
            "validate_production_governance."
            "validate_reference_integrity",
            side_effect=RuntimeError(
                "Controlled validator failure"
            ),
        ):

            errors = self.validate()

        self.assert_control_error(
            errors,
            "Reference file integrity",
        )

        self.assertTrue(
            any(
                "Controlled validator failure"
                in error
                for error in errors
            ),
            errors,
        )

    def test_invalid_validator_response(self):

        errors = run_governance_check(
            "Controlled check",
            lambda: None,
        )

        self.assertEqual(
            errors,
            [
                "Controlled check: "
                "Invalid validator response"
            ],
        )

    def test_invalid_validator_error_type(self):

        errors = run_governance_check(
            "Controlled check",
            lambda: [123],
        )

        self.assertEqual(
            errors,
            [
                "Controlled check: "
                "Invalid validator response"
            ],
        )

    def verify_partial_governance_inputs_rejected(
        self,
        supplied_paths,
    ):

        from itertools import combinations

        governance_inputs = {
            "registry_path": self.registry_path,
            "audit_path": self.audit_path,
            "identifier_registry_path": (
                self.identifier_registry_path
            ),
            "approvals_directory": (
                self.approvals_directory
            ),
        }

        # Confirm the complete governance fixture
        # passes before testing incomplete inputs.

        baseline_errors = validate_production_governance(
            **governance_inputs,
        )

        self.assertEqual(
            baseline_errors,
            [],
        )

        expected_errors = [
            "Production governance requires either "
            "all four explicit governance paths "
            "or all authoritative repository defaults"
        ]

        # Verify every incomplete combination
        # containing the specified number of paths.

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

                errors = validate_production_governance(
                    **partial_inputs,
                )

                self.assertEqual(
                    errors,
                    expected_errors,
                )


    def test_governance_rejects_one_explicit_path(self):

        self.verify_partial_governance_inputs_rejected(
            1
        )


    def test_governance_rejects_two_explicit_paths(self):

        self.verify_partial_governance_inputs_rejected(
            2
        )


    def test_governance_rejects_three_explicit_paths(self):

        self.verify_partial_governance_inputs_rejected(
            3
        )


    def test_centralized_partial_inputs_rejected_before_file_access(
        self,
    ):

        expected_errors = [
            "Production governance requires either "
            "all four explicit governance paths "
            "or all authoritative repository defaults"
        ]

        with patch.object(
            Path,
            "open",
            side_effect=AssertionError(
                "Unexpected governance file access"
            ),
        ) as file_open, patch.object(
            Path,
            "is_file",
            side_effect=AssertionError(
                "Unexpected governance file inspection"
            ),
        ) as file_check, patch.object(
            Path,
            "is_dir",
            side_effect=AssertionError(
                "Unexpected governance directory inspection"
            ),
        ) as directory_check:

            errors = validate_production_governance(
                registry_path=self.registry_path,
            )

            self.assertEqual(
                errors,
                expected_errors,
            )

            file_open.assert_not_called()
            file_check.assert_not_called()
            directory_check.assert_not_called()


    def test_vendor_partial_inputs_rejected_before_file_access(
        self,
    ):

        from validate_submission import validate_submission

        expected_errors = [
            "Production governance requires either "
            "all four explicit governance paths "
            "or all authoritative repository defaults"
        ]

        with patch.object(
            Path,
            "open",
            side_effect=AssertionError(
                "Unexpected submission or governance file access"
            ),
        ) as file_open, patch.object(
            Path,
            "is_file",
            side_effect=AssertionError(
                "Unexpected submission or governance file inspection"
            ),
        ) as file_check, patch.object(
            Path,
            "is_dir",
            side_effect=AssertionError(
                "Unexpected governance directory inspection"
            ),
        ) as directory_check:

            errors = validate_submission(
                self.registry_path.parent,
                production=True,
                registry_path=self.registry_path,
            )

            self.assertEqual(
                errors,
                expected_errors,
            )

            file_open.assert_not_called()
            file_check.assert_not_called()
            directory_check.assert_not_called()





if __name__ == "__main__":

    unittest.main(verbosity=2)
