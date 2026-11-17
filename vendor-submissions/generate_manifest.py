import hashlib
import json
import sys
from pathlib import Path

FILES = [
    "submission.json",
    "building.xml",
    "results.json",
    "component-map.json",
]


def generate_manifest(folder):
    folder = Path(folder)
    manifest_path = folder / "manifest.json"

    with manifest_path.open(encoding="utf-8") as f:
        manifest = json.load(f)

    entries = []

    for filename in FILES:
        path = folder / filename

        if not path.is_file():
            raise FileNotFoundError(
                f"Missing required file: {filename}"
            )

        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        entries.append({
            "filename": filename,
            "required": True,
            "sha256": digest
        })

    manifest["files"] = entries
    manifest["manifest_status"] = "CHECKSUMS_GENERATED"
    manifest["validation"] = {
        "files_verified": False,
        "checksums_verified": False,
        "validation_status": "PENDING"
    }

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print("B.E.E.P. MANIFEST GENERATED")
    for entry in entries:
        print(f"{entry['filename']}: {entry['sha256']}")


if __name__ == "__main__":
    folder = (
        sys.argv[1]
        if len(sys.argv) > 1
        else Path(__file__).parent
    )

    generate_manifest(folder)
