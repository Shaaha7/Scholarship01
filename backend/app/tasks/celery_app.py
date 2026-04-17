"""
Celery Application – Async Task Queue
=======================================
Background tasks for:
- PDF processing
- Embedding generation
- Email notifications
- Data ingestion
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "tamilscholar",
    broker=getattr(settings, 'CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672/'),
    backend=getattr(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    include=[
        "app.tasks.embedding_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.ingestion_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)
