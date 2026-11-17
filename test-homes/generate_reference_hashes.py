import hashlib
import json
import sys
from pathlib import Path


def generate_reference_hashes(registry_path):
    registry_path = Path(registry_path).resolve()
    home_directory = registry_path.parent

    with registry_path.open(encoding="utf-8") as f:
        registry = json.load(f)

    homes = registry.get("reference_homes", [])

    if not isinstance(homes, list):
        raise ValueError("Invalid reference home registry")

    for home in homes:
        home_id = home.get("test_home_id")
        home_version = home.get("test_home_version")

        if home.get("status") != "DEVELOPMENT":
            raise ValueError(
                f"Refusing to modify non-development home: "
                f"{home_id} / {home_version}"
            )

        for entry in home.get("reference_files", []):
            filename = entry["filename"]

            # Only permit files directly inside test-homes.
            if (
                not isinstance(filename, str)
                or Path(filename).name != filename
                or filename in (".", "..")
            ):
                raise ValueError(
                    f"Invalid reference filename: {filename}"
                )

            file_path = home_directory / filename

            if not file_path.is_file():
                raise FileNotFoundError(
                    f"Missing reference file: {filename}"
                )

            digest = hashlib.sha256(
                file_path.read_bytes()
            ).hexdigest()

            entry["sha256"] = digest

            print(
                f"{home_id} / {home_version} / "
                f"{filename}: {digest}"
            )

    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")

    print("B.E.E.P. REFERENCE FILE HASHES GENERATED")


if __name__ == "__main__":
    registry_file = (
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).parent / "reference-home-registry.json"
    )

    generate_reference_hashes(registry_file)
