# Rollback Manifest: users 0005_user_retention_fields

- Forward migration: `users.0005_user_retention_fields`
- Rollback target: `users.0005_merge_0004_emailotp_and_sessionlog`

## Command
```bash
python manage.py migrate users 0005_merge_0004_emailotp_and_sessionlog
```

## Notes
- This rollback removes `deleted_at`, `is_deleted`, and `is_anonymised` from `users`.
- Export any compliance state that has been written to those columns before rollback.
- Run this from the merged branch state so both `users.0004_*` migrations remain applied.

## Verification
```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('deleted_at', 'is_deleted', 'is_anonymised');
```

- Expect no rows after rollback.
