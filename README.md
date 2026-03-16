# Control Server - API Gateway + Gradio Interface

Este componente es el **punto de entrada** del cluster NeuralForgeAI. Proporciona una API REST y una interfaz Gradio para que los usuarios puedan lanzar estudios de entrenamiento de modelos YOLO con optimización de hiperparámetros.

---

## 1. 🚶 Diagram Walkthrough

```mermaid
flowchart TD
    subgraph "Usuario"
        U1[Interfaz Gradio]
        U2[API REST Client]
    end

    subgraph "Control Server"
        API[FastAPI Gateway]
        CELERY[Celery Client]
    end

    subgraph "Redis Broker"
        Q_MGR[Cola: managers]
    end

    U1 -->|1. Sube YAML| API
    U2 -->|1. POST /train| API
    API -->|2. Valida config| API
    API -->|3. Mapea prioridad| API
    API -->|4. Envia task| CELERY
    CELERY -->|5. tasks.manage_study| Q_MGR
    
    API -->|6. Retorna study_id| U1
    API -->|7. Retorna study_id| U2
```

**Flujo Principal:**
1. Usuario sube archivo YAML (vía Gradio o API)
2. FastAPI valida el YAML y extrae parámetros
3. Mapea prioridad/worker a cola destino
4. Envía tarea a la cola `managers`
5. Retorna Study ID para seguimiento

---

## 2. 🗺️ System Workflow

```mermaid
sequenceDiagram
    participant U as Usuario
    participant API as FastAPI
    participant C as Celery Client
    participant R as Redis
    participant M as Manager
    participant W as Worker

    U->>API: POST /train (config.yaml, mode, priority)
    
    rect rgb(200, 255, 200)
        note over API: Validación
        API->>API: Valida YAML
        alt mode == private
            API->>API: Verifica worker_name
        else
            API->>API: Mapea priority a cola
        end
    end
    
    API->>C: send_task(tasks.manage_study)
    C->>R: Publica en cola managers
    R->>M: Consume task
    
    API->>U: {study_id, status: Queued}
    
    rect rgb(255, 240, 200)
        note over M,W: Ejecución del estudio (background)
    end
    
    loop Monitoreo
        U->>API: GET /status/{study_id}
        API->>R: Consulta estado Celery
        R-->>API: Estado del task
        API->>U: {state, result}
    end
```

---

## 3. 🏗️ Architecture Components

```mermaid
graph TB
    subgraph "Capa de Presentación"
        G[Gradio Interface<br/>:7860]
    end

    subgraph "Capa API"
        F[FastAPI<br/>:8000]
        E[Endpoints<br/>train, status, workers]
    end

    subgraph "Capa de Orquestación"
        CC[Celery Client]
        CF[Celery Config]
    end

    subgraph "Infraestructura Externa"
        R[(Redis<br/>Broker)]
        P[(PostgreSQL<br/>Optuna DB)]
    end

    G --> F
    E --> F
    F --> CC
    CC --> R
    R --> CF
```

### Componentes Clave

| Componente | Descripción |
|------------|-------------|
| **FastAPI** | Servidor HTTP con endpoints REST |
| **Gradio Interface** | UI visual para lanzar estudios |
| **Celery Client** | Envía tareas al broker Redis |
| **Celery Config** | Configuración de colas y rutas |

---

## 4. ⚙️ Container Lifecycle

### Build Process

1. **Base Image**: Selecciona imagen Python base
2. **Dependencies**: Instala FastAPI, Celery, Redis, PyYAML
3. **Code Copy**: Copia código de `api/` e `interfaz/`
4. **Port Exposure**: Expone puertos 8000 (API) y 7860 (Gradio)
5. **Entrypoint**: Configura comando de inicio

### Runtime Process

1. **Redis Connection**: Conecta al broker Redis configurado
2. **Celery App**: Inicializa aplicación Celery
3. **FastAPI Start**: Inicia servidor en puerto 8000
4. **Gradio Start**: Inicia interfaz en puerto 7860
5. **Health Check**: Endpoints disponibles para consumo

---

## 5. 📂 File-by-File Guide

| Archivo/Carpeta | Propósito |
|-----------------|-----------|
| `api/main.py` | FastAPI app con endpoints REST |
| `api/celery_config.py` | Configuración de Celery (colas, rutas) |
| `api/__init__.py` | Inicialización del módulo API |
| `interfaz/app.py` | Aplicación Gradio para UI visual |
| `interfaz/requirements.txt` | Dependencias de la interfaz |
| `environment/` | Docker Compose de infraestructura |
| `docker-compose.yml` | Orquestación principal |
| `flow.md` | Diagrama del flujo del sistema |
| `PROJECT_SUMMARY.md` | Documentación del proyecto completo |

---

## Uso

### Iniciar el servidor

```bash
docker-compose up -d
```

### URLs

| Servicio | Puerto |
|----------|--------|
| API FastAPI | 8000 |
| Gradio UI | 7860 |

### Endpoints Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/train` | POST | Lanzar estudio |
| `/workers` | GET | Listar workers activos |
| `/status/{study_id}` | GET | Consultar estado |
| `/tasks` | GET | Listar tareas |
| `/tasks/{id}` | DELETE | Revocar tarea |

### Ejemplo de uso

```python
import requests

files = {'config_file': open('config_train.yaml', 'rb')}
data = {'mode': 'public', 'priority': 'high'}

response = requests.post("http://localhost:8000/train", files=files, data=data)
print(response.json())  # {"status": "Queued", "study_id": "..."}
```

---

## Configuración

```yaml
environment:
  - REDIS_URL=redis://192.168.10.252:23437/0
  - OPTUNA_DB_URL=postgresql://postgres:postgres@192.168.10.252:23436/wyoloservice
```

---

**William R.** - AI Leader & Solutions Architect
