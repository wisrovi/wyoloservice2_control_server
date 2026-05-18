# NeuralForgeAI Control Server - WDarwin Ops

## Descripción General

El **Control Server** es el núcleo de orquestación del cluster de entrenamiento ML de NeuralForgeAI. Este componente actúa como **API Gateway** y **punto de entrada** para lanzar estudios de optimización de hiperparámetros usando Optuna sobre modelos YOLO distribuidos en múltiples GPUs.

El sistema permite a los usuarios:
- Lanzar estudios de entrenamiento mediante archivos de configuración YAML
- Optimizar hiperparámetros automáticamente con Optuna TPE Sampler
- Gestionar workers GPU y colas de prioridad
- Monitorear el progreso de estudios en tiempo real
- Rastrear experimentos con MLflow

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAPA DE INTERFAZ (USUARIO)                        │
│                                                                              │
│  ┌──────────────────────┐              ┌────────────────────────────────┐  │
│  │   NeuralForgeAI      │              │         Gradio Interface      │  │
│  │   (React Frontend)   │              │         (Puerto 7860)          │  │
│  │   (Puerto 5810)      │              │                               │  │
│  └──────────┬──────────┘              └───────────────┬────────────────┘  │
└──────────────┼───────────────────────────────────────────┼──────────────────┘
               │              HTTP REST API                 │
               └─────────────────────┬─────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTROL SERVER LAYER (Puerto 8000)                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Application                           │   │
│  │                                                                       │   │
│  │  POST /train          → Valida YAML → Envia a Celery cola managers  │   │
│  │  GET  /status/{id}    → Consulta estado del estudio en Optuna       │   │
│  │  GET  /workers        → Lista GPU workers activos con sus colas      │   │
│  │  GET  /tasks          → Lista todas las tareas en cola Redis         │   │
│  │  DELETE /tasks/{id}   → Revoca tarea pendiente en Celery            │   │
│  │  POST /tasks/{id}/requeue → Re-encola con prioridad diferente      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Celery + Redis Message Broker                      │   │
│  │                                                                       │   │
│  │  Colas disponibles:                                                   │   │
│  │  ┌─────────────┬─────────────────────────────────────────────────┐   │   │
│  │  │ managers   │ Orquestación de estudios Optuna                 │   │   │
│  │  ├─────────────┼─────────────────────────────────────────────────┤   │   │
│  │  │ gpus_high  │ Trials de alta prioridad                        │   │   │
│  │  ├─────────────┼─────────────────────────────────────────────────┤   │   │
│  │  │ gpus_medium│ Trials de prioridad media                        │   │   │
│  │  ├─────────────┼─────────────────────────────────────────────────┤   │   │
│  │  │ gpus_low   │ Trials de baja prioridad                         │   │   │
│  │  ├─────────────┼─────────────────────────────────────────────────┤   │   │
│  │  │ gpus       │ Cola general para cualquier trial               │   │   │
│  │  └─────────────┴─────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│    Manager      │     │    GPU Worker 1     │     │    GPU Worker N     │
│   (managers)   │     │   (gpus_high)       │     │    (gpus_low)       │
│                 │     │                     │     │                     │
│ - Optuna Study │     │ - YOLO training     │     │ - YOLO training     │
│ - Trial sched  │     │ - PyTorch + CUDA   │     │ - PyTorch + CUDA   │
│ - Search space │     │ - Model evaluation  │     │ - Model evaluation  │
│ - OOM fallback │     │ - Metrics report    │     │ - Metrics report    │
└────────┬────────┘     └─────────────────────┘     └─────────────────────┘
         │
         ├──────────────────────────────────────┐
         ▼                                      ▼
