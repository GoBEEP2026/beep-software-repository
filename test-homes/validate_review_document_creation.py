import json
import subprocess
import sys
from pathlib import Path

from validate_review_identifiers import (
    load_identifier_registry,
    reject_duplicate_json_keys,
)

from validate_review_assignment_history import (
    REFERENCE_REGISTRY_RELATIVE_PATH,
    build_home_lookup,
    get_current_registry_path,
    load_historical_reference_registry,
    validate_review_assignment_history,
)

from validate_review_identifier_history import (
    REGISTRY_RELATIVE_PATH,
)

from validate_review_document_reservations import (
    discover_review_documents,
    parse_review_document_path,
    validate_document_reservation_data,
)

from validate_technical_review_records import (
    validate_review_record_content,
)

from validate_technical_review_record_history import (
    COMMIT_PATTERN,
    load_historical_review_records,
    validate_preserved_review_records,
)

from validate_technical_review_history import (
    validate_historical_review_transition,
)

from validate_technical_review import (
    validate_review_fingerprint,
)


def validate_document_creation_data(
    previous_homes,
    current_homes,
    previous_document_paths,
    current_documents,
):
    """
    Authorize new technical review documents
    only when a legitimate review completion
    transition has occurred.
    """

    if not isinstance(previous_homes, dict):

        return [
            "Historical reference home lookup "
            "must be a dictionary"
        ]

    if not isinstance(current_homes, dict):

        return [
            "Current reference home lookup "
            "must be a dictionary"
        ]

    if not isinstance(
        previous_document_paths,
        (set, frozenset),
    ):

        return [
            "Historical document paths "
            "must be a set"
        ]

    if not isinstance(current_documents, dict):

        return [
            "Current technical review documents "
            "must be a dictionary"
        ]

    errors = []

    authorized_paths = set()

    for home_key, current_home in (
        current_homes.items()
    ):

        if not isinstance(current_home, dict):

            errors.append(
                "Invalid current reference home"
            )

            continue

        home_id = current_home.get(
            "test_home_id"
        )

        version = current_home.get(
            "test_home_version"
        )

        prefix = f"{home_id}/{version}"

        if home_key != (home_id, version):

            errors.append(
                f"{prefix}: Reference home lookup "
                "identity mismatch"
            )

            continue

        fingerprint_errors = (
            validate_review_fingerprint(
                current_home
            )
        )

        if fingerprint_errors:

            errors.extend(
                f"{prefix}: {error}"
                for error in fingerprint_errors
            )

            continue

        current_review = current_home.get(
            "review"
        )

        if (
            current_review["review_status"]
            != "COMPLETED"
        ):

            continue

        record_id = current_review[
            "review_record"
        ]

        document_path = (
            f"{home_id}/{version}/"
            f"technical-reviews/{record_id}.md"
        )

        try:

            parse_review_document_path(
                document_path
            )

        except (ValueError, TypeError) as exc:

            errors.append(
                f"{prefix}: {exc}"
            )

            continue

        if document_path not in current_documents:

            errors.append(
                f"{prefix}: Completed technical "
                "review requires a supporting "
                f"document: {document_path}"
            )

            continue

        document_errors = (
            validate_review_record_content(
                current_home,
                current_documents[document_path],
            )
        )

        if document_errors:

            errors.extend(
                f"{document_path}: {error}"
                for error in document_errors
            )

            continue

        previous_home = previous_homes.get(
            home_key
        )

        if not isinstance(previous_home, dict):

            errors.append(
                f"{prefix}: Completed technical "
                "review requires a historical "
                "reference home"
            )

            continue

        transition_errors = (
            validate_historical_review_transition(
                previous_home,
                current_home,
            )
        )

        if transition_errors:

            errors.extend(
                f"{prefix}: {error}"
                for error in transition_errors
            )

            continue

        previous_review = previous_home.get(
            "review"
        )

        if not isinstance(previous_review, dict):

            errors.append(
                f"{prefix}: Completed technical "
                "review requires a historical "
                "review assignment"
            )

            continue

        previous_status = previous_review.get(
            "review_status"
        )

        if document_path in previous_document_paths:

            if previous_status != "COMPLETED":

                errors.append(
                    f"{prefix}: Existing historical "
                    "document cannot be reused for "
                    "a new review completion"
                )

            continue

        if previous_status != "IN_PROGRESS":

            errors.append(
                f"{prefix}: New technical review "
                "document requires an IN_PROGRESS "
                "to COMPLETED transition"
            )

            continue

        if (
            previous_review.get("review_record")
            != record_id
        ):

            errors.append(
                f"{prefix}: Technical review "
                "identifier changed during "
                "review completion"
            )

            continue

        if (
            previous_review.get("reviewer")
            != current_review["reviewer"]
        ):

            errors.append(
                f"{prefix}: Assigned technical "
                "reviewer changed during "
                "review completion"
            )

            continue

        authorized_paths.add(
            document_path
        )

    for document_path in current_documents:

        if not isinstance(document_path, str):

            errors.append(
                "Invalid technical review "
                "document path"
            )

            continue

        try:

            parse_review_document_path(
                document_path
            )

        except (ValueError, TypeError) as exc:

            errors.append(
                f"{document_path}: {exc}"
            )

            continue

        if document_path in previous_document_paths:

            continue

        if document_path not in authorized_paths:

            errors.append(
                "New technical review document "
                "has no authorized review "
                f"completion transition: "
                f"{document_path}"
            )

    for document_path in previous_document_paths:

        if document_path not in current_documents:

            errors.append(
                "Historical technical review "
                "document cannot be removed: "
                f"{document_path}"
            )

    return errors


