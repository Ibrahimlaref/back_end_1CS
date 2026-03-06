# Schema Governance Baseline Rehearsal

- Date: 2026-03-06
- Scope:
  - `apps/core/migrations/0004_request_log.py`
  - `apps/core/migrations/0005_systemlog.py`
  - `apps/core/migrations/0006_dbschemaversion.py`
  - `apps/core/migrations/0007_rename_request_log_indexes.py`
  - `apps/users/migrations/0004_sessionlog_cleanup_job.py`

## Environment
- PostgreSQL: local container/dev instance
- Django: `manage.py migrate` on clean test database

## Observations
- Migrations applied successfully without runtime errors.
- No long-running blocking operations observed in this baseline run.
- Reversal path documented per migration under `scripts/rollback/...`.

## Rollback rehearsal summary
- Rollback commands validated syntactically via rollback manifests.
- Full rollback drill to previous release is planned per release runbook.

## Verification checks
- `request_logs`, `system_logs`, and `db_schema_versions` tables created.
- Session cleanup periodic task seeded.
- Composite index `sessionlog_user_revoked_idx` present.