┌─────────────────┐               ┌─────────────────────────┐
│  PostgreSQL     │               │       MLflow           │
│  (Optuna DB)    │               │    (Tracking)         │
│                 │               │                       │
│ - Studies       │               │ - Experiments         │
│ - Trials        │               │ - Metrics curves      │
│ - Best params   │               │ - Model artifacts     │
│ - Trial states  │               │ - Training logs       │
└─────────────────┘               └─────────────────────────┘
```

---

## Estructura de Archivos

```
wyoloservice2_control_server/
│
├── api/                                    # FastAPI REST API
│   ├── main.py                            # Endpoints y lógica de la API
│   ├── celery_config.py                   # Configuración de Celery y rutas de tareas
│   ├── tasks.py                           # Definición de tareas Celery
│   ├── requirements.txt                   # Dependencias Python
│   ├── Dockerfile                         # Imagen Docker de la API
│   └── README.md                         # Documentación de la API
│
├── interfaz/                               # Interfaz Gradio alternativa
│   ├── app.py                            # Aplicación Gradio con UI visual
│   └── requirements.txt                   # Dependencias Gradio
│
├── dataset/                               # Dataset de ejemplo
│   └── datasets/
│       └── clasification/
│           └── colorball.v8i.multiclass/  # Dataset de clasificación de bolas
│               ├── config_train.yaml      # Configuración de entrenamiento
│               ├── emulate.request.py     # Script para emular requests
│               ├── README.dataset.txt     # Información del dataset
│               ├── README.roboflow.txt   # Detalles de exportación Roboflow
│               ├── report/train/         # Resultados del entrenamiento
│               │   ├── args.yaml
│               │   ├── confusion_matrix.png
│               │   ├── results.csv
│               │   ├── weights/
│               │   │   ├── best.pt       # Mejores pesos
│               │   │   └── last.pt       # Último checkpoint
│               │   └── training_summary.txt
│               ├── train/                 # Imágenes de entrenamiento
│               │   ├── blue/
│               │   ├── green/
│               │   └── red/
│               └── test/                  # Imágenes de prueba
│                   ├── blue/
│                   ├── green/
│                   └── red/
│
├── tests/                                 # Pruebas unitarias
│   ├── test_api.py                       # Tests de endpoints API
│   ├── test_tasks.py                     # Tests de tareas Celery
│   └── __init__.py
│
├── 00_config_train_example/              # Plantilla de configuración
│   └── config_train.yaml                # YAML ejemplo completo
│
├── docker-compose.yml                    # Orquestación Docker principal
├── Dockerfile                            # Dockerfile principal
├── .env.example                         # Variables de entorno ejemplo
└── PROJECT_SUMMARY.md                    # Este archivo
```

---

## El Archivo de Configuración: `config_train.yaml`

El archivo `config_train.yaml` es el **corazón del sistema**. Define todos los parámetros para un estudio de entrenamiento.

### Estructura Completa

```yaml
# ============================================================
# 1. CONFIGURACIÓN DE INFRAESTRUCTURA
# ============================================================
debug: "192.168.1.84"       # IP del servidor de debugging/monitoring
type: "yolo"                # Tipo de modelo (yolo, classification, detection)

# ============================================================
# 2. CONFIGURACIÓN BASE DE ENTRENAMIENTO
# ============================================================
train:
  # Datos
  data: /dataset/           # Ruta al dataset mountado en el worker
  
  # Recursos
  batch: 0.85              # Fracción de VRAM a usar (85%)
  device: 0                # ID de GPU (0, 1, 2... o 'cpu')
  workers: 8               # Workers de dataloader
  
  # Parámetros de entrenamiento
  epochs: 250              # Número máximo de épocas
  imgsz: 640               # Tamaño de imagen (pixels)
  
  # Optimizador
  lr0: 0.01                # Learning rate inicial
  lrf: 0.01                # Learning rate final (al final del cosine)
  
  # Regularización
  dropout: 0.0             # Dropout rate (0.0-1.0)
  erasing: 0.0             # Random erasing rate
  weight_decay: 0.0005     # Weight decay del optimizador
  
  # Learning rate schedule
  cos_lr: true             # Usar cosine annealing del LR
  
  # Data augmentation
  mixup: 0.0               # MixUp augmentation
  cache: true              # Cache imágenes en RAM para velocidad

