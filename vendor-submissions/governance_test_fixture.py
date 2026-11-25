
"""
Reusable fictional governance evidence for unit testing.

This module creates temporary test records only.
It does not represent an actual technical review,
Board decision, or approved reference home.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
TEST_HOMES_DIRECTORY = REPOSITORY_ROOT / "test-homes"

if str(TEST_HOMES_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TEST_HOMES_DIRECTORY))


from validate_technical_review import (
    calculate_technical_fingerprint,
)

from validate_review_identifiers import (
    SCHEMA_VERSION,
    REGISTRY_NAME,
    GOVERNANCE_AUTHORITY,
    EXPECTED_POLICY,
)


HOME_ID = "BEEP-HOME-001"
HOME_VERSION = "1.0.0"

REVIEWER = "Test Technical Reviewer"
REVIEW_RECORD = "TEST-REVIEW-001"

ASSIGNMENT_DATE = "2026-11-15"
REVIEW_DATE = "2026-11-16"
APPROVAL_DATE = "2026-11-17"

APPROVAL_RECORD = "TEST-APPROVAL-001"
BOARD_RESOLUTION = "TEST-BOARD-RES-001"

TEST_CYCLE = "TEST-CYCLE-001"

REVIEW_FINDINGS = (
    "Fictional technical review completed for unit testing"
)

CONFLICT_DISCLOSURE = (
    "No conflicts disclosed for fictional test"
)


def write_json(path, data):
    """Write a temporary JSON test document."""

    path = Path(path)

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )


def calculate_file_sha256(path):
    """Calculate SHA-256 from actual file bytes."""

    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def create_governance_fixture(directory):
    """
    Create complete fictional governance evidence.

    The supplied directory must be a dedicated
    temporary test location.

    Never use this function to create live
    repository approval records.
    """

    root = Path(directory).resolve()

    repository_root = REPOSITORY_ROOT.resolve()

    if (
        root == repository_root
        or root.is_relative_to(repository_root)
    ):
        raise ValueError(
            "Governance fixtures cannot be created "
            "inside the live repository"
        )

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_homes = root / "test-homes"
    approvals = root / "approvals"

    test_homes.mkdir(exist_ok=False)
    approvals.mkdir(exist_ok=False)

    registry_path = (
        test_homes
        / "reference-home-registry.json"
    )

    audit_path = (
        test_homes
        / "reference-approval-audit.json"
    )

    identifier_registry_path = (
        test_homes
        / "reference-review-identifier-registry.json"
    )

    # Load the existing reference home definition.

    source_registry = (
        TEST_HOMES_DIRECTORY
        / "reference-home-registry.json"
    )

    registry = json.loads(
        source_registry.read_text(
            encoding="utf-8"
        )
    )

    matching_homes = [
        home
        for home in registry["reference_homes"]
        if home["test_home_id"] == HOME_ID
        and home["test_home_version"] == HOME_VERSION
    ]

    if len(matching_homes) != 1:
        raise ValueError(
            "Expected exactly one matching "
            "reference home version"
        )

    home = matching_homes[0]

    # Isolate the fictional reference home.

    registry["reference_homes"] = [home]
    registry["registry_status"] = "APPROVED"

    # Copy reference files and calculate real hashes.

    reference_paths = []

    for entry in home["reference_files"]:

        filename = entry["filename"]

        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or filename in (".", "..")
            or "/" in filename
            or "\\" in filename
        ):
            raise ValueError(
                "Unsafe reference fixture filename"
            )

        source = (
            TEST_HOMES_DIRECTORY / filename
        )

        if (
            source.is_symlink()
            or not source.is_file()
        ):
            raise ValueError(
                "Invalid source reference file"
            )

        destination = test_homes / filename

        shutil.copyfile(
            source,
            destination,
        )

        entry["sha256"] = calculate_file_sha256(
            destination
        )

        reference_paths.append(destination)

    # Establish fictional completed review metadata.

    home["status"] = "APPROVED"

    home["review"] = {
        "reviewer": REVIEWER,
        "review_record": REVIEW_RECORD,
        "review_status": "COMPLETED",
        "review_date": REVIEW_DATE,
        "review_findings": REVIEW_FINDINGS,
        "review_recommendation": "RECOMMEND_APPROVAL",
        "conflict_of_interest_disclosure":
            CONFLICT_DISCLOSURE,
        "reviewed_content_sha256": None,
    }

    home["approval"] = {
        "approved_by": GOVERNANCE_AUTHORITY,
        "approval_date": APPROVAL_DATE,
        "approval_record": APPROVAL_RECORD,
        "board_resolution_reference": BOARD_RESOLUTION,
    }

    home["test_cycles"] = [
        TEST_CYCLE,
    ]

    fingerprint = calculate_technical_fingerprint(
        home
    )

    home["review"][
        "reviewed_content_sha256"
    ] = fingerprint

    write_json(
        registry_path,
        registry,
    )

    # Create version-specific supporting documents.

    approval_directory = (
        approvals
        / HOME_ID
        / HOME_VERSION
    )

    review_directory = (
        approval_directory
        / "technical-reviews"
    )

    review_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    review_document = (
        review_directory
        / f"{REVIEW_RECORD}.md"
    )

    review_document.write_text(
        "# Fictional Technical Review Record\n\n"
        f"Reference Home ID: {HOME_ID}\n"
        f"Reference Home Version: {HOME_VERSION}\n"
        f"Technical Review Record ID: {REVIEW_RECORD}\n"
        f"Technical Reviewer: {REVIEWER}\n"
        f"Technical Review Date: {REVIEW_DATE}\n"
        "Technical Review Status: COMPLETED\n"
        f"Review Findings: {REVIEW_FINDINGS}\n"
        "Review Recommendation: RECOMMEND_APPROVAL\n"
        "Conflict-of-Interest Disclosure: "
        f"{CONFLICT_DISCLOSURE}\n"
        f"Reviewed Content SHA-256: {fingerprint}\n"
        "Review Scope: Fictional reference home "
        "technical review\n"
        "Supporting Evidence: Temporary unit test "
        "reference home evidence\n\n"
        "This document is fictional and is intended "
        "exclusively for automated unit testing.\n",
        encoding="utf-8",
    )

    review_document_sha256 = (
        calculate_file_sha256(review_document)
    )

    # Create fictional Board approval documentation.

    approval_document = (
        approval_directory
        / "approval-record.md"
    )

    approval_document.write_text(
        "# B.E.E.P. Fictional Test Approval Record\n\n"
        f"Reference Home ID: {HOME_ID}\n"
        f"Reference Home Version: {HOME_VERSION}\n"
        f"Approval Record ID: {APPROVAL_RECORD}\n"
        "Approval Status: APPROVED\n"
        f"Approval Authority: {GOVERNANCE_AUTHORITY}\n"
        f"Board Resolution Reference: {BOARD_RESOLUTION}\n"
        f"Board Decision Date: {APPROVAL_DATE}\n\n"
        "This document does not represent an actual "
        "Board decision.\n",
        encoding="utf-8",
    )

    # Create the permanent identifier reservation.

    identifier_registry = {
        "registry_schema_version": SCHEMA_VERSION,
        "registry_status": "DEVELOPMENT",
        "registry_name": REGISTRY_NAME,
        "governance_authority": GOVERNANCE_AUTHORITY,
        "reservation_policy": dict(EXPECTED_POLICY),
        "reservations": [
            {
                "review_record_id": REVIEW_RECORD,
                "reference_home_id": HOME_ID,
                "reference_home_version": HOME_VERSION,
                "assigned_reviewer": REVIEWER,
                "assignment_date": ASSIGNMENT_DATE,
            }
        ],
    }

    write_json(
        identifier_registry_path,
        identifier_registry,
    )

    # Create schema 1.1.0 approval audit evidence.

    audit = {
        "audit_schema_version": "1.1.0",
        "repository":
            "BEEP Software Consistency Repository",
        "audit_status": "DEVELOPMENT",
        "description": (
            "Append-only audit records for reference-home "
            "review and approval decisions."
        ),
        "records": [
            {
                "record_id": APPROVAL_RECORD,
                "reference_home_id": HOME_ID,
                "reference_home_version": HOME_VERSION,
                "decision": "APPROVED",
                "reviewer": REVIEWER,
                "approval_authority":
                    GOVERNANCE_AUTHORITY,
                "evidence": "TEST-EVIDENCE-001",
                "pull_request": "TEST-PR-001",
                "decision_date": APPROVAL_DATE,
                "board_resolution_reference":
                    BOARD_RESOLUTION,
                "technical_review_record":
                    REVIEW_RECORD,
                "technical_review_date": REVIEW_DATE,
                "technical_review_sha256":
                    review_document_sha256,
                "reviewed_content_sha256":
                    fingerprint,
            }
        ],
    }

    write_json(
        audit_path,
        audit,
    )

    return {
        "registry_path": registry_path,
        "audit_path": audit_path,
        "identifier_registry_path":
            identifier_registry_path,
        "approvals_directory": approvals,
        "review_document": review_document,
        "approval_document": approval_document,
        "reference_paths": reference_paths,
        "technical_fingerprint": fingerprint,
        "review_document_sha256":
            review_document_sha256,
    }
