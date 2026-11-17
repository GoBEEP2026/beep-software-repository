import json
import re
import sys
from datetime import date
from pathlib import Path


VALID_STATUSES = {
    "DEVELOPMENT",
    "UNDER_REVIEW",
    "APPROVED",
    "RETIRED",
}

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def is_nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def valid_date(value):
    if not is_nonempty_string(value):
        return False

    try:
        parsed = date.fromisoformat(value)
        return parsed.isoformat() == value
    except ValueError:
        return False


def validate_reference_approval(registry_path=None):
    if registry_path is None:
        registry_path = (
            Path(__file__).resolve().parent
            / "reference-home-registry.json"
        )

    errors = []

    try:
        registry = json.loads(
            Path(registry_path).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Unable to read reference registry: {exc}"]

    homes = registry.get("reference_homes")

    if not isinstance(homes, list) or not homes:
        return ["Reference registry has no valid home entries"]

    for home in homes:
        if not isinstance(home, dict):
            errors.append("Invalid reference home entry")
            continue

        home_id = home.get("test_home_id", "UNKNOWN")
        version = home.get("test_home_version", "UNKNOWN")
        prefix = f"{home_id}/{version}"

        status = home.get("status")

        if status not in VALID_STATUSES:
            errors.append(
                f"{prefix}: Invalid approval status: {status}"
            )
            continue

        if status == "DEVELOPMENT":
            continue

        if status == "UNDER_REVIEW":
            review = home.get("review")

            if not isinstance(review, dict):
                errors.append(
                    f"{prefix}: Missing review metadata"
                )
                continue

            if not is_nonempty_string(
                review.get("reviewer")
            ):
                errors.append(
                    f"{prefix}: Missing reviewer"
                )

            if not is_nonempty_string(
                review.get("review_record")
            ):
                errors.append(
                    f"{prefix}: Missing review record"
                )

            continue

        # APPROVED and RETIRED must retain approval data.
        approval = home.get("approval")

        if not isinstance(approval, dict):
            errors.append(
                f"{prefix}: Missing approval metadata"
            )
            continue

        if not is_nonempty_string(
            approval.get("approved_by")
        ):
            errors.append(
                f"{prefix}: Missing approval authority"
            )

        if not valid_date(
            approval.get("approval_date")
        ):
            errors.append(
                f"{prefix}: Invalid approval date"
            )

        if not is_nonempty_string(
            approval.get("approval_record")
        ):
            errors.append(
                f"{prefix}: Missing approval record"
            )

        reference_files = home.get("reference_files")

        if not isinstance(reference_files, list) or not reference_files:
            errors.append(
                f"{prefix}: Missing reference file inventory"
            )
        else:
            for entry in reference_files:
                if not isinstance(entry, dict):
                    errors.append(
                        f"{prefix}: Invalid reference file entry"
                    )
                    continue

                checksum = entry.get("sha256")

                if (
                    not isinstance(checksum, str)
                    or not SHA256_PATTERN.fullmatch(checksum)
                ):
                    errors.append(
                        f"{prefix}: Missing or invalid "
                        f"reference file checksum"
                    )

        cycles = home.get("test_cycles")

        if not isinstance(cycles, list) or not cycles:
            errors.append(
                f"{prefix}: No assigned test cycles"
            )
        elif any(
            not is_nonempty_string(cycle)
            for cycle in cycles
        ):
            errors.append(
                f"{prefix}: Invalid test cycle identifier"
            )

    return errors


if __name__ == "__main__":
    validation_errors = validate_reference_approval()

    if validation_errors:
        print("REFERENCE HOME APPROVAL VALIDATION FAILED")

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print("REFERENCE HOME APPROVAL VALIDATION PASSED")
    sys.exit(0)