# ============================================================
# 3. CONFIGURACIÓN DEL SWEEPER (OPTUNA)
# ============================================================
sweeper:
  version: 1                                        # Versión del schema
  study_name: "MiExperimento_Clasificacion"        # Nombre único del estudio
  direction: maximize                               # maximize o minimize
  fitness: "metrics/accuracy_top1"                 # Métrica a optimizar
  
  # Configuración de optimización
  n_trials: 15                                     # Número de trials a ejecutar
  sampler: "TPESampler"                            # Algoritmo: TPE (bayesiano)
  algorithm: optuna                                 # Motor de optimización
  n_startup_trials: 5                              # Trials aleatorios antes de TPE
  
  # Distribución
  distributed: true                                # Habilitar distribución
  gpus_per_trial: 1                                # GPUs por trial
  cpus_per_trial: 4                                # CPUs por trial
  
  # Espacio de búsqueda (Hiperparámetros a optimizar)
  search_space:
    # MODELO: Elegir entre varios
    model:
      - "choice"
      - "yolov8n-cls.pt"    # Nano (más rápido, menos preciso)
      - "yolov8s-cls.pt"    # Small
      - "yolo11n-cls.pt"    # YOLO11 Nano
      - "yolo11s-cls.pt"    # YOLO11 Small
    
    # HIPERPARÁMETROS: Se prueban combinaciones
    train:
      # Imagen: elegir de opciones
      imgsz:
        - "choice"
        - 480
        - 640
        - 800
      
      # Epochs: elegir de opciones
      epochs:
        - "choice"
        - 100
        - 150
        - 200
        - 300
      
      # Learning rate inicial: distribución log-uniform
      lr0:
        - "loguniform"
        - 0.0001      # 1e-4
        - 0.01        # 1e-2
      
      # Learning rate final
      lrf:
        - "choice"
        - 0.01
        - 0.05
        - 0.1
        - 0.2
      
      # Weight decay: distribución log-uniform
      weight_decay:
        - "loguniform"
        - 0.00001     # 1e-5
        - 0.001       # 1e-3
      
      # Dropout
      dropout:
        - "choice"
        - 0.0
        - 0.1
        - 0.25
        - 0.5
      
      # MixUp augmentation
      mixup:
        - "choice"
        - 0.0
        - 0.1
        - 0.2
      
      # Cosine LR
      cos_lr:
        - "choice"
        - true
        - false

# ============================================================
# 4. FALLBACKS OOM (Out Of Memory)
# ============================================================
# Si el entrenamiento falla por falta de memoria VRAM,
# el sistema aplica overrides en orden hasta que funcione
fallback_overrides:
  - {}                                    # Intento 1: Configuración original
  - { workers: 4 }                        # Intento 2: Menos workers
  - { workers: 2, batch: 0.35 }          # Intento 3: Menos workers + batch menor
  - { workers: 0, batch: 0.30, cache: false }  # Intento 4: Modo minimal

# ============================================================
# 5. CONFIGURACIÓN DE VALIDACIÓN
# ============================================================
val:
  data: /dataset/
  device: 0
  imgsz: 640
  split: test              # split a usar (train, val, test)
  workers: 4

# ============================================================
# 6. LIMITACIÓN DE RECURSOS GPU
# ============================================================
extras:
  gpu:
    id: 0                  # GPU específica
    limit: 0.60           # Límite de VRAM (60%)
  
  # Montaje de volúmenes
  volumes:
    dataset: /dataset
    output: /output

# ============================================================
# 7. METADATOS DEL EXPERIMENTO
# ============================================================
metadata:
  content: "Clasificación de pelotas de colores"
  author: "William Rodriguez"
  organization: "WDarwin Ops"
  documentation: |
    Este experimento entrena un clasificador YOLO para
    identificar pelotas de colores (azul, verde, rojo).
    
    El objetivo es maximizar la accuracy top-1.
