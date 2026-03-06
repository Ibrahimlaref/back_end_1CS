import importlib
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from apps.core.models import Gym, SystemLog
from apps.users.models.user import SessionLog, User
from apps.users.services.session_cleanup_service import SessionCleanupService
from apps.users.tasks import cleanup_session_logs


class SessionCleanupServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="cleanup@example.com", password="Password123!")
        self.gym = Gym.objects.create(name="Cleanup Gym", slug="cleanup-gym")
        self.service = SessionCleanupService()

    def _create_session(self, **updates):
        session = SessionLog.objects.create(
            user=self.user,
            gym=self.gym,
            jwt_jti=str(uuid.uuid4()),
        )
        if updates:
            SessionLog.objects.filter(id=session.id).update(**updates)
            session.refresh_from_db()
        return session

    def test_purge_deletes_only_expired_inactive_sessions(self):
        now = timezone.now()

        old_revoked = self._create_session(
            is_revoked=True,
            logged_in_at=now - timedelta(days=40),
            logged_out_at=now - timedelta(days=31),
        )
        old_inactive = self._create_session(
            is_revoked=False,
            logged_in_at=now - timedelta(days=91),
            logged_out_at=now - timedelta(days=10),
        )
        old_active = self._create_session(
            is_revoked=False,
            logged_in_at=now - timedelta(days=200),
            logged_out_at=None,
        )
        revoked_boundary = self._create_session(
            is_revoked=True,
            logged_in_at=now - timedelta(days=35),
            logged_out_at=now - timedelta(days=30),
        )
        stale_boundary = self._create_session(
            is_revoked=False,
            logged_in_at=now - timedelta(days=90),
            logged_out_at=now - timedelta(days=1),
        )

        result = self.service.purge_expired_sessions(now=now, batch_size=2)

        self.assertEqual(result["deleted_count"], 2)
        self.assertFalse(SessionLog.objects.filter(id=old_revoked.id).exists())
        self.assertFalse(SessionLog.objects.filter(id=old_inactive.id).exists())
        self.assertTrue(SessionLog.objects.filter(id=old_active.id).exists())
        self.assertTrue(SessionLog.objects.filter(id=revoked_boundary.id).exists())
        self.assertTrue(SessionLog.objects.filter(id=stale_boundary.id).exists())

    def test_session_log_index_exists(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, SessionLog._meta.db_table)
        self.assertIn("sessionlog_user_revoked_idx", constraints)


class SessionCleanupTaskTests(TestCase):
    def test_cleanup_task_logs_success(self):
        now = timezone.now()
        fake_result = {
            "deleted_count": 7,
            "revoked_cutoff": now - timedelta(days=30),
            "stale_cutoff": now - timedelta(days=90),
            "batch_size": 5000,
        }

        with patch(
            "apps.users.tasks.SessionCleanupService.purge_expired_sessions",
            return_value=fake_result,
        ):
            result = cleanup_session_logs.run()

        self.assertEqual(result["deleted_count"], 7)
        log = SystemLog.objects.get(event=SessionCleanupService.EVENT_NAME, level=SystemLog.Level.INFO)
        self.assertEqual(log.metadata["deleted_count"], 7)
        self.assertEqual(log.metadata["batch_size"], 5000)
        self.assertIn("duration_ms", log.metadata)

    def test_cleanup_task_logs_error_and_retries(self):
        with patch(
            "apps.users.tasks.SessionCleanupService.purge_expired_sessions",
            side_effect=RuntimeError("db unavailable"),
        ), patch.object(
            cleanup_session_logs,
            "retry",
            side_effect=RuntimeError("retry called"),
        ) as retry_mock:
            with self.assertRaises(RuntimeError):
                cleanup_session_logs.run()

        retry_mock.assert_called_once()
        log = SystemLog.objects.get(event=SessionCleanupService.EVENT_NAME, level=SystemLog.Level.ERROR)
        self.assertEqual(log.metadata["error"], "db unavailable")
        self.assertIn("duration_ms", log.metadata)


class SessionCleanupScheduleMigrationTests(TestCase):
    def setUp(self):
        self.migration = importlib.import_module("apps.users.migrations.0004_sessionlog_cleanup_job")

    class _BeatApps:
        @staticmethod
        def get_model(app_label, model_name):
            if app_label != "django_celery_beat":
                raise LookupError(f"Unexpected app label: {app_label}")
            if model_name == "CrontabSchedule":
                return CrontabSchedule
            if model_name == "PeriodicTask":
                return PeriodicTask
            raise LookupError(f"Unexpected model name: {model_name}")

    def test_seed_creates_weekly_periodic_task(self):
        self.migration.seed_session_cleanup_periodic_task(self._BeatApps(), schema_editor=None)

        task = PeriodicTask.objects.get(name="users.session-log-cleanup-weekly")
        self.assertEqual(task.task, "apps.users.tasks.cleanup_session_logs")
        self.assertEqual(task.queue, "scheduled")
        self.assertTrue(task.enabled)
        self.assertEqual(task.crontab.minute, "0")
        self.assertEqual(task.crontab.hour, "3")
        self.assertEqual(task.crontab.day_of_week, "0")

    def test_reverse_removes_periodic_task(self):
        self.migration.seed_session_cleanup_periodic_task(self._BeatApps(), schema_editor=None)
        self.migration.remove_session_cleanup_periodic_task(self._BeatApps(), schema_editor=None)
        self.assertFalse(PeriodicTask.objects.filter(name="users.session-log-cleanup-weekly").exists())
