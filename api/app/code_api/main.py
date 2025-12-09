from typing import Dict, Any, List, Optional
import json
import random
import time
import asyncio
from datetime import datetime, timedelta
from api_models.dto import TrainingJobRequest
from data_example import mock_jobs

try:
    from fastapi import FastAPI, HTTPException, File, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    print("FastAPI not installed. Run: pip install -r requirements.txt")
    exit(1)


import os
import shutil
import uuid

import yaml
from database import TrainingHistory, db

# from api.minio import download_model, list_models
from wredis.queue import RedisQueueManager

CONFIG_DIR = "/config_versions"
os.makedirs(CONFIG_DIR, exist_ok=True)


config_path = "/config/config.yaml"
with open(config_path, "r") as f:
    cfg = yaml.safe_load(f)


redis_config = cfg.get("redis", {})
queue_manager = RedisQueueManager(
    host="redis",
    port=6379,
    db=redis_config.get("REDIS_DB"),
)


app = FastAPI(title="NeuroForge AI Backend", version="1.0.0")


# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5810", "http://192.168.1.84:5810"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/recreate/")
def recreate(
    user_code: str,
    task_id: str,
    last_model: str,
    file: UploadFile = File(...),
    resume: bool = True,
    destinity: str = "recreate",
):
    config_path = os.path.join(CONFIG_DIR, f"{task_id}.yaml")
    with open(config_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f)

    # validar si resume esta presente
    user_config["train"]["resume"] = True

    user_config["request_by"] = user_code
    user_config["task_id"] = task_id

    # esto fuerza el sistema a que use el modelo entregado y reportado como last_model
    user_config["sweeper"]["model"] = ["choice", last_model]
    user_config["model"] = last_model
    user_config["recreate"] = True

    # actualizar el config_path en el archivo de configuracion original
    with open(config_path, "w") as f:
        yaml.dump(user_config, f)

    try:
        count = len(db.get_all())
    except Exception:
        count = 0

    # Insertar un nuevo usuario con el nuevo campo
    db.insert(
        TrainingHistory(
            id=count + 1,
            task_id=task_id,
            status="pending",
            user_code=user_code,
            config_path=config_path,
        )
    )

    queue_manager.publish(
        queue_name=destinity,
        data={
            "task_id": task_id,
            "config_path": config_path,
            "user_code": user_code,
            "db_count": count + 1,
        },
    )

    return {"message": "Entrenamiento registrado", "task_id": task_id}


@app.post("/evaluate/")
def evaluate(user_code: str, data_yaml: str, model_path: str, topic: str = "evaluate"):
    """Ejecuta una evaluación de un modelo en un conjunto de datos.

    Args:
        user_code (str): Código del usuario que solicita la evaluación.
        data_yaml (str): Ruta al archivo YAML que contiene la configuración de los datos.
        model_path (str): Ruta al modelo a evaluar.
        topic (str): Nombre del tema en Redis donde se publicará la tarea. Por defecto es "evaluate".

    Returns:
        dict: Mensaje de confirmación y el ID de la tarea.
    """

    task_id = str(uuid.uuid4()).replace("-", "").replace("_", "")

    queue_manager.publish(
        queue_name=topic,
        data={
            "task_id": task_id,
            "user_code": user_code,
            "data_yaml": data_yaml,
            "model_path": model_path,
        },
    )
    return {"message": "Evaluación registrada", "task_id": task_id}


@app.post("/stop/")
def stop_training(user_code: str, file: UploadFile = File(...)):
    """Detiene un entrenamiento en curso."""

    # Detener el entrenamiento en curso
    start_training(user_code=user_code, file=file, resume=False)


