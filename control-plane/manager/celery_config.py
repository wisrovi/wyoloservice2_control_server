"""Celery configuration module for the Manager component.

This module initializes the Celery application with settings optimized for
long-running orchestration tasks, including trial sequencing and result persistence.
"""

import os
from typing import Any
import celery.result
from celery import Celery

# Get Redis URL from environment or default to localhost
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app: Celery = Celery("ml_cluster", broker=REDIS_URL, backend=REDIS_URL)

# Configuration for task routing
app.conf.task_routes = {
    "tasks.manage_study": {"queue": "managers"},
    "tasks.train_on_gpu": {"queue": "gpus"},
}

# Essential settings for long-running studies and nested task waiting
celery_settings: dict[str, Any] = {
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "result_expires": 86400,  # 24 hours
    "task_always_eager": False,
    "result_persistent": True,
}

app.conf.update(celery_settings)

# Allow .get() inside tasks, required for Optuna trial orchestration
celery.result.allow_join_result()
