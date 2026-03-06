from django.core.management import call_command
from django.test import TestCase

from apps.core.models import DBSchemaVersion


class TrackSchemaVersionCommandTests(TestCase):
    def test_command_creates_schema_version_row(self):
        call_command(
            "track_schema_version",
            git_sha="abc123",
            version_label="release-2026-03-06",
            environment="ci",
        )

        row = DBSchemaVersion.objects.get()
        self.assertEqual(row.git_sha, "abc123")
        self.assertEqual(row.version_label, "release-2026-03-06")
        self.assertEqual(row.environment, "ci")
        self.assertIn("core", row.migration_heads)
