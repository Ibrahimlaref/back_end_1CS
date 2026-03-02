import os
from celery import Celery

# Point to your settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brahim.settings.dev')

# Create the Celery app — name matches your project folder
app = Celery('brahim')

# Read config from Django settings, all CELERY_* keys
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in every installed app
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')