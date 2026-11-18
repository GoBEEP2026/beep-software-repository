import re
from datetime import date
from pathlib import Path


BOARD_AUTHORITY = "B.E.E.P. Board of Directors"


def extract_field(content, field):
    """Read a labeled field from an approval document."""
    pattern = (
        rf"(?im)^\s*(?:-\s*)?"
        rf"(?:\*\*)?{re.escape(field)}:"
        rf"(?:\*\*)?\s*(.*?)\s*$"
    )

    match = re.search(pattern, content)

    if not match:
        return None

    return match.group(1).strip()


def validate_board_authorization(record_path):
    """
    Check documented Board authorization requirements.

    This validates documentation, not the authenticity
    of a Board decision.
    """
    errors = []
    record_path = Path(record_path)

    try:
        content = record_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"Unable to read Board approval record: {exc}"]

    authority = extract_field(
        content, "Approval Authority"
    )

    if authority != BOARD_AUTHORITY:
        errors.append(
            "Approval Authority must be "
            "B.E.E.P. Board of Directors"
        )

    resolution = extract_field(
        content, "Board Resolution Reference"
    )

    if (
        not resolution
        or resolution.lower() in (
            "pending", "none", "n/a", "tbd"
        )
    ):
        errors.append(
            "Missing valid Board Resolution Reference"
        )

    decision_date = extract_field(
        content, "Board Decision Date"
    )

    if not decision_date:
        errors.append("Missing Board Decision Date")
    else:
        try:
            parsed = date.fromisoformat(decision_date)

            if parsed.isoformat() != decision_date:
                raise ValueError("Noncanonical date")

        except ValueError:
            errors.append(
                "Board Decision Date must use YYYY-MM-DD"
            )

    return errors