```

### Parámetros de Búsqueda Soportados

| Tipo | Sintaxis YAML | Descripción |
|------|---------------|-------------|
| `choice` | `["choice", val1, val2, val3]` | Selecciona una opción discretamente |
| `uniform` | `["uniform", min, max]` | Distribución uniforme continua |
| `loguniform` | `["loguniform", min, max]` | Distribución log-uniform (para LR, weight_decay) |
| `int` | `["int", min, max]` | Entero en rango |
| `categorical` | `["categorical", "a", "b", "c"]` | Equivalente a choice |

---

## Flujo de Comunicación Completo

### Paso 1: Usuario Prepara Configuración

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO                                                     │
│                                                              │
│  1. Copia config_train.yaml desde 00_config_train_example/  │
│  2. Modifica según necesidad:                                │
│     - study_name: "MiExperimento_v1"                        │
│     - n_trials: 20                                          │
│     - search_space: modelos, lr, epochs, etc.               │
│     - dataset path: /dataset/                               │
│  3. Sube archivo YAML por:                                  │
│     - NeuralForgeAI (React) Puerto 5810                     │
│     - Gradio UI Puerto 7860                                  │
│     - Directamente a API Puerto 8000                        │
└─────────────────────────────────────────────────────────────┘
```

### Paso 2: Validación y Envío a Celery

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (Gradio o React)                                  │
│                                                              │
│  Valida estructura YAML:                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ✓ Debe existir bloque: train                         │  │
│  │ ✓ Debe existir bloque: sweeper                       │  │
│  │ ✓ train.data debe estar presente                     │  │
│  │ ✓ sweeper.study_name debe existir                    │  │
│  │ ✓ sweeper.n_trials > 0                               │  │
│  │ ✓ search_space debe tener al menos 1 parámetro       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  POST http://neuroforge-api:8000/train                      │
│  Content-Type: multipart/form-data                           │
│  Fields:                                                     │
│    - config_file: <YAML file>                               │
│    - mode: "public" | "private"                             │
│    - priority: "high" | "medium" | "low"                    │
│    - worker_name: "gpu_node_01" (si mode=private)           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  FASTAPI (:8000)                                            │
│                                                              │
│  1. Recebe archivo YAML                                     │
│  2. Parsea y valida con Pydantic                            │
│  3. Extrae study_name y n_trials                            │
│  4. Crea task_id único                                       │
│  5. Llama celery_app.send_task():                           │
│                                                              │
│     ┌─────────────────────────────────────────────────────┐ │
│     │ celery_app.send_task(                               │ │
│     │     'tasks.manage_study',                           │ │
│     │     args=[yaml_content, task_id, mode, priority],  │ │
│     │     queue='managers',                               │ │
│     │     priority=priority_num                          │ │
│     │ )                                                   │ │
│     └─────────────────────────────────────────────────────┘ │
│                                                              │
│  6. Retorna:                                                │
│     {                                                        │
│       "study_id": "task_abc123",                           │
│       "status": "queued",                                  │
│       "message": "Study queued to managers"                 │
│     }                                                        │
└─────────────────────────────────────────────────────────────┘
```

### Paso 3: Manager Crea Estudio Optuna

```
┌─────────────────────────────────────────────────────────────┐
│  CELERY WORKER: Manager (cola managers)                     │
│                                                              │
│  Task: tasks.manage_study(yaml_content, task_id)            │
│                                                              │
│  1. Parsear search_space del YAML                           │
│  2. Crear Optuna Study:                                     │
│                                                              │
│     ┌─────────────────────────────────────────────────────┐ │
│     │ import optuna                                        │ │
│     │                                                        │ │
│     │ storage = "postgresql://..."  # OPTUNA_DB_URL        │ │
│     │ sampler = optuna.samplers.TPESampler(               │ │
│     │     n_startup_trials=5                              │ │
│     │ )                                                    │ │
│     │                                                        │ │
│     │ study = optuna.create_study(                         │ │
│     │     study_name="MiExperimento_v1",                  │ │
│     │     direction="maximize",                           │ │
│     │     storage=storage,                                 │ │
│     │     sampler=sampler,                                 │ │
│     │     load_if_exists=True                              │ │
│     │ )                                                    │ │
│     └─────────────────────────────────────────────────────┘ │
│                                                              │
│  3. Para cada trial (1..n_trials):                          │
│     a. Suggest hyperparameters del search_space             │
│     b. Enviar a cola GPU:                                   │
│        send_task('tasks.train_on_gpu',                      │
│                   args=[trial_params, trial_number])        │
│                                                              │
│  4. Monitorear completion de trials                         │
│  5. Reportar mejores hiperparámetros                        │
└─────────────────────────────────────────────────────────────┘
```

### Paso 4: GPU Workers Entrenan Modelos

```
┌─────────────────────────────────────────────────────────────┐
│  CELERY WORKER: GPU Worker (cola gpus)                     │
│                                                              │
│  Task: tasks.train_on_gpu(trial_params, trial_number)      │
│                                                              │
│  1. Recibir hiperparámetros del trial:                      │
│     {                                                       │
│       "model": "yolo11s-cls.pt",                           │
│       "imgsz": 640,                                        │
│       "epochs": 200,                                       │
│       "lr0": 0.001,                                       │
│       "dropout": 0.1,                                      │
│       "batch": 0.85                                        │
│     }                                                       │
│                                                              │
│  2. Configurar GPU:                                        │
│     - torch.cuda.set_device(gpu_id)                        │
│     - set CUDA_VISIBLE_DEVICES=gpu_id                      │
│                                                              │
│  3. Entrenar modelo YOLO:                                  │
│     from ultralytics import YOLO                            │
│     model = YOLO(trial_params['model'])                    │
│     results = model.train(                                  │
│         data='/dataset/',                                  │
│         epochs=trial_params['epochs'],                     │
│         imgsz=trial_params['imgsz'],                       │
│         lr0=trial_params['lr0'],                           │
│         dropout=trial_params['dropout'],                   │
│         batch=trial_params['batch'],                       │
│         device=0,                                          │
│         project='/output/',                                │
│         name=f'trial_{trial_number}'                       │
│     )                                                       │
│                                                              │
│  4. Extraer métricas:                                       │
│     - accuracy_top1: results.results['accuracy_top1']      │
│     - accuracy_top5: results.results['accuracy_top5']      │
│                                                              │
│  5. Reportar a Optuna:                                      │
│     study.tell(trial_number, accuracy_top1)                │
│                                                              │
│  6. Reportar a MLflow:                                      │
│     mlflow.log_metrics({                                   │
│         'accuracy_top1': accuracy_top1,                    │
│         'accuracy_top5': accuracy_top5                     │
│     })                                                      │
│     mlflow.log_params(trial_params)                        │
│                                                              │
│  7. Guardar artifact:                                       │
│     mlflow.log_artifact('runs/trial_X/weights/best.pt')   │
└─────────────────────────────────────────────────────────────┘
```

### Paso 5: Usuario Consulta Resultados

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO                                                     │
│                                                              │
│  GET http://neuroforge-api:8000/status/{study_id}           │
│                                                              │
│  Respuesta:                                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ {                                                      │  │
│  │   "study_name": "MiExperimento_v1",                   │  │
│  │   "state": "COMPLETED",                               │  │
│  │   "n_trials": 15,                                    │  │
│  │   "best_trial": 12,                                  │  │
│  │   "best_value": 0.9432,                              │  │
│  │   "best_params": {                                   │  │
│  │     "model": "yolo11s-cls.pt",                       │  │
│  │     "imgsz": 640,                                    │  │
│  │     "epochs": 200,                                   │  │
│  │     "lr0": 0.0008                                   │  │
│  │   },                                                 │  │
│  │   "mlflow_run_id": "abc123...",                      │  │
│  │   "artifacts": [                                     │  │
│  │     "/output/MiExperimento_v1/weights/best.pt"       │  │
│  │   ]                                                   │  │
│  │ }                                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  O acceder a MLflow UI:                                     │
│  http://192.168.1.84:23435                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Endpoints API Detallados

### POST `/train` - Lanzar Estudio

**Request:**
```bash
curl -X POST "http://localhost:8000/train" \
  -F "config_file=@config_train.yaml" \
  -F "mode=public" \
  -F "priority=high"
