"""Celery configuration module for the API component.

This module initializes the Celery application with the appropriate
broker and backend settings, and defines task routing.
"""

import os
from typing import Any
from celery import Celery

# Get Redis URL from environment or default to localhost
CONTROL_HOST = os.getenv("CONTROL_HOST", "localhost")
REDIS_URL: str = f"redis://{CONTROL_HOST}:23437/0"

app: Celery = Celery("neuralforge_launcher", broker=REDIS_URL, backend=REDIS_URL)

# Configuration for task routing
app.conf.task_routes = {
    "tasks.manage_study": {"queue": "managers"},
    "tasks.train_on_gpu": {"queue": "gpus"},
}

# Essential settings for long-running training tasks
celery_settings: dict[str, Any] = {
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "result_expires": 86400,  # 24 hours
}

app.conf.update(celery_settings)
