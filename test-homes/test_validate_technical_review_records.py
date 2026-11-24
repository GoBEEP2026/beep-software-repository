import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_technical_review import (
    calculate_technical_fingerprint,
)

from validate_technical_review_records import (
    is_valid_record_value,
    extract_review_record_fields,
    validate_review_record_content,
    get_review_record_path,
    validate_technical_review_record,
    validate_technical_review_records,
)


class TestTechnicalReviewRecords(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.approvals = self.root / "approvals"

    def make_home(self):
        home = {
            "test_home_id": "BEEP-HOME-TEST",
            "test_home_version": "1.0.0",
            "status": "UNDER_REVIEW",
            "conditioned_floor_area_ft2": 2200,
            "review": {
                "reviewer": "Fictional Test Reviewer",
                "review_record": "BEEP-REV-TEST-001",
                "review_status": "COMPLETED",
                "review_date": "2026-01-15",
                "review_findings": "Fictional test findings.",
                "review_recommendation": "RECOMMEND_APPROVAL",
                "conflict_of_interest_disclosure":
                    "No conflicts in this fictional test.",
                "reviewed_content_sha256": None,
            },
        }

        home["review"]["reviewed_content_sha256"] = (
            calculate_technical_fingerprint(home)
        )

        return home

    def make_document(self, home):
        review = home["review"]

        fields = {
            "Reference Home ID":
                home["test_home_id"],
            "Reference Home Version":
                home["test_home_version"],
            "Technical Review Record ID":
                review["review_record"],
            "Technical Reviewer":
                review["reviewer"],
            "Technical Review Date":
                review["review_date"],
            "Technical Review Status":
                review["review_status"],
            "Review Scope":
                "Fictional geometry and envelope review.",
            "Review Findings":
                review["review_findings"],
            "Review Recommendation":
                review["review_recommendation"],
            "Conflict-of-Interest Disclosure":
                review["conflict_of_interest_disclosure"],
            "Reviewed Content SHA-256":
                review["reviewed_content_sha256"],
            "Supporting Evidence":
                "Fictional supporting evidence.",
        }

        return "\n".join(
            f"{key}: {value}"
            for key, value in fields.items()
        ) + "\n"

    def write_document(self, home, content=None):
        path = get_review_record_path(
            home, self.approvals
        )

        path.parent.mkdir(
            parents=True, exist_ok=True
        )

        if content is None:
            content = self.make_document(home)

        path.write_text(
            content, encoding="utf-8"
        )

        return path

    def write_registry(self, homes):
        path = self.root / "registry.json"

        path.write_text(
            json.dumps({
                "reference_homes": homes
            }),
            encoding="utf-8",
        )

        return path

    def assert_error(self, errors, expected):
        self.assertTrue(
            any(expected in error for error in errors),
            errors,
        )

    def check_mismatch(self, field):
        home = self.make_home()
        document = self.make_document(home)

        modified = "\n".join(
            f"{field}: Incorrect fictional value"
            if line.startswith(f"{field}:")
            else line
            for line in document.splitlines()
        )

        errors = validate_review_record_content(
            home, modified
        )

        self.assert_error(
            errors, f"mismatched {field}"
        )

    # Record value validation: 7 tests

    def test_valid_value(self):
        self.assertTrue(
            is_valid_record_value("Valid test value")
        )

    def test_empty_value(self):
        self.assertFalse(
            is_valid_record_value("")
        )

    def test_whitespace_value(self):
        self.assertFalse(
            is_valid_record_value("   ")
        )

    def test_non_string_value(self):
        self.assertFalse(
            is_valid_record_value(None)
        )

    def test_multiline_value(self):
        self.assertFalse(
            is_valid_record_value("First\nSecond")
        )

    def test_recognized_placeholders(self):
        for value in (
            "TBD", "pending", "TODO",
            "required", "YYYY-MM-DD",
        ):
            with self.subTest(value=value):
                self.assertFalse(
                    is_valid_record_value(value)
                )

    def test_bracketed_placeholder(self):
        self.assertFalse(
            is_valid_record_value("[Reviewer name]")
        )

    # Document field extraction: 7 tests

    def test_extract_all_fields(self):
        fields, errors = extract_review_record_fields(
            self.make_document(self.make_home())
        )

        self.assertEqual(errors, [])
        self.assertEqual(len(fields), 12)

    def test_missing_field(self):
        document = self.make_document(
            self.make_home()
        )

        document = "\n".join(
            line for line in document.splitlines()
            if not line.startswith("Review Scope:")
        )

        _, errors = extract_review_record_fields(
            document
        )

        self.assert_error(
            errors, "Missing required field: Review Scope"
        )

    def test_duplicate_field(self):
        document = self.make_document(
            self.make_home()
        )

        document += "Review Scope: Duplicate scope\n"

        _, errors = extract_review_record_fields(
            document
        )

        self.assert_error(
            errors, "Duplicate required field: Review Scope"
        )

    def test_case_insensitive_duplicate(self):
        document = self.make_document(
            self.make_home()
        )

        document += "review scope: Duplicate scope\n"

        _, errors = extract_review_record_fields(
            document
        )

        self.assert_error(
            errors, "Duplicate required field: Review Scope"
        )

    def test_empty_field(self):
        document = self.make_document(
            self.make_home()
        ).replace(
            "Supporting Evidence: Fictional supporting evidence.",
            "Supporting Evidence:",
        )

        _, errors = extract_review_record_fields(
            document
        )

        self.assert_error(
            errors, "Invalid or placeholder value"
        )

    def test_placeholder_field(self):
        document = self.make_document(
            self.make_home()
        ).replace(
            "Supporting Evidence: Fictional supporting evidence.",
            "Supporting Evidence: TBD",
        )

        _, errors = extract_review_record_fields(
            document
        )

        self.assert_error(
            errors, "Invalid or placeholder value"
        )

    def test_non_text_document(self):
        _, errors = extract_review_record_fields(
            None
        )

        self.assertTrue(errors)

    # Registry and document consistency: 11 tests

    def test_matching_document(self):
        home = self.make_home()

        self.assertEqual(
            validate_review_record_content(
                home, self.make_document(home)
            ),
            [],
        )

    def test_home_id_mismatch(self):
        self.check_mismatch("Reference Home ID")

    def test_version_mismatch(self):
        self.check_mismatch("Reference Home Version")

    def test_record_id_mismatch(self):
        self.check_mismatch(
            "Technical Review Record ID"
        )

    def test_reviewer_mismatch(self):
        self.check_mismatch("Technical Reviewer")

    def test_review_date_mismatch(self):
        self.check_mismatch("Technical Review Date")

    def test_review_status_mismatch(self):
        self.check_mismatch("Technical Review Status")

    def test_findings_mismatch(self):
        self.check_mismatch("Review Findings")

    def test_recommendation_mismatch(self):
        self.check_mismatch("Review Recommendation")

    def test_conflict_disclosure_mismatch(self):
        self.check_mismatch(
            "Conflict-of-Interest Disclosure"
        )

    def test_fingerprint_mismatch(self):
        self.check_mismatch(
            "Reviewed Content SHA-256"
        )

    # Document path safeguards: 6 tests

    def test_valid_document_path(self):
        home = self.make_home()

        expected = (
            self.approvals
            / "BEEP-HOME-TEST"
            / "1.0.0"
            / "technical-reviews"
            / "BEEP-REV-TEST-001.md"
        )

        self.assertEqual(
            get_review_record_path(
                home, self.approvals
            ),
            expected,
        )

    def test_unsafe_home_identifier(self):
        home = self.make_home()
        home["test_home_id"] = "../outside"

        with self.assertRaises(ValueError):
            get_review_record_path(
                home, self.approvals
            )

    def test_unsafe_version(self):
        home = self.make_home()
        home["test_home_version"] = "../outside"

        with self.assertRaises(ValueError):
            get_review_record_path(
                home, self.approvals
            )

    def test_unsafe_record_identifier(self):
        home = self.make_home()
        home["review"]["review_record"] = "../outside"

        with self.assertRaises(ValueError):
            get_review_record_path(
                home, self.approvals
            )

    def test_document_symbolic_link(self):
        home = self.make_home()
        path = self.write_document(home)

        target = self.root / "target.md"
        path.rename(target)
        path.symlink_to(target)

        with self.assertRaises(ValueError):
            get_review_record_path(
                home, self.approvals
            )

    def test_parent_directory_symbolic_link(self):
        home = self.make_home()
        path = self.write_document(home)

        directory = path.parent
        target = self.root / "moved-reviews"

        directory.rename(target)

        directory.symlink_to(
            target, target_is_directory=True
        )

        with self.assertRaises(ValueError):
            get_review_record_path(
                home, self.approvals
            )

    # Individual review validation: 7 tests

    def test_completed_review_with_document(self):
        home = self.make_home()
        self.write_document(home)

        self.assertEqual(
            validate_technical_review_record(
                home, self.approvals
            ),
            [],
        )

    def test_completed_review_without_document(self):
        home = self.make_home()

        self.assert_error(
            validate_technical_review_record(
                home, self.approvals
            ),
            "Missing technical review document",
        )

    def test_approved_review_with_document(self):
        home = self.make_home()
        home["status"] = "APPROVED"

        self.write_document(home)

        self.assertEqual(
            validate_technical_review_record(
                home, self.approvals
            ),
            [],
        )

    def test_retired_review_without_document(self):
        home = self.make_home()
        home["status"] = "RETIRED"

        self.assert_error(
            validate_technical_review_record(
                home, self.approvals
            ),
            "Missing technical review document",
        )

    def test_changed_technical_content(self):
        home = self.make_home()
        self.write_document(home)

        home["conditioned_floor_area_ft2"] = 2400

        self.assert_error(
            validate_technical_review_record(
                home, self.approvals
            ),
            "fingerprint does not match",
        )

    def test_development_review_exempt(self):
        home = self.make_home()
        home["status"] = "DEVELOPMENT"

        for field in home["review"]:
            home["review"][field] = None

        home["review"]["review_status"] = "NOT_STARTED"

        self.assertEqual(
            validate_technical_review_record(
                home, self.approvals
            ),
            [],
        )

    def test_in_progress_review_exempt(self):
        home = self.make_home()

        review = home["review"]
        review["review_status"] = "IN_PROGRESS"
        review["review_date"] = None
        review["review_recommendation"] = None
        review["reviewed_content_sha256"] = None

        self.assertEqual(
            validate_technical_review_record(
                home, self.approvals
            ),
            [],
        )

    # Registry-wide validation: 2 tests

    def test_multiple_versions_require_documents(self):
        first = self.make_home()
        second = self.make_home()

        second["test_home_version"] = "1.0.1"

        second["review"]["review_record"] = (
            "BEEP-REV-TEST-002"
        )

        second["review"]["reviewed_content_sha256"] = (
            calculate_technical_fingerprint(second)
        )

        self.write_document(first)

        registry = self.write_registry(
            [first, second]
        )

        errors = validate_technical_review_records(
            registry, self.approvals
        )

        self.assert_error(
            errors, "Missing technical review document"
        )

        self.write_document(second)

        self.assertEqual(
            validate_technical_review_records(
                registry, self.approvals
            ),
            [],
        )

    def test_validation_does_not_modify_input(self):
        home = self.make_home()
        original = copy.deepcopy(home)

        self.write_document(home)

        validate_technical_review_record(
            home, self.approvals
        )

        self.assertEqual(home, original)


if __name__ == "__main__":
    unittest.main()
