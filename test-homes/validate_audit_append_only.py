import json
import sys
from pathlib import Path


AUDIT_FILE = (
    Path(__file__).resolve().parent
    / "reference-approval-audit.json"
)


def validate_append_only(previous_path, current_path=AUDIT_FILE):
    """
    Verify that previously recorded audit decisions
    have not been changed, removed, or reordered.
    """

    errors = []

    try:
        previous = json.loads(
            Path(previous_path).read_text(encoding="utf-8")
        )
        current = json.loads(
            Path(current_path).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"Unable to load audit history: {exc}"]

    if not isinstance(previous, dict) or not isinstance(current, dict):
        return ["Audit histories must be JSON objects"]

    previous_records = previous.get("records")
    current_records = current.get("records")

    if not isinstance(previous_records, list):
        return ["Previous audit records must be an array"]

    if not isinstance(current_records, list):
        return ["Current audit records must be an array"]

    if len(current_records) < len(previous_records):
        errors.append(
            "Audit history cannot remove existing records"
        )

    for index, previous_record in enumerate(previous_records):
        if index >= len(current_records):
            break

        if previous_record != current_records[index]:
            errors.append(
                f"Audit record {index + 1} was modified or reordered"
            )

    return errors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python validate_audit_append_only.py "
            "<previous-audit-file>"
        )
        sys.exit(2)

    validation_errors = validate_append_only(sys.argv[1])

    if validation_errors:
        print("APPEND-ONLY AUDIT VALIDATION FAILED")

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print("APPEND-ONLY AUDIT VALIDATION PASSED")
    sys.exit(0)
