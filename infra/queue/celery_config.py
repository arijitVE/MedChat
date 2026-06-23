# infra/queue/celery_config.py
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from celery import Celery
from shared.config import get_settings

settings = get_settings()

celery_app = Celery(
    "documed_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["pipeline_a.worker.tasks"]
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