def validate_review_document_creation(
    base_commit,
    repository_root=None,
):
    """
    Compare historical and current repository
    records to authorize new technical review
    supporting documents.
    """

    if (
        not isinstance(base_commit, str)
        or not COMMIT_PATTERN.fullmatch(
            base_commit
        )
    ):

        return [
            "Invalid historical Git commit "
            "identifier"
        ]

    if repository_root is None:

        repository_root = (
            Path(__file__).resolve().parent.parent
        )

    repository_root = Path(
        repository_root
    ).resolve()

    try:

        assignment_errors = (
            validate_review_assignment_history(
                base_commit,
                repository_root,
            )
        )

        if assignment_errors:

            return assignment_errors

        previous_records = (
            load_historical_review_records(
                repository_root,
                base_commit,
            )
        )

        preservation_errors = (
            validate_preserved_review_records(
                previous_records,
                repository_root,
            )
        )

        if preservation_errors:

            return preservation_errors

        previous_registry = (
            load_historical_reference_registry(
                repository_root,
                base_commit,
            )
        )

        previous_homes = build_home_lookup(
            previous_registry,
            "Historical",
        )

        current_registry_path = (
            get_current_registry_path(
                repository_root,
                REFERENCE_REGISTRY_RELATIVE_PATH,
            )
        )

        current_registry = json.loads(
            current_registry_path.read_text(
                encoding="utf-8"
            ),
            object_pairs_hook=(
                reject_duplicate_json_keys
            ),
        )

        current_homes = build_home_lookup(
            current_registry,
            "Current",
        )

        identifier_registry_path = (
            get_current_registry_path(
                repository_root,
                REGISTRY_RELATIVE_PATH,
            )
        )

        identifier_registry = (
            load_identifier_registry(
                identifier_registry_path
            )
        )

        current_documents, discovery_errors = (
            discover_review_documents(
                repository_root / "approvals"
            )
        )

        if discovery_errors:

            return discovery_errors

        reservation_errors = (
            validate_document_reservation_data(
                current_documents,
                identifier_registry,
            )
        )

        if reservation_errors:

            return reservation_errors

        previous_document_paths = {
            path.removeprefix("approvals/")
            for path in previous_records
        }

        return validate_document_creation_data(
            previous_homes,
            current_homes,
            previous_document_paths,
            current_documents,
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as exc:

        return [
            "Unable to validate historical "
            "technical review document creation: "
            f"{exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage: python "
            "validate_review_document_creation.py "
            "<base-commit>"
        )

        sys.exit(2)

    validation_errors = (
        validate_review_document_creation(
            sys.argv[1]
        )
    )

    if validation_errors:

        print(
            "HISTORICAL TECHNICAL REVIEW DOCUMENT "
            "CREATION VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "HISTORICAL TECHNICAL REVIEW DOCUMENT "
        "CREATION VALIDATION PASSED"
    )

    sys.exit(0)
