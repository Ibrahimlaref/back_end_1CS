#!/usr/bin/env python
"""
Fail CI when new migrations violate zero-downtime governance rules.
"""

import argparse
import ast
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_PREFIX = Path("apps")
REPORTS_PREFIX = Path("docs/migrations/reports")
WAIVERS_PREFIX = Path("docs/migrations/waivers")
ROLLBACK_PREFIX = Path("scripts/rollback")
MIGRATIONS_DIRNAME = "migrations"

RISKY_OPS = {"RemoveField", "DeleteModel", "RenameField", "RenameModel"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="main")
    args = parser.parse_args()

    changed_status = _changed_files_with_status(args.base_ref)
    changed_paths = [path for _, path in changed_status]
    new_migrations = [
        path
        for status, path in changed_status
        if status.startswith("A") and _is_migration_file(path)
    ]

    if not new_migrations:
        print("No new migration files found. Governance check skipped.")
        return 0

    failures = []
    migration_report_changed = any(path.as_posix().startswith(REPORTS_PREFIX.as_posix()) for path in changed_paths)
    if not migration_report_changed:
        failures.append(
            "At least one report must be added under docs/migrations/reports/ for production-scale rehearsal evidence."
        )

    for migration in new_migrations:
        failures.extend(_validate_migration(migration))

    if failures:
        print("Migration governance check failed:")
        for issue in failures:
            print(f"- {issue}")
        return 1

    print("Migration governance check passed.")
    return 0


def _changed_files_with_status(base_ref):
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
        status = parts[0]
        path_value = parts[-1]
        rows.append((status, Path(path_value)))
    return rows


def _run_git(cmd):
    try:
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return completed.stdout
    except subprocess.CalledProcessError:
        return None


def _is_migration_file(path):
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


def _validate_migration(path):
    failures = []
    full_path = ROOT / path
    rollback_path = (ROOT / ROLLBACK_PREFIX / path).with_suffix(".md")

    if not rollback_path.exists():
        failures.append(
            f"Missing rollback manifest for {path.as_posix()} at {rollback_path.relative_to(ROOT).as_posix()}."
        )

    try:
        source = full_path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(f"Unable to read migration {path.as_posix()}: {exc}")
        return failures

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        failures.append(f"Migration {path.as_posix()} has syntax error: {exc}")
        return failures

    operations = _migration_operations(tree)
    needs_waiver = False

    for op in operations:
        op_name = _call_name(op)
        if op_name == "AddField":
            add_field_issue = _validate_add_field(op, path)
            if add_field_issue:
                failures.append(add_field_issue)
        elif op_name == "RunPython":
            runpython_issue = _validate_runpython_reverse(op, path)
            if runpython_issue:
                failures.append(runpython_issue)
        elif op_name == "RunSQL":
            runsql_issue = _validate_runsql_reverse(op, path)
            if runsql_issue:
                failures.append(runsql_issue)
        elif op_name in RISKY_OPS:
            needs_waiver = True
        elif op_name == "AlterField" and _is_null_enforcement(op):
            needs_waiver = True

    if needs_waiver:
        waiver_path = (ROOT / WAIVERS_PREFIX / path).with_suffix(".md")
        if not waiver_path.exists():
            failures.append(
                f"Risky migration {path.as_posix()} requires waiver at {waiver_path.relative_to(ROOT).as_posix()}."
            )

    return failures


def _migration_operations(tree):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Migration":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "operations":
                            if isinstance(stmt.value, (ast.List, ast.Tuple)):
                                return [item for item in stmt.value.elts if isinstance(item, ast.Call)]
    return []


def _call_name(call):
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _kwarg(call, name):
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _literal_bool(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return None


def _field_call(call):
    field = _kwarg(call, "field")
    return field if isinstance(field, ast.Call) else None


def _field_type_name(field_call):
    if isinstance(field_call.func, ast.Attribute):
        return field_call.func.attr
    if isinstance(field_call.func, ast.Name):
        return field_call.func.id
    return ""


def _validate_add_field(call, path):
    field = _field_call(call)
    if field is None:
        return None

    field_type = _field_type_name(field)
    if field_type == "ManyToManyField":
        return None

    null_value = _literal_bool(_kwarg(field, "null"))
    has_default = _kwarg(field, "default") is not None

    # Zero-downtime guard: new columns should be nullable first or have explicit safe default.
    if (null_value is False or null_value is None) and not has_default:
        return (
            f"{path.as_posix()}: AddField must be nullable first or include a default for expand phase "
            "(expand -> migrate data -> contract)."
        )
    return None


def _validate_runpython_reverse(call, path):
    reverse_code = _kwarg(call, "reverse_code")
    if reverse_code is None:
        return f"{path.as_posix()}: RunPython requires reverse_code for rollback support."

    if isinstance(reverse_code, ast.Attribute) and reverse_code.attr == "noop":
        return f"{path.as_posix()}: RunPython reverse_code cannot be noop in this policy."
    return None


def _validate_runsql_reverse(call, path):
    reverse_sql = _kwarg(call, "reverse_sql")
    if reverse_sql is None:
        return f"{path.as_posix()}: RunSQL requires reverse_sql for rollback support."

    if isinstance(reverse_sql, ast.Constant) and reverse_sql.value in ("", None):
        return f"{path.as_posix()}: RunSQL reverse_sql cannot be empty."
    return None


def _is_null_enforcement(call):
    field = _field_call(call)
    if field is None:
        return False
    return _literal_bool(_kwarg(field, "null")) is False


if __name__ == "__main__":
    sys.exit(main())
