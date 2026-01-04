"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "polititrack",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.refresh_politicians",
        "app.tasks.refresh_votes",
        "app.tasks.refresh_finance",
        "app.tasks.refresh_stocks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
)

# Scheduled tasks (beat schedule)
celery_app.conf.beat_schedule = {
    # Refresh politicians weekly (Sunday at 2 AM UTC)
    "refresh-politicians-weekly": {
        "task": "app.tasks.refresh_politicians.refresh_all_politicians",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
    },
    # Refresh votes weekly (Sunday at 3 AM UTC)
    "refresh-votes-weekly": {
        "task": "app.tasks.refresh_votes.refresh_all_votes",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
    # Refresh finance weekly (Sunday at 4 AM UTC)
    "refresh-finance-weekly": {
        "task": "app.tasks.refresh_finance.refresh_all_finance",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
    },
    # Refresh stock trades daily (6 AM UTC)
    "refresh-stocks-daily": {
        "task": "app.tasks.refresh_stocks.refresh_all_stocks",
        "schedule": crontab(hour=6, minute=0),
    },
}