```

**Response:**
```json
{
  "study_id": "task_1699876543_abc123",
  "status": "queued",
  "message": "Study 'MiExperimento_v1' queued successfully",
  "n_trials": 15,
  "estimated_time": "2-4 hours"
}
```

### GET `/status/{study_id}` - Consultar Estado

**Response:**
```json
{
  "study_id": "task_1699876543_abc123",
  "study_name": "MiExperimento_v1",
  "state": "RUNNING",
  "progress": {
    "trials_completed": 8,
    "trials_total": 15,
    "percentage": 53
  },
  "best_trial": {
    "number": 7,
    "value": 0.9215,
    "params": {
      "model": "yolov8s-cls.pt",
      "imgsz": 640,
      "epochs": 200
    }
  },
  "mlflow_tracking_uri": "http://192.168.1.84:23435"
}
```

### GET `/workers` - Listar Workers

**Response:**
```json
{
  "workers": [
    {
      "name": "gpu_node_01",
      "status": "active",
      "queue": "gpus_high",
      "current_task": "trial_5",
      "gpu_utilization": 87,
      "gpu_memory_used": "4.2GB/8GB"
    },
    {
      "name": "gpu_node_02",
      "status": "active",
      "queue": "gpus_low",
      "current_task": "idle",
      "gpu_utilization": 0,
      "gpu_memory_used": "0GB/8GB"
    }
  ]
}
```

### GET `/tasks` - Listar Tareas

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "abc123",
      "name": "tasks.manage_study",
      "state": "STARTED",
      "queue": "managers",
      "eta": null,
      "worker": "manager_node_01"
    },
    {
      "task_id": "def456",
      "name": "tasks.train_on_gpu",
      "state": "PENDING",
      "queue": "gpus_high",
      "eta": null,
      "worker": null
    }
  ]
}
```

