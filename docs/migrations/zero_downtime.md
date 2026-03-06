# Zero-Downtime Migration Strategy

## Goals
- Keep API and worker traffic running during schema changes.
- Guarantee every migration can be rolled back.
- Split breaking schema evolution into safe multi-release phases.

## Required pattern
1. Expand:
- Add new columns as nullable first, or with safe default.
- Add new indexes concurrently when needed (`atomic = False` + `CONCURRENTLY`).
- Never drop/rename fields in the same release that introduces replacements.

2. Migrate data:
- Backfill in batches (management command or Celery task).
- Keep app code dual-read/dual-write while data is being migrated.
- Record progress metrics and verify row counts before contract phase.

3. Contract:
- After all app instances run compatible code and backfill is complete:
  - enforce `NOT NULL` / unique constraints,
  - drop old columns,
  - remove compatibility code.

## Rollback requirements
- Every new migration file must have a rollback manifest under:
  - `scripts/rollback/<app>/migrations/<migration_name>.md`
- Every `RunPython` must include a real `reverse_code`.
- Every `RunSQL` must include `reverse_sql`.

## Risky operation policy
- `RemoveField`, `DeleteModel`, `RenameField`, `RenameModel`, and `AlterField` to `null=False` are risky.
- Risky migrations require a waiver file under:
  - `docs/migrations/waivers/<app>/migrations/<migration_name>.md`

## Pre-deploy rehearsal
- Any PR adding migrations must add a rehearsal report under:
  - `docs/migrations/reports/`
- Report must include dataset size, duration, lock observations, and rollback result.
