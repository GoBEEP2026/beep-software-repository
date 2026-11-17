import hashlib
import json
import re
import sys
from pathlib import Path


def validate_reference_integrity(registry_path=None):
    """
    Verify reference-home files against their registered
    SHA-256 checksums without modifying any files.
    """

    if registry_path is None:
        registry_path = (
            Path(__file__).resolve().parent
            / "reference-home-registry.json"
        )

    registry_path = Path(registry_path).resolve()
    home_directory = registry_path.parent
    errors = []

    try:
        registry = json.loads(
            registry_path.read_text(encoding="utf-8")
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
        reference_files = home.get("reference_files")

        if not isinstance(reference_files, list) or not reference_files:
            errors.append(
                f"{home_id}/{version}: Missing reference file inventory"
            )
            continue

        seen_files = set()

        for entry in reference_files:
            if not isinstance(entry, dict):
                errors.append(
                    f"{home_id}/{version}: Invalid file entry"
                )
                continue

            filename = entry.get("filename")
            expected_hash = entry.get("sha256")

            if (
                not isinstance(filename, str)
                or not filename
                or Path(filename).name != filename
                or filename in (".", "..")
                or "\\" in filename
                or "/" in filename
            ):
                errors.append(
                    f"{home_id}/{version}: Invalid filename: {filename}"
                )
                continue

            if filename in seen_files:
                errors.append(
                    f"{home_id}/{version}: Duplicate file: {filename}"
                )
                continue

            seen_files.add(filename)

            if not isinstance(expected_hash, str) or not re.fullmatch(
                r"[0-9a-f]{64}", expected_hash
            ):
                errors.append(
                    f"{home_id}/{version}: Invalid or missing "
                    f"SHA-256 for {filename}"
                )
                continue

            file_path = home_directory / filename

            if not file_path.is_file():
                errors.append(
                    f"{home_id}/{version}: Missing file: {filename}"
                )
                continue

            # Reject symlinks and files resolving outside the
            # registry directory.
            if (
                file_path.is_symlink()
                or file_path.resolve().parent != home_directory
            ):
                errors.append(
                    f"{home_id}/{version}: Unsafe file path: {filename}"
                )
                continue

            actual_hash = hashlib.sha256(
                file_path.read_bytes()
            ).hexdigest()

            if actual_hash != expected_hash:
                errors.append(
                    f"{home_id}/{version}: SHA-256 mismatch "
                    f"for {filename}"
                )
            else:
                print(
                    f"PASS: {home_id}/{version} "
                    f"{filename} SHA-256 verified"
                )

    return errors


if __name__ == "__main__":
    validation_errors = validate_reference_integrity()

    if validation_errors:
        print("REFERENCE HOME INTEGRITY VALIDATION FAILED")

        for error in validation_errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print("REFERENCE HOME INTEGRITY VALIDATION PASSED")
    sys.exit(0)