### DELETE `/tasks/{task_id}` - Revocar Tarea

**Response:**
```json
{
  "task_id": "def456",
  "status": "revoked",
  "message": "Task has been revoked"
}
```

### POST `/tasks/{task_id}/requeue` - Recolar Tarea

**Request:**
```json
{
  "priority": "low",
  "queue": "gpus_low"
}
```

**Response:**
```json
{
  "task_id": "def456",
  "status": "requeued",
  "new_queue": "gpus_low",
  "new_priority": 5
}
```

---

## Sistema de Colas y Prioridades

### Colas Disponibles en Celery

| Cola | Propósito | Prioridad |
|------|-----------|-----------|
| `managers` | Tareas de orquestación Optuna | Alta |
| `gpus_high` | Trials de alta prioridad | 9-10 |
| `gpus_medium` | Trials de prioridad media | 5-6 |
| `gpus_low` | Trials de baja prioridad | 1-2 |
| `gpus` | Cola general/de fallback | Variable |

### Routing de Tareas

```python
# celery_config.py
task_routes = {
    'tasks.manage_study': {'queue': 'managers'},
    'tasks.train_on_gpu': {'queue': 'gpus'},
}
```

### Modos de Dispatch

#### Modo Público (Default)
```yaml
mode: "public"
priority: "high"  # gpus_high
# o "medium" -> gpus_medium
# o "low" -> gpus_low
```

