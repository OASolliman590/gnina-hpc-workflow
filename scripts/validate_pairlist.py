#!/usr/bin/env python3
"""
Lightweight validator for pairlist.csv.
Checks required headers and numeric box fields; exits non-zero on failure.
"""

import csv
import sys
from pathlib import Path


REQUIRED = ["receptor", "ligand", "center_x", "center_y", "center_z", "size_x", "size_y", "size_z"]
NUMERIC = ["center_x", "center_y", "center_z", "size_x", "size_y", "size_z"]


def validate(path: Path) -> int:
    if not path.exists():
        print(f"❌ File not found: {path}")
        return 1

    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print(f"❌ Missing header row in {path}")
            return 1

        missing_cols = [col for col in REQUIRED if col not in reader.fieldnames]
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return 1

        errors = 0
        rows = 0
        for line_num, row in enumerate(reader, start=2):  # account for header line
            rows += 1
            # Presence checks
            for col in REQUIRED:
                if row.get(col) in (None, ""):
                    print(f"❌ Empty value for '{col}' at line {line_num}")
                    errors += 1
            # Numeric checks
            for col in NUMERIC:
                try:
                    float(row.get(col, ""))
                except ValueError:
                    print(f"❌ Non-numeric value for '{col}' at line {line_num}: {row.get(col)}")
                    errors += 1

        if errors:
            print(f"❌ Validation failed: {errors} issue(s) across {rows} data row(s)")
            return 1

    print(f"✅ pairlist validation passed ({rows} data row(s))")
    return 0


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("pairlist.csv")
    raise SystemExit(validate(path))


if __name__ == "__main__":
    main()
