"""API Module for ML Training Cluster.

This module provides FastAPI endpoints to launch and monitor ML training studies
using Optuna and Celery. It supports YAML configuration uploads and priority-based
task routing.
"""

from typing import Any, Optional

import yaml
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from celery.result import AsyncResult

# Import Celery app from the local configuration
from celery_config import app as celery_app

app: FastAPI = FastAPI(title="ML CLUSTER API v5 - Strict Priority & Private Mode")


@app.post("/train")
async def start_training(
    config_file: UploadFile = File(...),
    mode: str = Form("public", description="Execution mode: public or private"),
    worker_name: Optional[str] = Form(
        None, description="Target worker name (for private mode)"
    ),
    priority: str = Form(
        "medium", description="Priority: high, medium, low (public mode only)"
    ),
) -> dict[str, str]:
    """Launches a new training study based on a YAML configuration.

    Args:
        config_file (UploadFile): The YAML configuration file for the study.
        mode (str, optional): The execution mode. Defaults to "public".
        worker_name (Optional[str], optional): The target worker name. Required if mode is private.
        priority (str, optional): The task priority. Defaults to "medium".

    Returns:
        dict[str, str]: A dictionary containing the job status and study ID.

    Raises:
        HTTPException: If the file is not a YAML or if private mode lacks a worker name.
    """
    if not config_file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not config_file.filename.lower().endswith((".yaml", ".yml")):
        raise HTTPException(
            status_code=400, detail="File must be a YAML (.yaml or .yml)"
        )

    try:
        content: bytes = await config_file.read()
        config_data: dict[str, Any] = yaml.safe_load(content)

        # Determine the target worker queue based on mode and priority
        if mode == "private":
            if not worker_name:
                raise HTTPException(
                    status_code=400, detail="Worker name is required for private mode"
                )
            target_worker_queue: str = worker_name
        else:
            # Map priority labels to specific queues for strict ordering
            priority_map: dict[str, str] = {
                "high": "gpus_high",
                "medium": "gpus_medium",
                "low": "gpus_low",
            }
            target_worker_queue = priority_map.get(priority.lower(), "gpus_medium")

        # Inject targeting information for the Manager orchestrator
        if "sweeper" not in config_data:
            config_data["sweeper"] = {}
        config_data["sweeper"]["target_worker_queue"] = target_worker_queue

        # Dispatch the study management task to the Celery 'managers' queue
        job: AsyncResult = celery_app.send_task(
            "tasks.manage_study", args=[config_data], queue="managers"
        )

        return {
            "status": "Queued",
            "study_id": str(job.id),
            "mode": mode,
            "worker_queue": target_worker_queue,
        }
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid YAML format: {exc}"
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@app.get("/workers")
async def get_available_workers() -> list[str]:
    """Retrieves a list of active workers with private queues.

    Returns:
        list[str]: A sorted list of private queue names (starting with 'worker_').
    """
    import redis

    workers = set()
    try:
        redis_url = celery_app.conf.broker.replace("/0", "/1")
        r = redis.from_url(redis_url)
        keys = r.keys("celery*")
        for key in keys:
            if b"worker_" in key:
                name = key.decode().replace("celery$", "").replace("celery%", "")
                if name.startswith("worker_"):
                    workers.add(name)
    except Exception:
        pass

    try:
        inspector = celery_app.control.inspect()
        active = inspector.active_queues()
        if active:
            for _, queues in active.items():
                for queue_info in queues:
                    queue_name = queue_info.get("name", "")
                    if queue_name.startswith("worker_"):
                        workers.add(queue_name)
    except Exception as exc:
        print(f"Error inspecting workers: {exc}")

    return sorted(list(workers))


@app.get("/status/{study_id}")
async def get_status(study_id: str) -> dict[str, Any]:
    """Gets the status and result of a specific study.

    Args:
        study_id (str): The Celery task ID for the study.

    Returns:
        dict[str, Any]: The study details including state and completion result.
    """
    res: AsyncResult = AsyncResult(study_id, app=celery_app)
    return {
        "study_id": study_id,
        "state": str(res.state),
        "result": res.result if res.ready() else None,
    }


@app.get("/tasks")
async def list_queued_tasks() -> dict[str, Any]:
    """Lists all pending tasks in the managers queue.

    Returns:
        dict[str, Any]: Dictionary with queued tasks info.
    """
    try:
        inspector = celery_app.control.inspect()
        scheduled = inspector.scheduled()
        reserved = inspector.reserved()

        tasks = []

        if scheduled:
            for worker, worker_tasks in scheduled.items():
                for task in worker_tasks:
                    if task.get("name") == "tasks.manage_study":
                        tasks.append(
                            {
                                "task_id": task.get("id"),
                                "name": task.get("name"),
                                "state": "scheduled",
                                "worker": worker,
                                "args": str(task.get("args", []))[:200],
                            }
                        )

        if reserved:
            for worker, worker_tasks in reserved.items():
                for task in worker_tasks:
                    if task.get("name") == "tasks.manage_study":
                        tasks.append(
                            {
                                "task_id": task.get("id"),
                                "name": task.get("name"),
                                "state": "reserved",
                                "worker": worker,
                                "args": str(task.get("args", []))[:200],
                            }
                        )

        return {"queued_tasks": tasks, "count": len(tasks)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error listing tasks: {exc}")


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> dict[str, Any]:
    """Revokes (deletes) a pending task by ID.

    Args:
        task_id (str): The Celery task ID to revoke.

    Returns:
        dict[str, Any]: Confirmation message.
    """
    try:
        celery_app.control.revoke(task_id, terminate=False)
        return {"status": "revoked", "task_id": task_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error revoking task: {exc}")


@app.post("/tasks/{task_id}/requeue")
async def requeue_with_priority(
    task_id: str,
    priority: str = Form("medium", description="New priority: high, medium, or low"),
) -> dict[str, Any]:
    """Re-queues a task with a different priority.

    Args:
        task_id (str): The original task ID to re-queue.
        priority (str, optional): New priority. Defaults to "medium".

    Returns:
        dict[str, Any]: New task info.
    """
    try:
        celery_app.control.revoke(task_id, terminate=False)

        priority_map = {
            "high": "gpus_high",
            "medium": "gpus_medium",
            "low": "gpus_low",
        }
        target_queue = priority_map.get(priority.lower(), "gpus_medium")

        job = celery_app.send_task(
            "tasks.manage_study",
            queue="managers",
            kwargs={
                "_requeue": True,
                "original_task_id": task_id,
                "new_priority": target_queue,
            },
        )

        return {
            "status": "requeued",
            "original_task_id": task_id,
            "new_task_id": str(job.id),
            "new_priority": priority,
            "target_queue": target_queue,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error re-queueing: {exc}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
