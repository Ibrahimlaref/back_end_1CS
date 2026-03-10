# Rollback Manifest: core 0008_data_retention_models

- Forward migration: `core.0008_data_retention_models`
- Rollback target: `core.0007_rename_request_log_indexes`

## Command
```bash
python manage.py migrate core 0007_rename_request_log_indexes
```

## Notes
- This rollback removes the retention-tracking fields added to `audit_logs`, `access_logs`, `error_logs`, and `system_logs`.
- The reverse data hook restores legacy values where possible before Django drops the new columns.
- Export any data that exists only in `audit_logs.data`, `error_logs.traceback`, or `system_logs.operation/detail/performed_at` before running the rollback.

## Verification
```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name IN ('audit_logs', 'access_logs', 'error_logs', 'system_logs')
  AND column_name IN ('data', 'timestamp', 'user_id', 'ip', 'path', 'level', 'traceback', 'detail', 'operation', 'performed_at');
```

- Expect only the pre-0008 columns to remain after rollback.
