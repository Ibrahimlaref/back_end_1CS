import os
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

from apps.core.models import DBSchemaVersion


class Command(BaseCommand):
    help = "Persist a schema version snapshot into db_schema_versions."

    def add_arguments(self, parser):
        parser.add_argument("--git-sha", default=os.getenv("GITHUB_SHA", "unknown"))
        parser.add_argument("--version-label", default="")
        parser.add_argument("--environment", default=os.getenv("DEPLOY_ENV", "dev"))

    def handle(self, *args, **options):
        migration_heads = self._get_migration_heads()

        row = DBSchemaVersion.objects.create(
            git_sha=options["git_sha"],
            version_label=options["version_label"],
            environment=options["environment"],
            migration_heads=migration_heads,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Tracked schema version {row.id} for env={row.environment} git_sha={row.git_sha}"
            )
        )

    @staticmethod
    def _get_migration_heads():
        recorder = MigrationRecorder(connection)
        per_app = defaultdict(list)
        for app, name in recorder.migration_qs.values_list("app", "name"):
            per_app[app].append(name)
        return {app: sorted(names)[-1] for app, names in per_app.items()}
