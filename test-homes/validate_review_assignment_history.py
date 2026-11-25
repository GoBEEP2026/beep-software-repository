import json
import subprocess
import sys
from pathlib import Path

from validate_review_identifiers import (
    REGISTRY_FILE,
    load_identifier_registry,
    reject_duplicate_json_keys,
)

from validate_review_identifier_history import (
    REGISTRY_RELATIVE_PATH,
    load_historical_identifier_registry,
    validate_review_identifier_history,
    validate_append_only_reservations,
)

from validate_review_assignment_consistency import (
    ACTIVE_REVIEW_STATUSES,
    validate_assignment_consistency_data,
)

from validate_technical_review_history import (
    validate_historical_review_transition,
)

from validate_technical_review_record_history import (
    COMMIT_PATTERN,
    run_git,
)


REFERENCE_REGISTRY_RELATIVE_PATH = (
    "test-homes/reference-home-registry.json"
)


def build_home_lookup(registry, label):
    """
    Create a reference-home lookup while rejecting
    malformed and duplicate home identities.
    """

    if not isinstance(registry, dict):

        raise ValueError(
            f"{label} reference registry "
            "must be a JSON object"
        )

    reference_homes = registry.get(
        "reference_homes"
    )

    if (
        not isinstance(reference_homes, list)
        or not reference_homes
    ):

        raise ValueError(
            f"{label} reference registry must "
            "contain reference homes"
        )

    homes = {}

    for home in reference_homes:

        if not isinstance(home, dict):

            raise ValueError(
                f"{label} registry contains "
                "a malformed reference home"
            )

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")

        if (
            not isinstance(home_id, str)
            or not home_id.strip()
            or not isinstance(version, str)
            or not version.strip()
        ):

            raise ValueError(
                f"{label} registry contains "
                "an invalid reference home identity"
            )

        key = (home_id, version)

        if key in homes:

            raise ValueError(
                f"{label} registry contains duplicate "
                f"reference home version: "
                f"{home_id}/{version}"
            )

        homes[key] = home

    return homes


def get_active_assignment(home):
    """
    Return the active or completed review assignment.

    Return None when no active assignment exists.
    """

    if home is None:
        return None

    review = home.get("review")

    if not isinstance(review, dict):

        if (
            review is None
            and home.get("status") == "DEVELOPMENT"
        ):

            return None

        raise ValueError(
            "Invalid technical review metadata"
        )

    review_status = review.get(
        "review_status"
    )

    if review_status == "NOT_STARTED":
        return None

    if (
        not isinstance(review_status, str)
        or review_status not in ACTIVE_REVIEW_STATUSES
    ):

        raise ValueError(
            "Invalid technical review assignment status"
        )

    record_id = review.get("review_record")
    reviewer = review.get("reviewer")

    if (
        not isinstance(record_id, str)
        or not record_id.strip()
        or not isinstance(reviewer, str)
        or not reviewer.strip()
    ):

        raise ValueError(
            "Invalid technical review assignment identity"
        )

    return {
        "review_record_id": record_id,
        "assigned_reviewer": reviewer,
    }


