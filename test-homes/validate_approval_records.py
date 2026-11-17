import json
import re
import sys
from pathlib import Path


APPROVAL_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
)

VERSION_PATTERN = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+$"
)


def validate_approval_records(
    registry_path=None,
    approvals_directory=None
):
    """
    Verify that APPROVED and RETIRED reference homes
    have a corresponding approval document.

    This checks record existence and consistency.
    It does not authenticate approval decisions.
    """

    repository_root = Path(__file__).resolve().parent.parent

    if registry_path is None:
        registry_path = (
            repository_root
            / "test-homes"
            / "reference-home-registry.json"
        )

    if approvals_directory is None:
        approvals_directory = repository_root / "approvals"

    registry_path = Path(registry_path)
    approvals_directory = Path(approvals_directory)

    errors = []

    try:
        registry = json.loads(
            registry_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        return [f"Unable to load reference registry: {exc}"]

    homes = registry.get("reference_homes")

    if not isinstance(homes, list):
        return ["Invalid reference home registry"]

    for home in homes:
        if not isinstance(home, dict):
            errors.append("Invalid reference home entry")
            continue

        status = home.get("status")

        if status not in ("APPROVED", "RETIRED"):
            continue

        home_id = home.get("test_home_id")
        version = home.get("test_home_version")
        approval = home.get("approval")

        if (
            not isinstance(home_id, str)
            or not APPROVAL_ID_PATTERN.fullmatch(home_id)
            or not isinstance(version, str)
            or not VERSION_PATTERN.fullmatch(version)
        ):
            errors.append(
                "Invalid approved reference home identifier"
            )
            continue

        prefix = f"{home_id}/{version}"

        if not isinstance(approval, dict):
            errors.append(
                f"{prefix}: Missing approval metadata"
            )
            continue

        record_id = approval.get("approval_record")

        if (
            not isinstance(record_id, str)
            or not APPROVAL_ID_PATTERN.fullmatch(record_id)
        ):
            errors.append(
                f"{prefix}: Invalid approval record identifier"
            )
            continue

        record_path = (
            approvals_directory
            / home_id
            / version
            / "approval-record.md"
        )

        if not record_path.is_file():
            errors.append(
                f"{prefix}: Missing approval document: "
                f"{record_path}"
            )
            continue

        if record_path.is_symlink():
            errors.append(
                f"{prefix}: Approval document cannot be a symlink"
            )
            continue

        try:
            content = record_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(
                f"{prefix}: Cannot read approval document: {exc}"
            )
            continue

        required_fields = {
            "Reference Home ID": home_id,
            "Reference Home Version": version,
            "Approval Record ID": record_id,
        }

        for field, expected in required_fields.items():
            pattern = re.compile(
                rf"(?m)^\s*(?:-\s*)?"
                rf"{re.escape(field)}:\s*"
                rf"{re.escape(expected)}\s*$"
            )

            if not pattern.search(content):
                errors.append(
                    f"{prefix}: Approval document missing or "
                    f"mismatched {field}"
                )

        
        # Require an explicit approval decision.
        approved_pattern = (
            r"(?im)^\s*(?:-\s*)?(?:\*\*)?"
            r"Approval Status:(?:\*\*)?\s*"
            r"APPROVED\s*$"
        )

        not_approved_pattern = (
            r"(?im)^\s*(?:-\s*)?(?:\*\*)?"
            r"Approval Status:(?:\*\*)?\s*"
            r"NOT APPROVED\s*$"
        )

        if re.search(not_approved_pattern, content):
            errors.append(
                f"{prefix}: Approval document is marked NOT APPROVED"
            )
        elif not re.search(approved_pattern, content):
            errors.append(
                f"{prefix}: Approval document must explicitly "
                f"state APPROVED"
            )

    return errors


if __name__ == "__main__":
    validation_errors = validate_approval_records()

    if validation_errors:
        print("REFERENCE APPROVAL RECORD VALIDATION FAILED")

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print("REFERENCE APPROVAL RECORD VALIDATION PASSED")
