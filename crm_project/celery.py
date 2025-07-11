from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
app = Celery('crm_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.update(
    timezone='UTC',
    enable_utc=True,
)