@app.post("/train/")
def start_training(user_code: str, file: UploadFile = File(...), resume: bool = False):
    """Registra un entrenamiento y lo encola en Redis."""

    task_id = str(uuid.uuid4()).replace("-", "").replace("_", "")

    config_path = os.path.join(CONFIG_DIR, f"{task_id}.yaml")
    with open(config_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with open(config_path, "r") as f:
        user_config = yaml.safe_load(f)

    # validar si resume esta presente
    if resume:
        user_config["train"]["resume"] = True

    user_config["request_by"] = user_code
    user_config["task_id"] = task_id

    # actualizar el config_path en el archivo de configuracion original
    with open(config_path, "w") as f:
        yaml.dump(user_config, f)

    try:
        count = len(db.get_all())
    except Exception:
        count = 0

    # Insertar un nuevo usuario con el nuevo campo
    db.insert(
        TrainingHistory(
            id=count + 1,
            task_id=task_id,
            status="pending",
            user_code=user_code,
            config_path=config_path,
        )
    )

    queue_topic = user_config.get("debug", redis_config.get("TOPIC"))

    queue_manager.publish(
        queue_name=queue_topic,
        data={
            "task_id": task_id,
            "config_path": config_path,
            "user_code": user_code,
            "db_count": count + 1,
        },
    )

    return {"message": "Entrenamiento registrado", "task_id": task_id}


# @app.get("/trainings/")
# def get_trainings():
#     """Consulta los entrenamientos registrados."""
#     return db.get_all()


# @app.get("/best_model/{experiment_name}")
# def get_best_model(experiment_name: str):
#     """Devuelve el mejor modelo del experimento."""

#     versions = db.get_by_field(experiment_name=experiment_name)
#     best_version = max(versions, key=lambda v: v.loss)
#     if best_version:
#         return {
#             "experiment_name": experiment_name,
#             "best_model": best_version.recommended_model,
#             "metrics": {
#                 "loss": best_version.loss,
#                 "precision": best_version.precision,
#                 "recall": best_version.recall,
#                 "map50": best_version.map50,
#                 "map50_95": best_version.map50_95,
#             },
#         }
#     return {"message": "No se encontró un mejor modelo"}


# @app.get("/model_versions/{task_id}")
# def get_model_versions(task_id: str):
#     """Devuelve todas las versiones de un modelo almacenadas en MinIO."""

#     versions = db.get_by_field(task_id=task_id)

#     return [
#         {"version": v.task_id.split("_v")[-1], "url": v.model_path} for v in versions
#     ]


# @app.get("/models/")
# def list_all_models():
#     """Lista todos los modelos almacenados en MinIO."""
#     return list_models()


# @app.get("/download_model/{model_name}")
# def download_model_endpoint(model_name: str):
#     """Descarga un modelo desde MinIO."""
#     save_path = f"/tmp/{model_name}"
#     download_model(model_name, save_path)
#     return {"message": "Modelo descargado", "path": save_path}


@app.post("/posts")
async def generic_post_endpoint(request: Dict[str, Any]):
    """Generic POST endpoint that handles all frontend requests"""
    
    # Simulate processing time
    await asyncio.sleep(0.1)
    
    # Check if this is a metrics request based on query parameters
    if "metric" in request:
        metric_type = request.get("metric", "")
        
        if metric_type == "workers":
            # Random number of active workers
            random_int = random.randint(2, 10)
            return {
                "id": random.randint(1, 1000),
                "value": random.randint(8, 24),
                "timestamp": datetime.now().isoformat(),
                "metric": "active_workers",
                "active_nodes": random_int
            }
        
        elif metric_type == "gpu":
            # Random GPU utilization with some variation
            base_util = random.uniform(65.0, 95.0)
            gpu_count = random.randint(1, 4)
            return {
                "id": random.randint(1, 1000),
                "value": round(base_util, 1),
                "timestamp": datetime.now().isoformat(),
                "metric": "gpu_utilization",
                "gpu_count": gpu_count,
                "avg_util": round(base_util * 0.9, 1),
                "peak_util": round(min(100, base_util * 1.1), 1)
            }
        
        elif metric_type == "queue":
            # Random queue depth with priority jobs
            total_jobs = random.randint(3, 18)
            priority_jobs = random.randint(0, min(5, total_jobs))
            return {
                "id": random.randint(1, 1000),
                "value": total_jobs,
                "timestamp": datetime.now().isoformat(),
                "metric": "queue_depth",
                "priority_jobs": priority_jobs,
                "normal_jobs": total_jobs - priority_jobs
            }
        
        elif metric_type == "storage":
            # Random storage usage with breakdown
            total_storage = random.uniform(2.1, 8.7)
            used_storage = total_storage * random.uniform(0.6, 0.9)
            return {
                "id": random.randint(1, 1000),
                "value": round(total_storage, 1),
                "timestamp": datetime.now().isoformat(),
                "metric": "storage_used_tb",
                "used_tb": round(used_storage, 1),
                "free_tb": round(total_storage - used_storage, 1),
                "usage_percent": round((used_storage / total_storage) * 100, 1)
            }
        
        elif metric_type == "jobs_list":
            # Random number of jobs to show
            random_int = random.randint(2, 10)
            random_int = min(random_int, len(mock_jobs))
            
            # Add some random progress updates to jobs
            jobs_to_return = []
            for job in mock_jobs[:random_int]:
                job_copy = job.copy()
                if job["status"] == "running":
                    job_copy["progress"] = min(100, job["progress"] + random.randint(-5, 10))
                    job_copy["eta"] = f"{random.randint(1, 30)}m"
                elif job["status"] == "queued" and random.random() > 0.7:
                    # Occasionally promote queued jobs to running
                    job_copy["status"] = "running"
                    job_copy["progress"] = random.randint(1, 15)
                    job_copy["eta"] = f"{random.randint(20, 60)}m"
                jobs_to_return.append(job_copy)
            
            return {
                "id": random.randint(1, 1000),
                "jobs": jobs_to_return,
                "timestamp": datetime.now().isoformat(),
                "metric": "active_jobs",
                "total_jobs": len(mock_jobs),
                "showing_jobs": len(jobs_to_return)
            }
        
        elif metric_type == "redis_mem":
            # Random Redis memory usage with breakdown
            total_mem = random.uniform(1.2, 4.8)
            used_mem = total_mem * random.uniform(0.4, 0.8)
            return {
                "id": random.randint(1, 1000),
                "value": round(total_mem, 1),
                "timestamp": datetime.now().isoformat(),
                "metric": "redis_memory_gb",
                "used_gb": round(used_mem, 1),
                "free_gb": round(total_mem - used_mem, 1),
                "cache_hit_rate": round(random.uniform(85, 99), 1)
            }
        
        elif metric_type == "minio_bw":
            # Random MinIO bandwidth with direction
            upload_bw = random.uniform(20, 150)
            download_bw = random.uniform(30, 200)
            total_bw = upload_bw + download_bw
            return {
                "id": random.randint(1, 1000),
                "value": round(total_bw, 0),
                "timestamp": datetime.now().isoformat(),
                "metric": "minio_bandwidth_mbps",
                "upload_mbps": round(upload_bw, 0),
                "download_mbps": round(download_bw, 0),
                "connections": random.randint(5, 25)
            }
        
        elif metric_type == "eta":
            # Random ETA with job breakdown
            total_jobs = random.randint(1, 8)
            completed_jobs = random.randint(0, max(0, total_jobs - 2))
            remaining_jobs = total_jobs - completed_jobs
            avg_eta_per_job = random.randint(5, 25)
            total_eta = remaining_jobs * avg_eta_per_job
            
            return {
                "id": random.randint(1, 1000),
                "value": f"{total_eta}m",
                "timestamp": datetime.now().isoformat(),
                "metric": "estimated_completion",
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "remaining_jobs": remaining_jobs,
                "avg_eta_minutes": avg_eta_per_job
            }
    
    # Default response for generic POST requests
    return {
        "id": random.randint(1, 1000),
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "message": "Request processed successfully",
        "request_id": f"req_{random.randint(10000, 99999)}"
    }

@app.post("/upload")
async def upload_data(file: UploadFile = File(...), user_id: Optional[str] = None):
    """Handle data upload for training"""
    
    # Simulate file processing
    content = await file.read()
    file_size = len(content)
    
    # Mock response
    return {
        "id": random.randint(1, 1000),
        "filename": file.filename,
        "size": file_size,
        "type": file.content_type,
        "user_id": user_id,
        "upload_time": datetime.now().isoformat(),
        "status": "uploaded",
        "message": f"File {file.filename} uploaded successfully"
    }

@app.post("/launch-training")
async def launch_training(job_request: TrainingJobRequest):
    """Launch a new training job"""
    
    job_id = f"job_{random.randint(1000, 9999)}"
    
    # Create new job entry
    new_job = {
        "id": job_id,
        "name": f"yolov8_training_{job_id}",
        "status": "queued",
        "progress": 0,
        "eta": "Processing...",
        "user_id": job_request.user_id,
        "project_id": job_request.project_id,
        "config": job_request.config,
        "created_at": datetime.now().isoformat()
    }
    
    # Add to mock jobs
    mock_jobs.insert(0, new_job)
    
    return {
        "id": random.randint(1, 1000),
        "job_id": job_id,
        "status": "queued",
        "message": f"Training job {job_id} launched successfully",
        "timestamp": datetime.now().isoformat(),
        "job": new_job
    }

@app.get("/jobs")
async def get_jobs():
    """Get all training jobs"""
    return {
        "jobs": mock_jobs,
        "total": len(mock_jobs),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get specific job details"""
    job = next((job for job in mock_jobs if job["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Service UI endpoints
@app.get("/mlflow")
async def get_mlflow():
    """MLflow Tracking UI redirect"""
    return {
        "message": "MLflow Tracking Service",
        "service": "MLflow",
        "description": "Experiment logging, metrics, and artifact storage",
        "status": "active",
        "experiments_count": random.randint(15, 45),
        "active_runs": random.randint(3, 12),
        "total_artifacts": random.randint(250, 1200),
        "ui_url": "http://mlflow:5000",
        "api_url": "http://mlflow:5000/api/2.0/mlflow"
    }

@app.get("/redis")
async def get_redis():
    """Redis Queue Monitor"""
    return {
        "message": "Redis Queue Management",
        "service": "Redis",
        "description": "Job orchestration and task scheduling status",
        "status": "active",
        "connected_clients": random.randint(5, 25),
        "memory_usage": f"{random.uniform(1.2, 4.8):.1f} GB",
        "queue_depth": random.randint(3, 18),
        "processing_rate": f"{random.uniform(10, 50):.1f} jobs/sec",
        "ui_url": "http://redis-commander:8081",
        "monitoring_url": "http://redis-insight:8001"
    }

@app.get("/filebrowser")
async def get_filebrowser():
    """File Browser for Datasets"""
    return {
        "message": "Dataset File Browser",
        "service": "MinIO File Browser",
        "description": "File Browser for Training Data management",
        "status": "active",
        "total_datasets": random.randint(8, 25),
        "total_size_gb": random.randint(150, 800),
        "recent_uploads": random.randint(1, 8),
        "active_downloads": random.randint(0, 5),
        "ui_url": "http://minio-console:9001",
        "api_url": "http://minio:9000"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "NeuroForge AI Backend API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/posts - Generic POST endpoint for metrics",
            "/upload - File upload endpoint",
            "/launch-training - Launch training jobs",
            "/jobs - Get all jobs",
            "/jobs/{job_id} - Get specific job",
            "/health - Health check",
            "/mlflow - MLflow Tracking UI",
            "/redis - Redis Queue Monitor",
            "/filebrowser - File Browser for Datasets"
        ]
    }



if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)