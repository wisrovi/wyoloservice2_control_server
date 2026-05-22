"""API Module for ML Training Cluster.

This module provides FastAPI endpoints to launch and monitor ML training studies
using Optuna and Celery. It supports YAML configuration uploads and priority-based
task routing.
"""

from typing import Any, Optional
import shutil
import redis
import yaml
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from celery.result import AsyncResult

# Import Celery app from the local configuration
from celery_config import app as celery_app

from fastapi.middleware.cors import CORSMiddleware

app: FastAPI = FastAPI(title="ML CLUSTER API v5 - Strict Priority & Private Mode")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/workers/count")
async def get_workers_count() -> dict[str, int]:
    """Returns the count of active workers."""
    workers = await get_available_workers()
    return {"count": len(workers), "value": len(workers)}

@app.get("/tasks/count")
async def get_tasks_count() -> dict[str, int]:
    """Returns the count of tasks in the managers queue."""
    try:
        r = redis.from_url(celery_app.conf.broker)
        count = r.llen("managers")
        return {"count": count, "value": count}
    except Exception:
        return {"count": 0, "value": 0}

@app.get("/tasks/active")
async def get_active_tasks() -> dict[str, Any]:
    """Returns a list of currently active tasks."""
    try:
        # Increase timeout for inspector to wait for worker replies
        inspector = celery_app.control.inspect(timeout=1.0)
        active = inspector.active()
        tasks = []
        if active:
            for worker_name, worker_tasks in active.items():
                for task in worker_tasks:
                    # Clean up worker name
                    short_worker = worker_name.split('@')[-1]
                    
                    tasks.append({
                        "id": task.get("id"),
                        "name": task.get("name", "Unknown"),
                        "worker": short_worker,
                        "runtime": round(task.get("runtime", 0), 1),
                        "epoch": "Orchestrating..." if "manage_study" in task.get("name", "") else "Training...",
                        "progress": 50 if "manage_study" in task.get("name", "") else 20, # Simulation
                        "map": "0.000"
                    })
        return {"jobs": tasks, "value": len(tasks)}
    except Exception as e:
        print(f"Error fetching active tasks: {e}")
        return {"jobs": [], "value": 0}

@app.get("/metrics/gpu")
async def get_gpu_metrics() -> dict[str, Any]:
    """Returns simulated or real GPU utilization metrics."""
    return {"utilization": 45.5, "unit": "%", "value": 45.5}

@app.get("/metrics/storage")
async def get_storage_metrics() -> dict[str, Any]:
    """Returns storage usage metrics for the datasets directory."""
    import os
    path = "/wyolo/control_server/datasets"
    if not os.path.exists(path):
        path = "/app"
        
    try:
        usage = shutil.disk_usage(path)
        percent = (usage.used / usage.total) * 100
        # Convert to TB for dashboard display
        val_tb = round(usage.used / (1024**4), 2)
        return {
            "used": usage.used,
            "total": usage.total,
            "percent": percent,
            "value": val_tb if val_tb > 0 else round(usage.used / (1024**3), 2) # Show GB if TB is 0
        }
    except Exception:
        return {"used": 0, "total": 0, "percent": 0, "value": 0}

@app.get("/metrics/redis")
async def get_redis_metrics() -> dict[str, Any]:
    """Returns Redis memory usage metrics."""
    try:
        r = redis.from_url(celery_app.conf.broker)
        info = r.info("memory")
        used_gb = round(info.get("used_memory", 0) / (1024**3), 2)
        return {
            "used_memory": info.get("used_memory_human"),
            "peak_memory": info.get("used_memory_peak_human"),
            "value": 8,  # Total GB simulation
            "used_gb": used_gb
        }
    except Exception:
        return {"used_memory": "0B", "peak_memory": "0B", "value": 0, "used_gb": 0}


import json

# Connection for shared persistence (Users/Projects) - Use DB 2 to avoid Celery conflict
shared_db = redis.from_url(celery_app.conf.broker_url.replace("/0", "/2"))

# --- PERSISTENCE ENDPOINTS (Users & Projects) ---

@app.get("/config/users")
async def get_users():
    """Retrieves all registered users from shared storage."""
    data = shared_db.get("registry:users")
    return json.loads(data) if data else []

@app.post("/config/users")
async def save_users(users: list[dict[str, Any]]):
    """Overwrites the user registry in shared storage."""
    shared_db.set("registry:users", json.dumps(users))
    return {"status": "success"}

@app.get("/config/projects")
async def get_projects():
    """Retrieves all registered projects from shared storage."""
    data = shared_db.get("registry:projects")
    return json.loads(data) if data else []

@app.post("/config/projects")
async def save_projects(projects: list[dict[str, Any]]):
    """Overwrites the project registry in shared storage."""
    shared_db.set("registry:projects", json.dumps(projects))
    return {"status": "success"}


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

        # Robustness check: Ensure config_data is a dictionary
        if not isinstance(config_data, dict):
            raise HTTPException(
                status_code=400, 
                detail="Invalid YAML: content must be a dictionary (key-value pairs)"
            )

        # Determine the target worker queue based on mode
        if mode == "private":
            if not worker_name:
                raise HTTPException(
                    status_code=400, detail="Worker name is required for private mode"
                )
            # Inject targeting information ONLY for private mode
            if "sweeper" not in config_data:
                config_data["sweeper"] = {}
            config_data["sweeper"]["target_worker_queue"] = worker_name
            target_info = f"private:{worker_name}"
        else:
            # In public mode, we don't inject target_worker_queue to let the Manager 
            # use its default logic (same as the test script)
            target_info = f"public:{priority}"

        # Dispatch the study management task to the Celery 'managers' queue
        job: AsyncResult = celery_app.send_task(
            "tasks.manage_study", args=[config_data], queue="managers"
        )

        return {
            "status": "Queued",
            "study_id": str(job.id),
            "mode": mode,
            "routing": target_info,
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
