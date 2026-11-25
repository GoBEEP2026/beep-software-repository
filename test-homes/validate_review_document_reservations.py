import os
import re
import sys
from datetime import date
from pathlib import Path

from validate_review_identifiers import (
    REGISTRY_FILE,
    is_valid_identifier,
    is_valid_version,
    load_identifier_registry,
    validate_identifier_registry_data,
)

from validate_technical_review_records import (
    extract_review_record_fields,
)


APPROVALS_DIRECTORY = (
    Path(__file__).resolve().parent.parent
    / "approvals"
)

VALID_RECOMMENDATIONS = {
    "RECOMMEND_APPROVAL",
    "REVISIONS_REQUIRED",
}


def parse_review_document_path(relative_path):
    """
    Validate the required version-specific
    technical review document path.
    """

    parts = Path(relative_path).parts

    if len(parts) != 4:

        raise ValueError(
            "Invalid technical review document "
            "directory structure"
        )

    home_id, version, directory, filename = parts

    if directory != "technical-reviews":

        raise ValueError(
            "Invalid technical review directory"
        )

    if not is_valid_identifier(home_id):

        raise ValueError(
            "Invalid reference home identifier "
            "in document path"
        )

    if not is_valid_version(version):

        raise ValueError(
            "Invalid reference home version "
            "in document path"
        )

    if not filename.endswith(".md"):

        raise ValueError(
            "Technical review document "
            "must use the .md extension"
        )

    record_id = filename[:-3]

    if not is_valid_identifier(record_id):

        raise ValueError(
            "Invalid technical review record "
            "identifier in document filename"
        )

    return home_id, version, record_id


def validate_document_reservation(
    relative_path,
    content,
    reservations_by_id,
):
    """
    Match a technical review document against
    its permanent identifier reservation.
    """

    try:

        home_id, version, record_id = (
            parse_review_document_path(
                relative_path
            )
        )

    except (ValueError, TypeError) as exc:

        return [str(exc)]

    errors = []

    reservation = reservations_by_id.get(
        record_id.casefold()
    )

    if reservation is None:

        return [
            "Technical review document has no "
            f"permanent identifier reservation: "
            f"{record_id}"
        ]

    expected_path_values = {
        "review_record_id": record_id,
        "reference_home_id": home_id,
        "reference_home_version": version,
    }

    for field, actual in (
        expected_path_values.items()
    ):

        if reservation[field] != actual:

            errors.append(
                "Technical review document path "
                f"does not match reserved {field}"
            )

    fields, field_errors = (
        extract_review_record_fields(
            content
        )
    )

    errors.extend(field_errors)

    if field_errors:
        return errors

    expected_fields = {
        "Reference Home ID":
            reservation["reference_home_id"],

        "Reference Home Version":
            reservation["reference_home_version"],

        "Technical Review Record ID":
            reservation["review_record_id"],

        "Technical Reviewer":
            reservation["assigned_reviewer"],
    }

    for field, expected in (
        expected_fields.items()
    ):

        if fields[field] != expected:

            errors.append(
                "Technical review document "
                f"does not match reserved {field}"
            )

    if fields["Technical Review Status"] != "COMPLETED":

        errors.append(
            "Technical review supporting document "
            "must have COMPLETED review status"
        )

    if (
        fields["Review Recommendation"]
        not in VALID_RECOMMENDATIONS
    ):

        errors.append(
            "Invalid technical review "
            "document recommendation"
        )

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        fields["Reviewed Content SHA-256"],
    ):

        errors.append(
            "Invalid reviewed content "
            "SHA-256 fingerprint"
        )

    try:

        review_date_value = fields[
            "Technical Review Date"
        ]

        review_date = date.fromisoformat(
            review_date_value
        )

        if (
            review_date.isoformat()
            != review_date_value
        ):

            raise ValueError(
                "Noncanonical review date"
            )

        assignment_date = date.fromisoformat(
            reservation["assignment_date"]
        )

        if review_date < assignment_date:

            errors.append(
                "Technical review document "
                "completion date cannot precede "
                "the identifier assignment date"
            )

    except ValueError:

        errors.append(
            "Invalid technical review "
            "document completion date"
        )

    return errors


