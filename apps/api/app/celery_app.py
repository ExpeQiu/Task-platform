from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "task_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.dispatch", "app.tasks.watchdog", "app.tasks.scheduler"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "watchdog-scan": {
            "task": "app.tasks.watchdog.run_watchdog",
            "schedule": float(settings.watchdog_interval_seconds),
        },
        "process-scheduled-jobs": {
            "task": "app.tasks.scheduler.process_scheduled_jobs",
            "schedule": 30.0,
        },
    },
)
