# Waiver: core 0008_data_retention_models

## Why the risky operation is required
- The retention rollout adds nullable fields, backfills them, and then enforces the final non-null timestamp shape needed by the current models in the same release.
- Deferring the contract step would require another round of dual-schema model support across retention tasks, admin reporting, and tests.

## Mitigation steps
- Backfill runs before the `AlterField(... null=False / auto_now_add=True)` contract step.
- Rollback is documented in `scripts/rollback/apps/core/migrations/0008_data_retention_models.md`.
- The reverse data hook restores legacy fields before schema rollback.
- Apply during a low-traffic window and monitor DDL lock time on `audit_logs`, `access_logs`, `error_logs`, and `system_logs`.

## Rollback impact
- Newly added retention columns are dropped on rollback.
- Any values stored only in the new columns must be exported before reverting.

## Approval owner
- Backend platform maintainer for the compliance rollout.