def discover_review_documents(
    approvals_directory,
):
    """
    Discover technical review supporting documents,
    including documents no longer referenced by
    the current reference home review metadata.

    Reject symbolic links and malformed paths.
    """

    root = Path(
        approvals_directory
    ).absolute()

    documents = {}
    errors = []

    if root.is_symlink():

        return {}, [
            "Approvals directory cannot "
            "be a symbolic link"
        ]

    if not root.is_dir():

        return {}, [
            "Approvals directory does not "
            "exist as a regular directory"
        ]

    def handle_walk_error(exc):

        errors.append(
            f"Unable to scan approvals directory: "
            f"{exc}"
        )

    for directory, subdirectories, filenames in os.walk(
        root,
        topdown=True,
        onerror=handle_walk_error,
        followlinks=False,
    ):

        directory_path = Path(directory)

        subdirectories.sort()
        filenames.sort()

        relative_directory = (
            directory_path.relative_to(root)
        )

        directory_parts = (
            relative_directory.parts
        )

        inside_review_directory = (
            "technical-reviews"
            in directory_parts
        )

        for name in list(subdirectories):

            path = directory_path / name

            relative_path = (
                path.relative_to(root)
            )

            if path.is_symlink():

                errors.append(
                    "Approvals directory path "
                    "cannot contain symbolic links: "
                    f"{relative_path.as_posix()}"
                )

                subdirectories.remove(name)

                continue

            if name == "technical-reviews":

                if (
                    len(directory_parts) != 2
                    or not is_valid_identifier(
                        directory_parts[0]
                    )
                    or not is_valid_version(
                        directory_parts[1]
                    )
                ):

                    errors.append(
                        "Invalid technical review "
                        "directory structure: "
                        f"{relative_path.as_posix()}"
                    )

            if inside_review_directory:

                errors.append(
                    "Unexpected nested directory "
                    "inside technical reviews: "
                    f"{relative_path.as_posix()}"
                )

        for filename in filenames:

            path = directory_path / filename

            relative_path = (
                path.relative_to(root).as_posix()
            )

            if path.is_symlink():

                errors.append(
                    "Approvals document cannot "
                    "be a symbolic link: "
                    f"{relative_path}"
                )

                continue

            if filename == "technical-reviews":

                errors.append(
                    "Technical reviews path "
                    "must be a directory: "
                    f"{relative_path}"
                )

                continue

            if not inside_review_directory:
                continue

            try:

                parse_review_document_path(
                    relative_path
                )

                if not path.is_file():

                    raise ValueError(
                        "Technical review document "
                        "must be a regular file"
                    )

                if not path.resolve().is_relative_to(
                    root.resolve()
                ):

                    raise ValueError(
                        "Technical review document "
                        "escapes approvals directory"
                    )

                documents[relative_path] = (
                    path.read_text(
                        encoding="utf-8"
                    )
                )

            except (
                OSError,
                UnicodeError,
                ValueError,
                RuntimeError,
            ) as exc:

                errors.append(
                    f"{relative_path}: {exc}"
                )

    return documents, errors


def validate_document_reservation_data(
    documents,
    identifier_registry,
):
    """
    Validate all discovered technical review
    documents against permanent reservations.
    """

    registry_errors = (
        validate_identifier_registry_data(
            identifier_registry
        )
    )

    if registry_errors:

        return [
            f"Identifier registry: {error}"
            for error in registry_errors
        ]

    if not isinstance(documents, dict):

        return [
            "Technical review documents "
            "must be a dictionary"
        ]

    reservations_by_id = {
        reservation["review_record_id"].casefold():
        reservation
        for reservation in identifier_registry[
            "reservations"
        ]
    }

    errors = []

    document_identifiers = {}

    for relative_path, content in documents.items():

        if not isinstance(relative_path, str):

            errors.append(
                "Invalid technical review "
                "document path"
            )

            continue

        try:

            _, _, record_id = (
                parse_review_document_path(
                    relative_path
                )
            )

        except (ValueError, TypeError) as exc:

            errors.append(
                f"{relative_path}: {exc}"
            )

            continue

        normalized_id = record_id.casefold()

        if normalized_id in document_identifiers:

            errors.append(
                "Technical review identifier "
                f"{record_id} appears in multiple "
                "document paths: "
                f"{document_identifiers[normalized_id]} "
                f"and {relative_path}"
            )

        else:

            document_identifiers[
                normalized_id
            ] = relative_path

        document_errors = (
            validate_document_reservation(
                relative_path,
                content,
                reservations_by_id,
            )
        )

        errors.extend(
            f"{relative_path}: {error}"
            for error in document_errors
        )

    return errors


def validate_review_document_reservations(
    identifier_registry_path=None,
    approvals_directory=None,
):
    """
    Validate all current and preserved historical
    technical review supporting documents.
    """

    if identifier_registry_path is None:

        identifier_registry_path = REGISTRY_FILE

    if approvals_directory is None:

        approvals_directory = (
            APPROVALS_DIRECTORY
        )

    try:

        registry_path = Path(
            identifier_registry_path
        )

        if registry_path.is_symlink():

            return [
                "Identifier reservation registry "
                "cannot be a symbolic link"
            ]

        identifier_registry = (
            load_identifier_registry(
                registry_path
            )
        )

        documents, discovery_errors = (
            discover_review_documents(
                approvals_directory
            )
        )

        validation_errors = (
            validate_document_reservation_data(
                documents,
                identifier_registry,
            )
        )

        return (
            discovery_errors
            + validation_errors
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
    ) as exc:

        return [
            "Unable to validate technical review "
            f"document reservations: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) not in (1, 3):

        print(
            "Usage: python "
            "validate_review_document_reservations.py "
            "[identifier-registry approvals-directory]"
        )

        sys.exit(2)

    identifier_registry_path = (
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
        validate_review_document_reservations(
            identifier_registry_path,
            approvals_directory,
        )
    )

    if validation_errors:

        print(
            "TECHNICAL REVIEW DOCUMENT RESERVATION "
            "VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "TECHNICAL REVIEW DOCUMENT RESERVATION "
        "VALIDATION PASSED"
    )

    sys.exit(0)
