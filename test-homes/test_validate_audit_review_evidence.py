import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from validate_reference_audit import (
    AUDIT_DESCRIPTION,
    AUDIT_STATUS,
    CURRENT_SCHEMA_VERSION,
    GOVERNANCE_AUTHORITY,
    LEGACY_SCHEMA_VERSION,
    REPOSITORY_NAME,
    TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    validate_live_audit_data,
)

from validate_audit_review_evidence import (
    validate_audit_review_evidence,
    validate_audit_review_evidence_data,
)


class TestAuditReviewEvidence(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)

        self.approvals = self.root / "approvals"

        self.approvals.mkdir()

        self.audit_path = (
            self.root / "reference-approval-audit.json"
        )

    def make_record(self, decision="APPROVED"):

        return {
            "record_id": "BEEP-AUDIT-TEST-001",
            "reference_home_id": "BEEP-HOME-TEST",
            "reference_home_version": "1.0.0",
            "decision": decision,
            "reviewer": "Fictional Test Reviewer",
            "approval_authority": GOVERNANCE_AUTHORITY,
            "evidence": "Fictional supporting evidence",
            "pull_request": "TEST-PR-001",
            "board_resolution_reference": "BEEP-RES-TEST-001",
            "decision_date": "2026-01-25",
            "technical_review_record": "BEEP-REV-TEST-001",
            "technical_review_date": "2026-01-20",
            "technical_review_sha256": "a" * 64,
            "reviewed_content_sha256": "b" * 64,
        }

    def make_registry(self, records=None):

        return {
            "audit_schema_version": CURRENT_SCHEMA_VERSION,
            "repository": REPOSITORY_NAME,
            "audit_status": AUDIT_STATUS,
            "description": AUDIT_DESCRIPTION,
            "records": [] if records is None else records,
        }

    def make_document(
        self,
        record,
        recommendation="RECOMMEND_APPROVAL",
        status="COMPLETED",
    ):

        return (
            "# Fictional Technical Review\n"
            "\n"
            f"Reference Home ID: "
            f"{record['reference_home_id']}\n"
            f"Reference Home Version: "
            f"{record['reference_home_version']}\n"
            f"Technical Review Record ID: "
            f"{record['technical_review_record']}\n"
            f"Technical Reviewer: "
            f"{record['reviewer']}\n"
            f"Technical Review Date: "
            f"{record['technical_review_date']}\n"
            f"Technical Review Status: {status}\n"
            "Review Findings: Fictional test findings\n"
            f"Review Recommendation: {recommendation}\n"
            "Conflict-of-Interest Disclosure: "
            "No conflicts disclosed\n"
            f"Reviewed Content SHA-256: "
            f"{record['reviewed_content_sha256']}\n"
            "Review Scope: Fictional reference home review\n"
            "Supporting Evidence: Fictional test evidence\n"
        )

    def document_path(self, record):

        return (
            self.approvals
            / record["reference_home_id"]
            / record["reference_home_version"]
            / "technical-reviews"
            / f"{record['technical_review_record']}.md"
        )

    def write_document_bytes(self, record, data):

        path = self.document_path(record)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(data)

        record["technical_review_sha256"] = (
            hashlib.sha256(data).hexdigest()
        )

        return path

    def write_document(
        self,
        record,
        content=None,
        recommendation="RECOMMEND_APPROVAL",
        status="COMPLETED",
    ):

        if content is None:

            content = self.make_document(
                record,
                recommendation,
                status,
            )

        return self.write_document_bytes(
            record,
            content.encode("utf-8"),
        )

    def make_valid_fixture(self, decision="APPROVED"):

        record = self.make_record(decision)

        path = self.write_document(record)

        audit = self.make_registry([record])

        self.assertEqual(
            validate_live_audit_data(audit),
            [],
        )

        self.assert_accepted(audit)

        return audit, record, path

    def make_null_evidence_record(self):

        record = self.make_record("REJECTED")

        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS:

            record[field] = None

        return record

    def validate(self, audit):

        return validate_audit_review_evidence_data(
            audit,
            self.approvals,
        )

    def assert_accepted(self, audit):

        self.assertEqual(
            self.validate(audit),
            [],
        )

    def assert_rejected(self, audit, expected):

        errors = self.validate(audit)

        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected {expected!r}; got {errors}",
        )

    def assert_evidence_rejected(self, audit, expected):

        self.assertEqual(
            validate_live_audit_data(audit),
            [],
            "Audit schema must remain valid",
        )

        self.assert_rejected(audit, expected)

    def save_audit(self, audit):

        self.audit_path.write_text(
            json.dumps(audit, indent=2),
            encoding="utf-8",
        )

    # CATEGORY 1
    # VALID AUDIT EVIDENCE ACCEPTANCE

    def test_01_empty_audit_registry(self):

        self.assert_accepted(
            self.make_registry()
        )

    def test_02_valid_approved_evidence(self):

        audit, record, path = self.make_valid_fixture()

        self.assert_accepted(audit)

    def test_03_valid_retired_evidence(self):

        audit, record, path = (
            self.make_valid_fixture("RETIRED")
        )

        self.assert_accepted(audit)

    def test_04_valid_rejected_historical_evidence(self):

        record = self.make_record("REJECTED")

        self.write_document(
            record,
            recommendation="REVISIONS_REQUIRED",
        )

        self.assert_accepted(
            self.make_registry([record])
        )

    def test_05_rejected_all_null_evidence(self):

        self.assert_accepted(
            self.make_registry(
                [self.make_null_evidence_record()]
            )
        )

    # CATEGORY 2
    # DOCUMENT CHECKSUM VERIFICATION

    def test_06_modified_document_rejected(self):

        audit, record, path = self.make_valid_fixture()

        path.write_bytes(
            path.read_bytes()
            + b"\nUnauthorized modification\n"
        )

        self.assert_evidence_rejected(
            audit,
            "Technical review document SHA-256 "
            "checksum mismatch",
        )

    def test_07_incorrect_recorded_checksum(self):

        audit, record, path = self.make_valid_fixture()

        record["technical_review_sha256"] = "f" * 64

        self.assert_evidence_rejected(
            audit,
            "checksum mismatch",
        )

    def test_08_changed_line_endings_rejected(self):

        audit, record, path = self.make_valid_fixture()

        original = path.read_bytes()

        path.write_bytes(
            original.replace(b"\n", b"\r\n")
        )

        self.assert_evidence_rejected(
            audit,
            "checksum mismatch",
        )

    def test_09_exact_crlf_bytes_accepted(self):

        record = self.make_record()

        content = self.make_document(record)

        data = content.replace(
            "\n",
            "\r\n",
        ).encode("utf-8")

        self.write_document_bytes(
            record,
            data,
        )

        self.assert_accepted(
            self.make_registry([record])
        )

    def test_10_validation_preserves_original_data(self):

        audit, record, path = self.make_valid_fixture()

        original_audit = copy.deepcopy(audit)

        original_document = path.read_bytes()

        self.assert_accepted(audit)

        self.assertEqual(
            audit,
            original_audit,
        )

        self.assertEqual(
            path.read_bytes(),
            original_document,
        )

    # CATEGORY 3
    # DOCUMENT METADATA CONSISTENCY

    def test_11_reference_home_identifier_mismatch(self):

        audit, record, path = self.make_valid_fixture()

        content = self.make_document(record).replace(
            "Reference Home ID: BEEP-HOME-TEST",
            "Reference Home ID: BEEP-HOME-OTHER",
        )

        self.write_document(record, content)

        self.assert_evidence_rejected(
            audit,
            "mismatched Reference Home ID",
        )

    def test_12_reference_home_version_mismatch(self):

        audit, record, path = self.make_valid_fixture()

        content = self.make_document(record).replace(
            "Reference Home Version: 1.0.0",
            "Reference Home Version: 2.0.0",
        )

        self.write_document(record, content)

        self.assert_evidence_rejected(
            audit,
            "mismatched Reference Home Version",
        )

    def test_13_review_record_identifier_mismatch(self):

        audit, record, path = self.make_valid_fixture()

        content = self.make_document(record).replace(
            "Technical Review Record ID: BEEP-REV-TEST-001",
            "Technical Review Record ID: BEEP-REV-OTHER",
        )

        self.write_document(record, content)

        self.assert_evidence_rejected(
            audit,
            "mismatched Technical Review Record ID",
        )

    def test_14_reviewer_mismatch(self):

        audit, record, path = self.make_valid_fixture()

        content = self.make_document(record).replace(
            "Technical Reviewer: Fictional Test Reviewer",
            "Technical Reviewer: Different Test Reviewer",
        )

        self.write_document(record, content)

        self.assert_evidence_rejected(
            audit,
            "mismatched Technical Reviewer",
        )

    def test_15_date_and_fingerprint_mismatches(self):

        for field, replacement, expected in (
            (
                "technical_review_date",
                "2026-01-19",
                "mismatched Technical Review Date",
            ),
            (
                "reviewed_content_sha256",
                "c" * 64,
                "mismatched Reviewed Content SHA-256",
            ),
        ):

            with self.subTest(field=field):

                audit, record, path = (
                    self.make_valid_fixture()
                )

                record[field] = replacement

                self.assert_evidence_rejected(
                    audit,
                    expected,
                )

    # CATEGORY 4
    # REVIEW STATUS AND RECOMMENDATIONS

    def test_16_incomplete_review_status(self):

        audit, record, path = self.make_valid_fixture()

        self.write_document(
            record,
            status="IN_PROGRESS",
        )

        self.assert_evidence_rejected(
            audit,
            "requires COMPLETED technical review status",
        )

    def test_17_invalid_recommendation(self):

        audit, record, path = self.make_valid_fixture()

        self.write_document(
            record,
            recommendation="UNSUPPORTED",
        )

        self.assert_evidence_rejected(
            audit,
            "Invalid technical review document recommendation",
        )

    def test_18_approved_requires_recommend_approval(self):

        audit, record, path = self.make_valid_fixture()

        self.write_document(
            record,
            recommendation="REVISIONS_REQUIRED",
        )

        self.assert_evidence_rejected(
            audit,
            "APPROVED audit decision requires "
            "RECOMMEND_APPROVAL",
        )

    def test_19_retired_requires_recommend_approval(self):

        audit, record, path = (
            self.make_valid_fixture("RETIRED")
        )

        self.write_document(
            record,
            recommendation="REVISIONS_REQUIRED",
        )

        self.assert_evidence_rejected(
            audit,
            "RETIRED audit decision requires "
            "RECOMMEND_APPROVAL",
        )

    def test_20_rejected_allows_either_recommendation(self):

        for recommendation in (
            "RECOMMEND_APPROVAL",
            "REVISIONS_REQUIRED",
        ):

            with self.subTest(
                recommendation=recommendation
            ):

                record = self.make_record("REJECTED")

                self.write_document(
                    record,
                    recommendation=recommendation,
                )

                self.assert_accepted(
                    self.make_registry([record])
                )

    # CATEGORY 5
    # MISSING OR INVALID DOCUMENTS

    def test_21_missing_document(self):

        audit, record, path = self.make_valid_fixture()

        path.unlink()

        self.assert_evidence_rejected(
            audit,
            "Missing technical review document",
        )

    def test_22_missing_required_document_metadata(self):

        audit, record, path = self.make_valid_fixture()

        content = self.make_document(record).replace(
            "Review Scope: Fictional reference home review\n",
            "",
        )

        self.write_document(record, content)

        self.assert_evidence_rejected(
            audit,
            "Missing required field: Review Scope",
        )

    def test_23_duplicate_document_metadata(self):

        audit, record, path = self.make_valid_fixture()

        content = (
            self.make_document(record)
            + "Technical Reviewer: Duplicate Reviewer\n"
        )

        self.write_document(record, content)

        self.assert_evidence_rejected(
            audit,
            "Duplicate required field: Technical Reviewer",
        )

    def test_24_placeholder_document_metadata(self):

        audit, record, path = self.make_valid_fixture()

        content = self.make_document(record).replace(
            "Review Findings: Fictional test findings",
            "Review Findings: TBD",
        )

        self.write_document(record, content)

        self.assert_evidence_rejected(
            audit,
            "Invalid or placeholder value for Review Findings",
        )

    def test_25_invalid_utf8_document(self):

        audit, record, path = self.make_valid_fixture()

        self.write_document_bytes(
            record,
            b"\xff\xfe\xfa",
        )

        self.assert_evidence_rejected(
            audit,
            "Unable to access technical review document",
        )

    # CATEGORY 6
    # PATH SECURITY

    def test_26_document_symbolic_link_rejected(self):

        audit, record, path = self.make_valid_fixture()

        target = self.root / "external-document.md"

        target.write_bytes(path.read_bytes())

        path.unlink()

        path.symlink_to(target)

        self.assert_evidence_rejected(
            audit,
            "cannot contain symbolic links",
        )

    def test_27_parent_directory_symbolic_link(self):

        audit, record, path = self.make_valid_fixture()

        parent = path.parent

        target = self.root / "external-reviews"

        parent.rename(target)

        parent.symlink_to(
            target,
            target_is_directory=True,
        )

        self.assert_evidence_rejected(
            audit,
            "cannot contain symbolic links",
        )

    def test_28_approvals_root_symbolic_link(self):

        audit, record, path = self.make_valid_fixture()

        target = self.root / "external-approvals"

        self.approvals.rename(target)

        self.approvals.symlink_to(
            target,
            target_is_directory=True,
        )

        self.assert_evidence_rejected(
            audit,
            "cannot contain symbolic links",
        )

    def test_29_directory_traversal_identifiers(self):

        for field in (
            "reference_home_id",
            "reference_home_version",
            "technical_review_record",
        ):

            with self.subTest(field=field):

                record = self.make_record()

                record[field] = "../outside"

                audit = self.make_registry([record])

                schema_errors = (
                    validate_live_audit_data(audit)
                )

                self.assertTrue(schema_errors)

                self.assertEqual(
                    self.validate(audit),
                    schema_errors,
                )

    def test_30_directory_instead_of_document(self):

        audit, record, path = self.make_valid_fixture()

        path.unlink()

        path.mkdir()

        self.assert_evidence_rejected(
            audit,
            "Missing technical review document",
        )

    # CATEGORY 7
    # AUDIT SCHEMA ENFORCEMENT

    def test_31_legacy_live_schema_rejected(self):

        audit = self.make_registry()

        audit["audit_schema_version"] = (
            LEGACY_SCHEMA_VERSION
        )

        self.assert_rejected(
            audit,
            "Live audit registry must use schema version",
        )

    def test_32_missing_review_evidence_fields(self):

        audit, record, path = self.make_valid_fixture()

        del record["technical_review_sha256"]

        self.assert_rejected(
            audit,
            "Missing technical_review_sha256",
        )

    def test_33_approved_null_review_evidence(self):

        record = self.make_null_evidence_record()

        record["decision"] = "APPROVED"

        self.assert_rejected(
            self.make_registry([record]),
            "APPROVED audit decisions require "
            "complete technical review evidence",
        )

    def test_34_rejected_partial_review_evidence(self):

        audit, record, path = (
            self.make_valid_fixture("REJECTED")
        )

        record["technical_review_sha256"] = None

        self.assert_rejected(
            audit,
            "REJECTED audit decisions require either "
            "complete technical review evidence "
            "or all-null evidence",
        )

    def test_35_invalid_audit_registry_structure(self):

        for audit in (
            None,
            [],
            "invalid",
        ):

            with self.subTest(audit=audit):

                self.assertEqual(
                    self.validate(audit),
                    ["Audit log must be a JSON object"],
                )

    # CATEGORY 8
    # FILE-BASED VALIDATION

    def test_36_valid_audit_registry_file(self):

        audit, record, path = self.make_valid_fixture()

        self.save_audit(audit)

        self.assertEqual(
            validate_audit_review_evidence(
                self.audit_path,
                self.approvals,
            ),
            [],
        )

    def test_37_missing_audit_registry_file(self):

        errors = validate_audit_review_evidence(
            self.audit_path,
            self.approvals,
        )

        self.assertTrue(
            any(
                "Unable to validate audit review evidence"
                in error
                for error in errors
            ),
            errors,
        )

    def test_38_malformed_or_duplicate_json_keys(self):

        for content, expected in (
            (
                "{invalid JSON",
                "Unable to validate audit review evidence",
            ),
            (
                '{"audit_schema_version": "1.0.0",'
                '"audit_schema_version": "1.1.0"}',
                "Duplicate JSON key",
            ),
        ):

            with self.subTest(content=content):

                self.audit_path.write_text(
                    content,
                    encoding="utf-8",
                )

                errors = validate_audit_review_evidence(
                    self.audit_path,
                    self.approvals,
                )

                self.assertTrue(
                    any(
                        expected in error
                        for error in errors
                    ),
                    errors,
                )

    def test_39_audit_registry_symbolic_link(self):

        target = self.root / "external-audit.json"

        target.write_text(
            json.dumps(self.make_registry()),
            encoding="utf-8",
        )

        self.audit_path.symlink_to(target)

        self.assertEqual(
            validate_audit_review_evidence(
                self.audit_path,
                self.approvals,
            ),
            [
                "Audit registry cannot be a symbolic link"
            ],
        )

    def test_40_invalid_approvals_directory(self):

        self.save_audit(
            self.make_registry()
        )

        missing = self.root / "missing-approvals"

        self.assertEqual(
            validate_audit_review_evidence(
                self.audit_path,
                missing,
            ),
            [
                "Approvals directory does not exist"
            ],
        )

        link = self.root / "linked-approvals"

        link.symlink_to(
            self.approvals,
            target_is_directory=True,
        )

        self.assertEqual(
            validate_audit_review_evidence(
                self.audit_path,
                link,
            ),
            [
                "Approvals directory cannot be a symbolic link"
            ],
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