def validate_historical_assignment_data(
    previous_homes,
    current_homes,
    previous_identifier_registry,
    current_identifier_registry,
):
    """
    Protect accepted technical review assignments
    and prevent permanent identifier reuse.
    """

    errors = []

    if (
        not isinstance(previous_homes, dict)
        or not previous_homes
    ):

        return [
            "Historical reference home lookup "
            "must be a nonempty dictionary"
        ]

    current_errors = (
        validate_assignment_consistency_data(
            current_homes,
            current_identifier_registry,
        )
    )

    if current_errors:
        return current_errors

    # The initial identifier registry must be
    # established without actual review assignments.

    if previous_identifier_registry is None:

        if current_identifier_registry[
            "reservations"
        ]:

            return [
                "Initial identifier reservation "
                "registry must be empty"
            ]

        previous_reservations = []

    else:

        history_errors = (
            validate_append_only_reservations(
                previous_identifier_registry,
                current_identifier_registry,
            )
        )

        if history_errors:
            return history_errors

        previous_errors = (
            validate_assignment_consistency_data(
                previous_homes,
                previous_identifier_registry,
            )
        )

        if previous_errors:

            return [
                f"Historical assignment: {error}"
                for error in previous_errors
            ]

        previous_reservations = (
            previous_identifier_registry[
                "reservations"
            ]
        )

    previous_ids = {
        reservation["review_record_id"].casefold()
        for reservation in previous_reservations
    }

    current_reservations = (
        current_identifier_registry[
            "reservations"
        ]
    )

    new_reservations = {
        reservation["review_record_id"].casefold():
        reservation
        for reservation in current_reservations[
            len(previous_reservations):
        ]
    }

    new_assignment_ids = set()

    # Previously registered home versions cannot
    # disappear from the proposed registry.

    for key in previous_homes:

        if key not in current_homes:

            errors.append(
                f"{key[0]}/{key[1]}: Historical "
                "reference home version cannot be removed"
            )

    for key, current_home in current_homes.items():

        prefix = f"{key[0]}/{key[1]}"

        previous_home = previous_homes.get(key)

        if previous_home is None:

            if current_home.get("status") != "DEVELOPMENT":

                errors.append(
                    f"{prefix}: New reference home "
                    "must begin in DEVELOPMENT"
                )

                continue

        else:

            transition_errors = (
                validate_historical_review_transition(
                    previous_home,
                    current_home,
                )
            )

            if transition_errors:

                errors.extend(transition_errors)
                continue

        try:

            previous_assignment = (
                get_active_assignment(
                    previous_home
                )
            )

            current_assignment = (
                get_active_assignment(
                    current_home
                )
            )

        except ValueError as exc:

            errors.append(
                f"{prefix}: {exc}"
            )

            continue

        if (
            previous_identifier_registry is None
            and previous_assignment is not None
        ):

            errors.append(
                f"{prefix}: Historical review assignment "
                "exists before establishment of the "
                "identifier reservation registry"
            )

            continue

        # A valid reset ends the current assignment.
        # Its permanent reservation remains unchanged.

        if current_assignment is None:
            continue

        record_id = current_assignment[
            "review_record_id"
        ]

        normalized_id = record_id.casefold()

        # Existing assignments may continue but
        # cannot change their identifier or reviewer.

        if previous_assignment is not None:

            if (
                previous_assignment["review_record_id"]
                != record_id
            ):

                errors.append(
                    f"{prefix}: Existing technical review "
                    "identifier cannot be changed"
                )

            if (
                previous_assignment["assigned_reviewer"]
                != current_assignment["assigned_reviewer"]
            ):

                errors.append(
                    f"{prefix}: Existing assigned "
                    "technical reviewer cannot be changed"
                )

            continue

        # A new assignment cannot reuse any
        # previously accepted identifier.

        if normalized_id in previous_ids:

            errors.append(
                f"{prefix}: Previously reserved "
                "technical review identifier "
                f"cannot be reused: {record_id}"
            )

            continue

        # A new assignment requires a reservation
        # appended in the same pull request.

        if normalized_id not in new_reservations:

            errors.append(
                f"{prefix}: New technical review "
                "assignment requires a newly appended "
                f"identifier reservation: {record_id}"
            )

            continue

        new_assignment_ids.add(
            normalized_id
        )

    # Newly appended reservations cannot exist
    # without corresponding new assignments.

    for normalized_id, reservation in (
        new_reservations.items()
    ):

        if normalized_id not in new_assignment_ids:

            errors.append(
                "New permanent identifier reservation "
                f"{reservation['review_record_id']} "
                "has no corresponding new review assignment"
            )

    return errors


