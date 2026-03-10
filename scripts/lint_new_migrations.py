#!/usr/bin/env python
"""
Run django-migration-linter only for migrations introduced on the current branch.

Waived migrations are skipped here and covered by the repository governance docs.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_PREFIX = Path("apps")
WAIVERS_PREFIX = Path("docs/migrations/waivers")
MIGRATIONS_DIRNAME = "migrations"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--settings", default="brahim.settings.dev")
    parser.add_argument("--warnings-as-errors", action="store_true")
    args = parser.parse_args()

    migrations = [
        path
        for status, path in _changed_files_with_status(args.base_ref)
        if status.startswith("A") and _is_migration_file(path)
    ]

    if not migrations:
        print("No new migration files found. Backward-compatibility lint skipped.")
        return 0

    exit_code = 0
    for migration in migrations:
        if not _has_operations(migration):
            print(f"Skipping no-op migration lint for {migration.as_posix()}.")
            continue
        if _waiver_path(migration).exists():
            print(f"Skipping waived migration lint for {migration.as_posix()}.")
            continue

        command = [
            sys.executable,
            "manage.py",
            "lintmigrations",
            migration.parts[1],
            migration.stem,
            f"--settings={args.settings}",
        ]
        if args.warnings_as_errors:
            command.append("--warnings-as-errors")

        print(f"Linting {migration.as_posix()}...")
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode != 0:
            exit_code = completed.returncode

    return exit_code


def _changed_files_with_status(base_ref: str) -> list[tuple[str, Path]]:
    primary_cmd = [
        "git",
        "diff",
        "--name-status",
        "--diff-filter=AR",
        f"origin/{base_ref}...HEAD",
    ]
    fallback_cmd = ["git", "diff", "--name-status", "--diff-filter=AR", "HEAD~1..HEAD"]

    output = _run_git(primary_cmd) or _run_git(fallback_cmd)
    if output is None:
        return []

    rows = []
    for line in output.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        rows.append((parts[0], Path(parts[-1])))
    return rows


def _run_git(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, cwd=ROOT)
        return completed.stdout
    except subprocess.CalledProcessError:
        return None


def _is_migration_file(path: Path) -> bool:
    parts = path.parts
    if len(parts) < 4:
        return False
    if parts[0] != MIGRATIONS_PREFIX.name:
        return False
    if MIGRATIONS_DIRNAME not in parts:
        return False
    if path.name == "__init__.py":
        return False
    return path.suffix == ".py"


def _waiver_path(path: Path) -> Path:
    return (ROOT / WAIVERS_PREFIX / path).with_suffix(".md")


def _has_operations(path: Path) -> bool:
    try:
        source = (ROOT / path).read_text(encoding="utf-8")
    except OSError:
        return True

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Migration":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "operations":
                            if isinstance(stmt.value, (ast.List, ast.Tuple)):
                                return bool(stmt.value.elts)
    return True


if __name__ == "__main__":
    raise SystemExit(main())