#### Modo Privado
```yaml
mode: "private"
worker_name: "gpu_node_01"  # Cola privada del worker
```

---

## Variables de Entorno

### Configuración de Infraestructura

```bash
# Redis (Message Broker)
REDIS_URL=redis://192.168.10.252:23437/0

# PostgreSQL (Optuna Storage)
OPTUNA_DB_URL=postgresql://postgres:postgres@192.168.10.252:23436/wyoloservice

# MLflow (Experiment Tracking)
MLFLOW_TRACKING_URI=http://192.168.1.84:23435

# Identificación del Worker (para modo privado)
WORKER_NAME=gpu_node_01
PRIVATE_QUEUE=worker_gpu1

# File Browser (visualización de archivos)
FILEBROWSER_URL=http://192.168.1.84:23443/files/
```

### Puertos de Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| FastAPI (Control Server) | 8000 | API REST principal |
| Gradio UI | 7860 | Interfaz visual alternativa |
| Redis | 6379 | Message broker |
| PostgreSQL | 5432 | Optuna study database |
| MLflow | 23435 | Experiment tracking |
| File Browser | 23443 | Explorador de archivos |
| MinIO | 9000 | Object storage |

---

## Dependencias

### Python (api/requirements.txt)

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
celery>=5.3.0
redis>=5.0.0
PyYAML>=6.0
pydantic>=2.0.0
python-multipart>=0.0.6
httpx>=0.25.0
optuna>=3.4.0
mlflow>=2.8.0
```

### Docker Images Registradas

| Componente | Imagen Docker | Propósito |
|------------|---------------|-----------|
| Control Server | `wisrovi/train_service:control_server_v1.0.0` | FastAPI + Gradio |
| Manager | `wisrovi/train_service/manager:orchestrator_v1.0.0` | Optuna orchestrator |
| Worker Invoker | `wisrovi/train_service:worker_invoker_v1.0.0` | Docker container manager |
| Worker Executor | `wisrovi/train_service:worker_executor_v1.0.0` | YOLO training |
| Frontend | `wisrovi/neuralforgeai:v1.0.0` | React UI |

---

## Ejemplos de Uso

### 1. Lanzar Estudio por API Python

```python
import requests

# Preparar archivo de configuración
files = {'config_file': open('config_train.yaml', 'rb')}
data = {
    'mode': 'public',
    'priority': 'high'
}

# Enviar estudio
response = requests.post(
    "http://localhost:8000/train",
    files=files,
    data=data
)

study_id = response.json()['study_id']
print(f"Study queued: {study_id}")

# Monitorear estado
while True:
    status = requests.get(f"http://localhost:8000/status/{study_id}")
    state = status.json()['state']
    print(f"State: {state}")
    
    if state in ['COMPLETED', 'FAILED']:
        break
    
    import time
    time.sleep(30)
```

### 2. Lanzar Estudio con Cliente Celery

```python
from api.celery_config import celery_app
from api.tasks import manage_study
import yaml

with open('config_train.yaml') as f:
    yaml_content = yaml.safe_load(f)

result = manage_study.apply_async(
    args=[yaml_content, 'my_task_id'],
    queue='managers',
    priority=9
)

print(f"Task ID: {result.id}")
```

### 3. Usar la Interfaz Gradio

```bash
# Abrir en navegador
http://localhost:7860

# Funcionalidades:
# - Dashboard con estadísticas
# - Subir archivo YAML
# - Seleccionar modo (public/private)
# - Seleccionar prioridad
# - Monitorear workers
# - Ver estado de estudios
```

---

## Comandos de Gestión

### Iniciar Servicios con Docker Compose

```bash
# Desde wyoloservice2_control_server/
docker-compose up -d

# Ver logs
docker-compose logs -f api
docker-compose logs -f interfaz
```

### Iniciar Workers Celery

```bash
# Worker Manager
celery -A api.celery_config worker -Q managers --loglevel=info -n manager1

