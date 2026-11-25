import hashlib
import sys
from pathlib import Path

from validate_reference_audit import (
    AUDIT_FILE,
    TECHNICAL_REVIEW_EVIDENCE_FIELDS,
    load_audit_registry,
    validate_live_audit_data,
)

from validate_technical_review_records import (
    extract_review_record_fields,
    get_review_record_path,
)


REPOSITORY_ROOT = (
    Path(__file__).resolve().parent.parent
)

APPROVALS_DIRECTORY = (
    REPOSITORY_ROOT / "approvals"
)


AUDIT_MATCHED_FIELDS = {
    "Reference Home ID":
        "reference_home_id",
    "Reference Home Version":
        "reference_home_version",
    "Technical Review Record ID":
        "technical_review_record",
    "Technical Reviewer":
        "reviewer",
    "Technical Review Date":
        "technical_review_date",
    "Reviewed Content SHA-256":
        "reviewed_content_sha256",
}


VALID_RECOMMENDATIONS = {
    "RECOMMEND_APPROVAL",
    "REVISIONS_REQUIRED",
}


def build_review_path_metadata(record):
    """
    Construct the metadata required by the existing
    safe technical review document path helper.

    Use the audit record rather than the home's
    current technical review assignment.
    """

    return {
        "test_home_id":
            record["reference_home_id"],
        "test_home_version":
            record["reference_home_version"],
        "review": {
            "review_record":
                record["technical_review_record"],
        },
    }


def validate_document_checksum(record, document_bytes):
    """
    Compare the recorded checksum against the
    original supporting document bytes.
    """

    actual_checksum = hashlib.sha256(
        document_bytes
    ).hexdigest()

    expected_checksum = record[
        "technical_review_sha256"
    ]

    if actual_checksum != expected_checksum:

        return [
            "Technical review document SHA-256 "
            "checksum mismatch"
        ]

    return []


def validate_document_metadata(record, content):
    """
    Compare supporting document metadata against
    the audit decision and its review evidence.
    """

    fields, errors = extract_review_record_fields(
        content
    )

    for document_field, audit_field in (
        AUDIT_MATCHED_FIELDS.items()
    ):

        if document_field not in fields:
            continue

        if fields[document_field] != record[audit_field]:

            errors.append(
                "Technical review document "
                f"mismatched {document_field}"
            )

    if "Technical Review Status" in fields:

        if fields["Technical Review Status"] != "COMPLETED":

            errors.append(
                "Audit review evidence requires "
                "COMPLETED technical review status"
            )

    if "Review Recommendation" in fields:

        recommendation = fields[
            "Review Recommendation"
        ]

        if recommendation not in VALID_RECOMMENDATIONS:

            errors.append(
                "Invalid technical review "
                "document recommendation"
            )

        elif record["decision"] in {
            "APPROVED",
            "RETIRED",
        }:

            if recommendation != "RECOMMEND_APPROVAL":

                errors.append(
                    f"{record['decision']} audit decision "
                    "requires RECOMMEND_APPROVAL"
                )

    return errors


def validate_audit_record_evidence(
    record,
    approvals_directory,
):
    """
    Validate the supporting technical review document
    for a schema-validated audit record.

    REJECTED decisions with all-null review evidence
    do not require a completed review document.
    """

    if all(
        record[field] is None
        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS
    ):

        if record["decision"] == "REJECTED":
            return []

        return [
            "Complete technical review evidence "
            "is required"
        ]

    if any(
        record[field] is None
        for field in TECHNICAL_REVIEW_EVIDENCE_FIELDS
    ):

        return [
            "Partial technical review evidence "
            "is not permitted"
        ]

    try:

        path_metadata = build_review_path_metadata(
            record
        )

        record_path = get_review_record_path(
            path_metadata,
            approvals_directory,
        )

        if not record_path.is_file():

            return [
                "Missing technical review "
                f"document: {record_path}"
            ]

        document_bytes = record_path.read_bytes()

        errors = validate_document_checksum(
            record,
            document_bytes,
        )

        content = document_bytes.decode("utf-8")

        errors.extend(
            validate_document_metadata(
                record,
                content,
            )
        )

        return errors

    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
    ) as exc:

        return [
            "Unable to access technical review "
            f"document: {exc}"
        ]


def validate_audit_review_evidence_data(
    audit,
    approvals_directory,
):
    """
    Validate the live audit schema before verifying
    supporting technical review document evidence.
    """

    errors = validate_live_audit_data(audit)

    if errors:
        return errors

    errors = []

    for index, record in enumerate(
        audit["records"],
        start=1,
    ):

        record_id = record["record_id"]

        record_errors = (
            validate_audit_record_evidence(
                record,
                approvals_directory,
            )
        )

        errors.extend(
            f"Record {index} ({record_id}): {error}"
            for error in record_errors
        )

    return errors


def validate_audit_review_evidence(
    audit_path=None,
    approvals_directory=None,
):
    """
    Load the live approval audit registry and
    verify its supporting technical review evidence.
    """

    if audit_path is None:

        audit_path = AUDIT_FILE

    if approvals_directory is None:

        approvals_directory = APPROVALS_DIRECTORY

    try:

        audit_path = Path(audit_path)

        if audit_path.is_symlink():

            return [
                "Audit registry cannot be "
                "a symbolic link"
            ]

        approvals_directory = Path(
            approvals_directory
        )

        if approvals_directory.is_symlink():

            return [
                "Approvals directory cannot be "
                "a symbolic link"
            ]

        if not approvals_directory.is_dir():

            return [
                "Approvals directory does not exist"
            ]

        audit = load_audit_registry(
            audit_path
        )

        return validate_audit_review_evidence_data(
            audit,
            approvals_directory,
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        RuntimeError,
    ) as exc:

        return [
            "Unable to validate audit review "
            f"evidence: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) not in {1, 3}:

        print(
            "Usage: python "
            "validate_audit_review_evidence.py "
            "[audit-path approvals-directory]"
        )

        sys.exit(2)

    audit_path = (
        sys.argv[1]
        if len(sys.argv) == 3
        else None
    )

    approvals_directory = (
        sys.argv[2]
        if len(sys.argv) == 3
        else None
    )

    validation_errors = (
        validate_audit_review_evidence(
            audit_path,
            approvals_directory,
        )
    )

    if validation_errors:

        print(
            "AUDIT REVIEW EVIDENCE "
            "VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "AUDIT REVIEW EVIDENCE "
        "VALIDATION PASSED"
    )

    sys.exit(0)
