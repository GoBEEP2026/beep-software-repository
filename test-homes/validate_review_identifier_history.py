import json
import subprocess
import sys
from pathlib import Path

from validate_review_identifiers import (
    REGISTRY_FILE,
    load_identifier_registry,
    reject_duplicate_json_keys,
    validate_identifier_registry_data,
)

from validate_technical_review_record_history import (
    COMMIT_PATTERN,
    run_git,
)


REGISTRY_RELATIVE_PATH = (
    "test-homes/"
    "reference-review-identifier-registry.json"
)


def validate_append_only_reservations(
    previous_registry,
    current_registry,
):
    """
    Verify that historical identifier reservations
    remain unchanged and that new reservations
    are appended to the end of the registry.
    """

    errors = []

    previous_errors = (
        validate_identifier_registry_data(
            previous_registry
        )
    )

    current_errors = (
        validate_identifier_registry_data(
            current_registry
        )
    )

    for error in previous_errors:

        errors.append(
            f"Historical registry: {error}"
        )

    for error in current_errors:

        errors.append(
            f"Current registry: {error}"
        )

    if errors:
        return errors

    previous_metadata = {
        key: value
        for key, value in previous_registry.items()
        if key != "reservations"
    }

    current_metadata = {
        key: value
        for key, value in current_registry.items()
        if key != "reservations"
    }

    if previous_metadata != current_metadata:

        errors.append(
            "Historical identifier registry metadata "
            "and reservation policy cannot be modified"
        )

    previous_reservations = (
        previous_registry["reservations"]
    )

    current_reservations = (
        current_registry["reservations"]
    )

    if len(current_reservations) < len(
        previous_reservations
    ):

        errors.append(
            "Historical identifier reservations "
            "cannot be deleted"
        )

    for index, previous_record in enumerate(
        previous_reservations
    ):

        record_id = previous_record[
            "review_record_id"
        ]

        if index >= len(current_reservations):

            errors.append(
                f"Missing historical identifier "
                f"reservation: {record_id}"
            )

            continue

        current_record = (
            current_reservations[index]
        )

        if previous_record != current_record:

            errors.append(
                f"Historical identifier reservation "
                f"cannot be modified, replaced, "
                f"or reordered: {record_id}"
            )

    return errors


def load_historical_identifier_registry(
    repository_root,
    base_commit,
):
    """
    Load the identifier reservation registry
    from the specified historical Git commit.

    Return None only when the registry does
    not exist in the historical commit.
    """

    if (
        not isinstance(base_commit, str)
        or not COMMIT_PATTERN.fullmatch(
            base_commit
        )
    ):

        raise ValueError(
            "Invalid historical Git commit identifier"
        )

    run_git(
        repository_root,
        [
            "cat-file",
            "-e",
            f"{base_commit}^{{commit}}",
        ],
    )

    tree_output = run_git(
        repository_root,
        [
            "ls-tree",
            "-z",
            base_commit,
            "--",
            REGISTRY_RELATIVE_PATH,
        ],
    )

    if not tree_output:
        return None

    entries = [
        entry
        for entry in tree_output.split(b"\0")
        if entry
    ]

    if len(entries) != 1:

        raise ValueError(
            "Invalid historical identifier "
            "registry tree entry"
        )

    metadata, raw_path = entries[0].split(
        b"\t", 1
    )

    mode, object_type, object_id = (
        metadata.decode("ascii").split()
    )

    path = raw_path.decode("utf-8")

    if path != REGISTRY_RELATIVE_PATH:

        raise ValueError(
            "Unexpected historical identifier "
            "registry path"
        )

    if (
        object_type != "blob"
        or mode not in ("100644", "100755")
    ):

        raise ValueError(
            "Historical identifier registry "
            "must be a regular file"
        )

    content = run_git(
        repository_root,
        [
            "cat-file",
            "blob",
            object_id,
        ],
    )

    registry = json.loads(
        content.decode("utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )

    if registry is None:

        raise ValueError(
            "Historical identifier registry "
            "cannot contain a null root"
        )

    return registry


def validate_review_identifier_history(
    base_commit,
    repository_root=None,
):
    """
    Compare the current identifier reservation
    registry against the accepted historical
    registry.
    """

    if repository_root is None:

        repository_root = (
            REGISTRY_FILE.parent.parent
        )

    repository_root = Path(
        repository_root
    ).resolve()

    current_registry_path = (
        repository_root
        / REGISTRY_RELATIVE_PATH
    )

    try:

        path_component = (
            current_registry_path
        )

        while path_component != repository_root:

            if path_component.is_symlink():

                return [
                    "Identifier registry path "
                    "cannot contain symbolic links"
                ]

            path_component = (
                path_component.parent
            )

        if not current_registry_path.resolve().is_relative_to(
            repository_root
        ):

            return [
                "Identifier registry path "
                "escapes repository directory"
            ]

        if not current_registry_path.is_file():

            return [
                "Current identifier reservation "
                "registry does not exist "
                "as a regular file"
            ]

        current_registry = (
            load_identifier_registry(
                current_registry_path
            )
        )

        current_errors = (
            validate_identifier_registry_data(
                current_registry
            )
        )

        if current_errors:

            return [
                f"Current registry: {error}"
                for error in current_errors
            ]

        previous_registry = (
            load_historical_identifier_registry(
                repository_root,
                base_commit,
            )
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        RuntimeError,
        subprocess.CalledProcessError,
    ) as exc:

        return [
            f"Unable to validate historical "
            f"identifier reservations: {exc}"
        ]

    if previous_registry is None:

        if current_registry["reservations"]:

            return [
                "Initial identifier reservation "
                "registry must be empty"
            ]

        return []

    return validate_append_only_reservations(
        previous_registry,
        current_registry,
    )


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage: python "
            "validate_review_identifier_history.py "
            "<base-commit>"
        )

        sys.exit(2)

    validation_errors = (
        validate_review_identifier_history(
            sys.argv[1]
        )
    )

    if validation_errors:

        print(
            "HISTORICAL TECHNICAL REVIEW IDENTIFIER "
            "VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "HISTORICAL TECHNICAL REVIEW IDENTIFIER "
        "VALIDATION PASSED"
    )

    sys.exit(0)
