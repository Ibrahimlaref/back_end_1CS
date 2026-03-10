# Rollback Manifest: notifications 0003_notification_delivery_tracking

- Forward migration: `notifications.0003_notification_delivery_tracking`
- Rollback target: `notifications.0002_alter_notificationlog_status_userdevice`

## Command
```bash
python manage.py migrate notifications 0002_alter_notificationlog_status_userdevice
```

## Notes
- This rollback restores the legacy `attempted_at`, `delivered_at`, and `provider_id` schema on `notification_logs`.
- `raw_payload` is dropped on rollback.
- Recreated legacy columns come back empty, so export or reconstruct any delivery data that now exists only inside `raw_payload`.

## Verification
```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'notification_logs'
  AND column_name IN ('attempted_at', 'timestamp', 'delivered_at', 'provider_id', 'raw_payload');
```

- Expect `attempted_at`, `delivered_at`, and `provider_id` to exist, and `raw_payload` / `timestamp` to be absent after rollback.
