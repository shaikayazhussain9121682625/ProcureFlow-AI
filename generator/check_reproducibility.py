import hashlib
import subprocess
import sys
from pathlib import Path

def get_hashes():
    results = {}
    for folder in ["exports/csv", "exports/json"]:
        for path in sorted(Path(folder).glob("*")):
            if path.is_file():
                results[str(path)] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    return results

print("Calculating initial checksums...")
before = get_hashes()

print("\nRegenerating CSV and JSON exports...")
result = subprocess.run(
    [sys.executable, "-m", "generator.export_all"]
)

if result.returncode != 0:
    raise SystemExit("Export command failed.")

print("\nCalculating final checksums...")
after = get_hashes()

if before == after:
    print("\nREPRODUCIBILITY CHECK: PASSED")
    print("All CSV and JSON exports are identical after regeneration.")
    print("Files checked:", len(after))
else:
    print("\nREPRODUCIBILITY CHECK: FAILED")
    for path in sorted(set(before) | set(after)):
        if before.get(path) != after.get(path):
            print("Changed:", path)