# Worker GPU (alta prioridad)
celery -A api.celery_config worker -Q gpus_high,gpus --loglevel=info -n gpu_high1

# Worker GPU (todas las colas)
celery -A api.celery_config worker -Q gpus_high,gpus_medium,gpus_low,gpus --loglevel=info -n gpu_all1
```

### Monitorear con Flower

```bash
celery -A api.celery_config flower --port=5555

# Abrir http://localhost:5555
```

---

## Solución de Problemas (Troubleshooting)

### Error: "Redis connection refused"

```bash
# Verificar que Redis esté corriendo
docker ps | grep redis

# Probar conexión
redis-cli -h 192.168.10.252 -p 23437 ping
```

### Error: "Optuna study not found"

```bash
# Verificar que PostgreSQL esté corriendo
docker ps | grep postgres

# Conectar a PostgreSQL
psql postgresql://postgres:postgres@192.168.10.252:23436/wyoloservice

# Ver estudios
SELECT study_name, direction, n_trials FROM studies;
```

### GPU Out of Memory

El sistema aplica automáticamente los `fallback_overrides` del YAML:
1. Reduce workers a 4
2. Reduce workers a 2 y batch a 0.35
3. Reduce workers a 0, batch a 0.30, desactiva cache

### Worker no procesa tareas

```bash
# Ver colas disponibles
celery -A api.celery_config inspect active_queues

# Revisar logs del worker
celery -A api.celery_config worker --loglevel=debug
```

---

## Seguridad

### Recomendaciones de Producción

1. **Redis**: Usar password y TLS
   ```bash
   redis://:password@host:6379/0?ssl=true
   ```

2. **PostgreSQL**: Usar password fuerte y conexiones TLS

3. **API**: Implementar autenticación (OAuth2/JWT)

4. **MLflow**: Usar autenticación y TLS

5. **Workers**: Limitar recursos por contenedor
   ```yaml
   resources:
     limits:
       memory: 16G
       devices:
         - driver: nvidia
           count: 1
           capabilities: [gpu]
   ```

---

## Integración con NeuralForgeAI (Frontend)

El Control Server está diseñado para integrarse con el frontend React **NeuralForgeAI**:

```typescript
// NeuralForgeAI/constants.tsx
const API_BASE = getEnv('VITE_API_URL', 'http://localhost:5809');
const UPLOAD_API_BASE = getEnv('VITE_API_URL', 'http://neuroforge-api:8000');

// Endpoints usados
POST ${UPLOAD_API_BASE}/train    // Lanzar estudio
GET  ${UPLOAD_API_BASE}/status/{id}  // Estado
GET  ${UPLOAD_API_BASE}/workers      // Workers
```

### Dashboard de NeuralForgeAI

El frontend muestra:
- **Cluster Telemetry**: Workers activos, uso GPU, cola de tareas
- **Training Launch**: Formulario para subir YAML
- **Status Tracking**: Progreso de estudios en tiempo real
- **Service Viewer**: Iframe para ver microservicios externos

---

## Roadmap y Mejoras Futuras

- [ ] Implementar autenticación OAuth2/JWT en API
- [ ] Soporte para modelos adicionales (YOLOX, Detectron2)
- [ ] Auto-scaling de workers basado en demanda
- [ ] Integración con Kubernetes para orquestación
- [ ] Dashboard de costos de compute
- [ ] Historial de experimentos con comparison tools
- [ ] API de Webhooks para notificaciones

---

## Créditos y Contacto

**Desarrollado por:** William Rodriguez  
**Organización:** WDarwin Ops - AI Leader & Solutions Architect  
**GitHub:** github.com/wisrovi  
**Email:** william@wdarwin.io

**Versión:** 2.0  
**Última actualización:** 2026-03-25

---

## Licencia

MIT License - Ver archivo LICENSE para más detalles.
