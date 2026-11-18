import json
import re
import sys
from datetime import date
from pathlib import Path


AUDIT_FILE = (
    Path(__file__).resolve().parent
    / "reference-approval-audit.json"
)

VALID_DECISIONS = {
    "APPROVED",
    "REJECTED",
    "RETIRED",
}


def validate_audit(path=AUDIT_FILE):
    errors = []
    path = Path(path)

    try:
        audit = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"Unable to load audit log: {exc}"]

    if not isinstance(audit, dict):
        return ["Audit log must be a JSON object"]

    if audit.get("audit_schema_version") != "1.0.0":
        errors.append("Invalid audit schema version")

    if audit.get("audit_status") != "DEVELOPMENT":
        errors.append("Unsupported audit status")

    records = audit.get("records")

    if not isinstance(records, list):
        return errors + ["Audit records must be an array"]

    seen_ids = set()

    for index, record in enumerate(records, start=1):
        prefix = f"Record {index}"

        if not isinstance(record, dict):
            errors.append(f"{prefix}: Must be an object")
            continue

        record_id = record.get("record_id")

        if not isinstance(record_id, str) or not record_id.strip():
            errors.append(f"{prefix}: Missing record ID")
        elif record_id in seen_ids:
            errors.append(f"{prefix}: Duplicate record ID")
        else:
            seen_ids.add(record_id)

        home_id = record.get("reference_home_id")

        if not isinstance(home_id, str) or not home_id.strip():
            errors.append(f"{prefix}: Missing reference home ID")

        version = record.get("reference_home_version")

        if not isinstance(version, str) or not re.fullmatch(
            r"\d+\.\d+\.\d+", version
        ):
            errors.append(f"{prefix}: Invalid reference home version")

        if record.get("decision") not in VALID_DECISIONS:
            errors.append(f"{prefix}: Invalid decision")

       
        for field in (
            "reviewer",
            "approval_authority",
            "evidence",
            "pull_request",
            "board_resolution_reference",
        ):

            value = record.get(field)

            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: Missing {field}")

        decision_date = record.get("decision_date")

        if not isinstance(decision_date, str):
            errors.append(f"{prefix}: Invalid decision date")
        else:
            try:
                parsed_date = date.fromisoformat(decision_date)

                if parsed_date.isoformat() != decision_date:
                    raise ValueError("Noncanonical date")

            except ValueError:
                errors.append(f"{prefix}: Invalid decision date")

    return errors


if __name__ == "__main__":
    validation_errors = validate_audit()

    if validation_errors:
        print("Reference approval audit validation FAILED")

        for error in validation_errors:
            print(f"- {error}")

        sys.exit(1)

    print("Reference approval audit validation PASSED")
    sys.exit(0)
