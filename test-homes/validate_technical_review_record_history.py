import re
import subprocess
import sys
from pathlib import Path


IDENTIFIER_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_-]*"
)

VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)"
)

COMMIT_PATTERN = re.compile(
    r"[0-9a-fA-F]{40}"
)


def is_technical_review_record_path(path):
    """
    Identify version-specific technical review
    documents within the approvals directory.
    """

    if not isinstance(path, str):
        return False

    parts = path.split("/")

    if len(parts) != 5:
        return False

    directory, home_id, version, category, filename = (
        parts
    )

    if directory != "approvals":
        return False

    if category != "technical-reviews":
        return False

    if not IDENTIFIER_PATTERN.fullmatch(home_id):
        return False

    if not VERSION_PATTERN.fullmatch(version):
        return False

    if not filename.endswith(".md"):
        return False

    record_id = filename[:-3]

    if not IDENTIFIER_PATTERN.fullmatch(record_id):
        return False

    return True


def run_git(repository_root, arguments):
    """
    Execute a read-only Git command and return
    its output as bytes.
    """

    result = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    return result.stdout


def load_historical_review_records(
    repository_root,
    base_commit,
):
    """
    Load technical review documents from the
    specified historical Git commit.
    """

    if (
        not isinstance(base_commit, str)
        or not COMMIT_PATTERN.fullmatch(base_commit)
    ):
        raise ValueError(
            "Invalid historical Git commit identifier"
        )

    tree_output = run_git(
        repository_root,
        [
            "ls-tree",
            "-r",
            "-z",
            base_commit,
            "--",
            "approvals/",
        ],
    )

    records = {}

    for entry in tree_output.split(b"\0"):

        if not entry:
            continue

        metadata, raw_path = entry.split(
            b"\t", 1
        )

        mode, object_type, object_id = (
            metadata.decode("ascii").split()
        )

        path = raw_path.decode("utf-8")

        if not is_technical_review_record_path(path):
            continue

        if (
            object_type != "blob"
            or mode not in ("100644", "100755")
        ):
            raise ValueError(
                f"Invalid historical technical review "
                f"document type: {path}"
            )

        content = run_git(
            repository_root,
            [
                "cat-file",
                "blob",
                object_id,
            ],
        )

        records[path] = content

    return records


def validate_preserved_review_records(
    previous_records,
    repository_root,
):
    """
    Verify that historical technical review
    documents still exist and remain unchanged.
    """

    if not isinstance(previous_records, dict):
        return [
            "Historical technical review records "
            "must be a dictionary"
        ]

    root = Path(repository_root).resolve()

    errors = []

    for relative_path, previous_content in (
        previous_records.items()
    ):

        if not is_technical_review_record_path(
            relative_path
        ):
            errors.append(
                f"Invalid historical technical review "
                f"document path: {relative_path}"
            )
            continue

        if not isinstance(previous_content, bytes):
            errors.append(
                f"Invalid historical document content: "
                f"{relative_path}"
            )
            continue

        current_path = root / relative_path

        try:
            path_component = current_path
            contains_symlink = False

            while path_component != root:

                if path_component.is_symlink():
                    contains_symlink = True
                    break

                path_component = (
                    path_component.parent
                )

            if contains_symlink:
                errors.append(
                    f"Historical technical review document "
                    f"path cannot contain symbolic links: "
                    f"{relative_path}"
                )
                continue

            if not current_path.resolve().is_relative_to(
                root
            ):
                errors.append(
                    f"Historical technical review document "
                    f"escapes repository directory: "
                    f"{relative_path}"
                )
                continue

            if not current_path.is_file():
                errors.append(
                    f"Historical technical review document "
                    f"cannot be deleted or renamed: "
                    f"{relative_path}"
                )
                continue

            current_content = (
                current_path.read_bytes()
            )

            if current_content != previous_content:
                errors.append(
                    f"Historical technical review document "
                    f"cannot be modified: "
                    f"{relative_path}"
                )

        except (
            OSError,
            ValueError,
            RuntimeError,
        ) as exc:

            errors.append(
                f"Unable to verify historical technical "
                f"review document {relative_path}: {exc}"
            )

    return errors


def validate_technical_review_record_history(
    base_commit,
    repository_root=None,
):
    """
    Compare historical technical review records
    with the current repository contents.
    """

    if repository_root is None:
        repository_root = (
            Path(__file__).resolve().parent.parent
        )

    repository_root = Path(
        repository_root
    ).resolve()

    try:
        previous_records = (
            load_historical_review_records(
                repository_root,
                base_commit,
            )
        )

    except (
        OSError,
        UnicodeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:

        return [
            f"Unable to load historical technical "
            f"review documents: {exc}"
        ]

    return validate_preserved_review_records(
        previous_records,
        repository_root,
    )


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage: python "
            "validate_technical_review_record_history.py "
            "<base-commit>"
        )

        sys.exit(2)

    validation_errors = (
        validate_technical_review_record_history(
            sys.argv[1]
        )
    )

    if validation_errors:

        print(
            "HISTORICAL TECHNICAL REVIEW RECORD "
            "VALIDATION FAILED"
        )

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print(
        "HISTORICAL TECHNICAL REVIEW RECORD "
        "VALIDATION PASSED"
    )

    sys.exit(0)
