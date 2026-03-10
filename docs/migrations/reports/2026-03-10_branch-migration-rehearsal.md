# Branch Migration Rehearsal

- Date: 2026-03-10
- Branch reference: `badro/System`
- Scope:
  - `apps/core/migrations/0008_data_retention_models.py`
  - `apps/membersNsubscription/migrations/0001_initial.py`
  - `apps/notifications/migrations/0003_notification_delivery_tracking.py`
  - `apps/users/migrations/0005_user_retention_fields.py`
  - `apps/users/migrations/0006_merge_20260310_0153.py`

## Environment
- PostgreSQL: local dev / CI-style database
- Django commands:
  - `python manage.py makemigrations --check --dry-run`
  - `python manage.py migrate --noinput`
  - targeted pytest coverage for notifications, retention, health, and observability

## Dataset scale
- Schema rehearsal was run against a clean local database in this workspace.
- No production-scale anonymized snapshot is available in the repository, so the affected tables were effectively empty before apply.

## Duration
- Schema creation and targeted migration runs completed within the normal local CI startup window.
- `membersNsubscription.0001_initial` is the heaviest migration by object count and should still be scheduled off-peak on non-empty databases.

## Lock observations
- Strict backward-compatibility lint flags the contract-style operations in:
  - `core.0008_data_retention_models`
  - `notifications.0003_notification_delivery_tracking`
  - `users.0005_user_retention_fields`
- Those migrations are documented with waivers and rollback manifests because they intentionally perform contract-phase schema cleanup in this release.

## Rollback result
- Rollback commands were verified against the current migration graph and documented per migration under `scripts/rollback/...`.
- `core.0008_data_retention_models` now includes a real reverse data hook instead of `RunPython.noop`.

## Verification summary
- `apps/notifications/tests/test_notification_log.py`
- `apps/core/tests/test_retention.py`
- `apps/core/tests/test_health.py`
- `apps/core/tests/test_observability.py`
- Post-rollback verification queries are included in each rollback manifest.
