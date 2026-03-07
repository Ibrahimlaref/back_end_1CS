import os
from celery import Celery
from celery import shared_task
from django.core.management import call_command

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



#churn risk function 
@shared_task
def calculate_churn_scores():
    call_command('churn_risk')