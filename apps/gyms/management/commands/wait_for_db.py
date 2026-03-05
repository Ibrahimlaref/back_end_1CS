import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait for the database to become available."

    def handle(self, *args, **kwargs):
        self.stdout.write("Waiting for database...")
        for attempt in range(30):
            try:
                connections["default"].ensure_connection()
                self.stdout.write(self.style.SUCCESS("Database ready."))
                return
            except OperationalError:
                self.stdout.write(f"Attempt {attempt + 1}/30: waiting 2s...")
                time.sleep(2)
        raise RuntimeError("Database never became available after 60 seconds.")
