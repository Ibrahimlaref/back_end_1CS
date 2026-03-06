#!/usr/bin/env python
"""
Enforce migration-count threshold per app to drive periodic squash discipline.
"""

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-per-app", type=int, default=50)
    args = parser.parse_args()

    counts = _migration_counts()
    offenders = {app: count for app, count in counts.items() if count > args.max_per_app}

    if offenders:
        print("Migration squash policy failed:")
        for app, count in sorted(offenders.items()):
            print(f"- {app}: {count} migrations (max {args.max_per_app})")
        return 1

    print("Migration squash policy passed.")
    for app, count in sorted(counts.items()):
        print(f"- {app}: {count}")
    return 0


def _migration_counts():
    counts = {}
    apps_dir = ROOT / "apps"
    for app_dir in sorted(apps_dir.iterdir()):
        if not app_dir.is_dir():
            continue
        migrations_dir = app_dir / "migrations"
        if not migrations_dir.exists():
            continue
        migration_files = [
            path
            for path in migrations_dir.glob("*.py")
            if path.name != "__init__.py" and path.name[0:4].isdigit()
        ]
        counts[f"apps.{app_dir.name}"] = len(migration_files)
    return counts


if __name__ == "__main__":
    sys.exit(main())