def load_historical_reference_registry(
    repository_root,
    base_commit,
):
    """
    Retrieve the accepted reference home registry
    from a historical Git commit.
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
            REFERENCE_REGISTRY_RELATIVE_PATH,
        ],
    )

    entries = [
        entry
        for entry in tree_output.split(b"\0")
        if entry
    ]

    if len(entries) != 1:

        raise ValueError(
            "Historical reference home registry "
            "must exist as a single regular file"
        )

    metadata, raw_path = entries[0].split(
        b"\t", 1
    )

    mode, object_type, object_id = (
        metadata.decode("ascii").split()
    )

    if (
        raw_path.decode("utf-8")
        != REFERENCE_REGISTRY_RELATIVE_PATH
        or object_type != "blob"
        or mode not in ("100644", "100755")
    ):

        raise ValueError(
            "Invalid historical reference "
            "home registry tree entry"
        )

    content = run_git(
        repository_root,
        [
            "cat-file",
            "blob",
            object_id,
        ],
    )

    return json.loads(
        content.decode("utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )


def get_current_registry_path(
    repository_root,
    relative_path,
):
    """
    Require a regular registry file located
    within the repository without symbolic links.
    """

    registry_path = (
        repository_root / relative_path
    )

    component = registry_path

    while component != repository_root:

        if component.is_symlink():

            raise ValueError(
                "Registry path cannot contain "
                f"symbolic links: {relative_path}"
            )

        component = component.parent

    if not registry_path.resolve().is_relative_to(
        repository_root
    ):

        raise ValueError(
            "Registry path escapes repository "
            f"directory: {relative_path}"
        )

    if not registry_path.is_file():

        raise ValueError(
            "Registry does not exist as a "
            f"regular file: {relative_path}"
        )

    return registry_path


def validate_review_assignment_history(
    base_commit,
    repository_root=None,
):
    """
    Validate historical assignment consistency
    against the accepted Git base commit.
    """

    if repository_root is None:

        repository_root = (
            REGISTRY_FILE.parent.parent
        )

    try:

        repository_root = Path(
            repository_root
        ).resolve()

        reservation_history_errors = (
            validate_review_identifier_history(
                base_commit,
                repository_root,
            )
        )

        if reservation_history_errors:

            return reservation_history_errors

        current_reference_path = (
            get_current_registry_path(
                repository_root,
                REFERENCE_REGISTRY_RELATIVE_PATH,
            )
        )

        current_identifier_path = (
            get_current_registry_path(
                repository_root,
                REGISTRY_RELATIVE_PATH,
            )
        )

        previous_reference_registry = (
            load_historical_reference_registry(
                repository_root,
                base_commit,
            )
        )

        current_reference_registry = json.loads(
            current_reference_path.read_text(
                encoding="utf-8"
            ),
            object_pairs_hook=reject_duplicate_json_keys,
        )

        previous_homes = build_home_lookup(
            previous_reference_registry,
            "Historical",
        )

        current_homes = build_home_lookup(
            current_reference_registry,
            "Current",
        )

        previous_identifier_registry = (
            load_historical_identifier_registry(
                repository_root,
                base_commit,
            )
        )

        current_identifier_registry = (
            load_identifier_registry(
                current_identifier_path
            )
        )

        return validate_historical_assignment_data(
            previous_homes,
            current_homes,
            previous_identifier_registry,
            current_identifier_registry,
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
            "Unable to validate historical technical "
            f"review assignment consistency: {exc}"
        ]


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage: python "
            "validate_review_assignment_history.py "
            "<base-commit>"
        )

        sys.exit(2)

    validation_errors = (
        validate_review_assignment_history(
            sys.argv[1]
        )
    )

    if validation_errors:

        print(
            "HISTORICAL TECHNICAL REVIEW ASSIGNMENT "
            "VALIDATION FAILED"
        )

        for error in validation_errors:

            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "HISTORICAL TECHNICAL REVIEW ASSIGNMENT "
        "VALIDATION PASSED"
    )

    sys.exit(0)
