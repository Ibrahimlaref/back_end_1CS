# Waiver: notifications 0003_notification_delivery_tracking

## Why the risky operation is required
- This migration is the contract phase of the notification delivery redesign.
- The application code now reads `notification_logs.timestamp` and `notification_logs.raw_payload`, so the legacy `attempted_at`, `delivered_at`, and `provider_id` fields are being retired.

## Mitigation steps
- The webhook, analytics, and retry paths were updated before this contract migration landed.
- Rollback is documented in `scripts/rollback/apps/notifications/migrations/0003_notification_delivery_tracking.md`.
- Raw provider payloads are retained in `raw_payload` until rollback is no longer needed.

## Rollback impact
- Rollback recreates the legacy columns but cannot reconstruct dropped values automatically.
- Any delivery metadata that exists only in `raw_payload` must be exported or replayed from the provider if the old schema is restored.

## Approval owner
- Backend platform maintainer for the notifications rollout.
