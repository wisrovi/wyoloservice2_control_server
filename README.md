# NeuralForge AI - Distributed YOLO Training Cluster

Este proyecto implementa un ecosistema completo para el entrenamiento distribuido y optimización de hiperparámetros de modelos YOLO. Utiliza **Celery** para orquestación, **Optuna** para optimización de hiperparámetros, y un patrón **Invoker-Executor** basado en Docker para garantizar el aislamiento total de los procesos de entrenamiento.

## Arquitectura del Sistema (Escenario Distribuido C)

El sistema utiliza una arquitectura de microservicios desacoplada que se comunica a través de **Redis** como broker de mensajes y **PostgreSQL** como centro de inteligencia centralizado.

---

## Diagramas de Arquitectura

### 1. Arquitectura General del Sistema

```mermaid
graph TD
    subgraph "Capa de Usuario"
        U1[Gradio Interface]
        U2[NeuralForgeAI - React UI]
    end

    subgraph "Infraestructura Central (192.168.10.252)"
        R[(Redis Broker<br/>puerto 23437)]
        PG[(PostgreSQL<br/>puerto 23436)]
        M[(MinIO / MLflow<br/>puerto 23435)]
    end

    subgraph "Servidor API (control_server)"
        API[FastAPI Gateway<br/>puerto 8000]
    end

    subgraph "Nodo Manager"
        MGR[Manager Celery<br/>cola: managers]
    end

    subgraph "Nodo GPU (Worker)"
        INV[Invoker Celery<br/>cola: worker_*, gpus_*]
        DOCKER[Docker Engine]
    end

    U1 -->|HTTP| API
    U2 -->|HTTP| API
    API -->|Celery: tasks.manage_study| R
    R -->|Celery: tasks.manage_study| MGR
    MGR -->|Celery: tasks.train_on_gpu| R
    R -->|Celery: tasks.train_on_gpu| INV
    INV -->|Optuna Query| PG
    INV -->|Docker Run| DOCKER
    DOCKER -->|results.json| INV
    INV -->|Write Results| PG
    MGR -->|Wait & Collect Results| R
    API -->|Check Status| R
    MGR -.->|Optuna Study| PG
```

**Explicación del diagrama:**
- **Capa de Usuario**: Interfaz Gradio simple o NeuralForgeAI (React) para enviar configuraciones
- **Infraestructura Central**: Redis (broker de mensajes), PostgreSQL (base de datos de Optuna), MinIO/MLflow (tracking de experimentos)
- **API Gateway**: FastAPI que recibe archivos YAML y los envía a la cola de managers
- **Manager**: Worker Celery especial que corre estudios Optuna
- **Invoker**: Worker Celery que ejecuta contenedores Docker para entrenar
- **Docker Engine**: Ejecuta el contenedor efímero con el entrenamiento YOLO

---

### 2. Flujo de Datos - Ciclo de Vida de un Estudio

```mermaid
sequenceDiagram
    participant U as Usuario
    participant API as Control Server<br/>(FastAPI)
    participant Q as Redis<br/>(Broker)
    participant M as Manager<br/>(Optuna)
    participant I as Invoker<br/>(Celery Worker)
    participant D as Docker<br/>(Executor)
    participant DB as PostgreSQL<br/>(Optuna DB)
    participant ML as MLflow<br/>(Tracking)

    U->>API: 1. POST /train<br/>(config_train.yaml)
    API->>API: Valida YAML<br/>Inyecta metadata de rutas
    API->>Q: 2. Envia task<br/>tasks.manage_study<br/>(cola: managers)
    
    Q->>M: 3. Consume task<br/>manage_study
    
    rect rgb(200, 255, 200)
        note over M: BUCLE DE OPTUNA<br/>(n_trials veces)
        M->>M: 4. Optuna sugiere<br/>hiperparámetros
        M->>Q: 5. Envia task<br/>tasks.train_on_gpu<br/>(cola: gpus_*)
        
        Q->>I: 6. Consume task<br/>train_on_gpu
        
        I->>DB: 7. Consulta próximo<br/>trial de Optuna
        DB-->>I: 8. Parámetros<br/>del trial
        
        I->>I: 9. Crea config.yaml<br/>en volumen temporal
        I->>D: 10. docker run<br/>(executor container)
        
        rect rgb(255, 240, 200)
            note over D: CONTENEDOR WORKER
            D->>D: 11. Lee config.json<br/>del volumen
            D->>ML: 12. Inicializa<br/>MLflow tracking
            D->>D: 13. Entrena YOLO<br/>(epochs, batch, etc)
            D->>ML: 14. Log metrics<br/>(accuracy, loss)
            D->>D: 15. Guarda<br/>results.json
        end
        
        D-->>I: 16. Contenedor termina<br/>(auto-remove)
        I->>I: 17. Lee accuracy<br/>de results.json
        I->>DB: 18. Guarda resultado<br/>del trial
        I-->>M: 19. Retorna accuracy
        
        note over M: Repite hasta<br/>completar n_trials
    end
    
    M->>API: 20. Retorna<br/>best_params
    API->>U: 21. Respuesta final<br/>(mejores parámetros)
```

**Explicación del flujo:**
1. Usuario envía YAML con configuración de entrenamiento
2. API valida y envía a la cola "managers"
3. Manager inicia estudio Optuna (n_trials)
4. Por cada trial: Manager envía tarea a cola de GPUs
5. Invoker recibe tarea, consulta parámetros en PostgreSQL
6. Invoker crea volumen temporal con config.json
7. Invoker ejecuta contenedor Docker (worker)
8. Worker entrena YOLO y guarda results.json
9. Invoker lee resultado y lo guarda en PostgreSQL
10. Manager repite hasta completar todos los trials
11. Retorna mejores parámetros al usuario

---

### 3. Jerarquía de Colas con Prioridad Estricta

```mermaid
graph TB
    subgraph "Redis Broker"
        subgraph "Cola Managers (1)"
            Q_MGR["managers<br/>(cola de estudios)"]
        end
        
        subgraph "Colas GPU (Prioridad)"
            Q_HIGH["gpus_high<br/>(alta prioridad)"]
            Q_MED["gpus_medium<br/>(media)"]
            Q_LOW["gpus_low<br/>(baja)"]
        end
        
        subgraph "Colas Privadas"
            Q_W1["worker_gpu1<br/>(privada)"]
            Q_W2["worker_gpu2<br/>(privada)"]
            Q_WN["worker_gpun<br/>(privada)"]
        end
    end

    subgraph "Invokers ( Workers GPU)"
        INV1[Invoker GPU1<br/>-Q worker_gpu1,gpus_high,gpus_medium,gpus_low]
        INV2[Invoker GPU2<br/>-Q worker_gpu2,gpus_high,gpus_medium,gpus_low]
    end

    Q_MGR -->|1. Studies| INV1
    Q_MGR -->|2. Studies| INV2
    
    Q_W1 -->|3. Tasks| INV1
    Q_W2 -->|4. Tasks| INV2
    Q_HIGH -->|5. Tasks| INV1
    Q_HIGH -->|6. Tasks| INV2
    Q_MED -->|7. Tasks| INV1
    Q_MED -->|8. Tasks| INV2
    Q_LOW -->|9. Tasks| INV1
    Q_LOW -->|10. Tasks| INV2
```

**Explicación de prioridades:**
- **Cola managers**: Solo para estudios de Optuna (tareas de orquestación)
- **Colas privadas** (`worker_*`): Máxima prioridad - tareas dirigidas a una máquina específica
- **Cola gpus_high**: Alta prioridad - tareas urgentes
- **Cola gpus_medium**: Prioridad media - tareas estándar
- **Cola gpus_low**: Baja prioridad - tareas de relleno/experimentales

Cada Invoker escucha en orden estricto: `private > gpus_high > gpus_medium > gpus_low`

---

### 4. Patrón Invoker-Executor

```mermaid
graph TD
    subgraph "Nodo Worker (Servidor GPU)"
        C[Celery Worker<br/>(Invoker)]
        
        subgraph "Volumen Temporal"
            V["/tmp/trial_XXXXX/"]
            V1["config.json"]
            V2["results.json"]
        end
        
        D[Docker Engine]
        
        subgraph "Contenedor Efímero"
            EX[Executor Container<br/>wisrovi/train_service:worker_executor]
        end
    end

    C -->|1. Crea directorio| V
    C -->|2. Escribe config.json| V1
    C -->|3. docker run| D
    D -->|4. Monta volumen| EX
    EX -->|5. Lee config| V1
    EX -->|6. Entrena YOLO| EX
    EX -->|7. Escribe results| V2
    D -->>|8. Auto-remove| C
    C -->|9. Lee results.json| V2
    C -->|10. Cleanup| V
```

**Explicación del patrón:**
1. Invoker crea directorio temporal en `/tmp`
2. Escribe archivo `config.json` con parámetros de entrenamiento
3. Ejecuta contenedor Docker con el volumen montado
4. Contenedor entrena modelo YOLO
5. Contenedor escribe `results.json` con métricas
6. Contenedor se elimina automáticamente (`auto_remove=True`)
7. Invoker lee resultados y limpia directorio temporal

---

### 5. Arquitectura de Optuna Distribuido

```mermaid
graph LR
    subgraph "Estudio Optuna (PostgreSQL)"
        DB[(PostgreSQL<br/>wyoloservice)]
        
        subgraph "Trials"
            T1[Trial 1<br/>lr=0.01, imgsz=640]
            T2[Trial 2<br/>lr=0.001, imgsz=512]
            T3[Trial 3<br/>lr=0.005, imgsz=480]
            Tn[Trial N<br/>...]
        end
        
        DB --> T1
        DB --> T2
        DB --> T3
        DB --> Tn
    end

    subgraph "Workers"
        W1[Worker 1<br/>GPU 1]
        W2[Worker 2<br/>GPU 2]
        W3[Worker 3<br/>GPU 3]
    end

    T1 -->|Ejecuta| W1
    T2 -->|Ejecuta| W2
    T3 -->|Ejecuta| W3
    
    W1 -->|accuracy=0.85| T1
    W2 -->|accuracy=0.78| T2
    W3 -->|accuracy=0.82| T3
```

**Explicación:**
- PostgreSQL almacena el estudio y todos los trials
- Múltiples workers pueden ejecutar trials en paralelo
- Cada worker consulta el siguiente trial disponible
- Los resultados se escriben directamente en PostgreSQL
- Optuna organiza y busca los mejores parámetros

---

### 6. Configuración de YAML para Entrenamiento

```mermaid
graph TD
    subgraph "config_train.yaml"
        SEC1["debug: IP del servidor"]
        SEC2["model: yolov8n-cls.pt"]
        
        subgraph "train (parámetros base)"
            T1["data: /dataset/"]
            T2["epochs: 250"]
            T3["imgsz: 640"]
            T4["lr0: 0.01"]
        end
        
        subgraph "sweeper (espacio de búsqueda)"
            S1["study_name: 'mi_estudio'"]
            S2["n_trials: 15"]
            S3["direction: maximize"]
            S4["search_space:"]
            SS1["model: [choice, yolov8n, yolo11s]"]
            SS2["train.imgsz: [choice, 480, 640]"]
            SS3["train.lr0: [loguniform, 1e-4, 1e-2]"]
        end
        
        subgraph "metadata"
            M1["author: William R."]
            M2["content: descripción"]
        end
    end
    
    SEC1 --> API
    SEC2 --> API
    T1 --> API
    T2 --> API
    T3 --> API
    T4 --> API
    S1 --> API
    S2 --> API
    S3 --> API
    S4 --> API
    SS1 --> S4
    SS2 --> S4
    SS3 --> S4
    M1 --> API
    M2 --> API
```

**Explicación de secciones:**
- **debug**: Configuración de infraestructura (IP del servidor)
- **model**: Modelo base YOLO a entrenar
- **train**: Parámetros de entrenamiento (pueden ser sobrescritos por sweeper)
- **sweeper**: Configuración de Optuna para optimización de hiperparámetros
- **search_space**: Espacio de búsqueda con tipos (choice, loguniform, uniform, range)
- **metadata**: Información del experimento

---

### 7. Despliegue Multi-Nodo

```mermaid
graph TB
    subgraph "Servidor Central"
        REDIS[(Redis<br/>192.168.10.252:23437)]
        POSTGRES[(PostgreSQL<br/>192.168.10.252:23436)]
        MLFLOW[(MLflow<br/>192.168.10.252:23435)]
    end

    subgraph "Nodo 1: API + Manager"
        API1[FastAPI<br/>:8000]
        MGR[Manager<br/>Celery]
    end

    subgraph "Nodo 2: GPU Worker 1"
        INV1[Invoker<br/>worker_gpu1]
        DOCKER1[Docker]
    end

    subgraph "Nodo 3: GPU Worker 2"
        INV2[Invoker<br/>worker_gpu2]
        DOCKER2[Docker]
    end

    subgraph "Nodo 4: NeuralForgeAI (Frontend)"
        REACT[React App<br/>:3000]
    end

    REACT -->|HTTP| API1
    API1 -->|Celery| REDIS
    REDIS -->|Celery| MGR
    REDIS -->|Celery| INV1
    REDIS -->|Celery| INV2
    MGR -->|SQL| POSTGRES
    INV1 -->|SQL| POSTGRES
    INV2 -->|SQL| POSTGRES
    INV1 -->|Docker| DOCKER1
    INV2 -->|Docker| DOCKER2
    INV1 -->|MLflow| MLFLOW
    INV2 -->|MLflow| MLFLOW
```

**Explicación del despliegue:**
- **Servidor Central**: Redis, PostgreSQL y MLflow compartidos
- **Nodo API+Manager**: Corre la API FastAPI y el worker Manager de Optuna
- **Nodos Worker**: Cada nodo tiene su Invoker Celery y Docker para ejecutar contenedores
- **NeuralForgeAI**: Interfaz React que consume la API

---

## Componentes del Sistema

| Repositorio | Función | Puerto |
|-------------|---------|--------|
| **wyoloservice2_control_server** | API Gateway + Interfaz Gradio | 8000 |
| **wyoloservice2_manager** | Orchestrator con Optuna | N/A |
| **wyoloservice2_invoker** | Ejecuta Docker run al worker | N/A |
| **wyoloservice2_worker** | Contenedor que entrena YOLO | N/A |
| **NeuralForgeAI** | Interfaz React | 3000 |

---

## 📥 Clonar Repositorios

Clona todos los repositorios necesarios para desplegar el cluster:

```bash
# 1. Control Server (API + Manager + Gradio)
git clone https://github.com/wisrovi/wyoloservice2_control_server.git
cd wyoloservice2_control_server

# 2. Worker Invoker (Celery Worker que ejecuta Docker)
git clone https://github.com/wisrovi/wyoloservice2_invoker.git

# 3. Worker Executor (Contenedor YOLO)
git clone https://github.com/wisrovi/wyoloservice2_worker.git

# 4. Manager (Orquestador Optuna)
git clone https://github.com/wisrovi/wyoloservice2_manager.git

# 5. NeuralForgeAI (Frontend React)
git clone https://github.com/wisrovi/NeuralForgeAI.git
```

### URLs de los Repositorios

| Servicio | GitHub URL |
|----------|------------|
| **Control Server** | https://github.com/wisrovi/wyoloservice2_control_server |
| **Worker Invoker** | https://github.com/wisrovi/wyoloservice2_invoker |
| **Worker Executor** | https://github.com/wisrovi/wyoloservice2_worker |
| **Manager** | https://github.com/wisrovi/wyoloservice2_manager |
| **NeuralForgeAI** | https://github.com/wisrovi/NeuralForgeAI |

### Estructura de Carpetas Recomendada

```
train_service/
├── wyoloservice2_control_server/   # API + Gradio
├── wyoloservice2_manager/           # Optuna Orchestrator
├── wyoloservice2_invoker/           # Celery Worker
├── wyoloservice2_worker/            # YOLO Executor Container
└── NeuralForgeAI/                  # React Frontend
```

---

## Variables de Entorno Comunes

```bash
# Infraestructura Central
REDIS_URL=redis://192.168.10.252:23437/0
OPTUNA_DB_URL=postgresql://postgres:postgres@192.168.10.252:23436/wyoloservice

# Worker específico
WORKER_NAME=gpu_node_01
PRIVATE_QUEUE=worker_gpu1
```

---

## Uso Rápido

### 1. Iniciar Infraestructura Central

```bash
cd wyoloservice2_control_server
docker-compose up -d
```

### 2. Iniciar un Worker

```bash
cd wyoloservice2_invoker
WORKER_NAME=gpu_node_01 docker-compose up -d
```

### 3. Lanzar Entrenamiento (vía Gradio)

Abre tu navegador y ve a **http://localhost:7860** para usar la interfaz Gradio:

1. En la pestaña **"New Study"**:
   - Sube tu archivo `config_train.yaml`
   - Selecciona el **Modo**:
     - `public`: La tarea se envía a la cola pública (`gpus_high`, `gpus_medium`, `gpus_low`)
     - `private`: La tarea se envía a un worker específico
   - Selecciona la **Prioridad** (solo en modo public): `high`, `medium` o `low`
   - Si es modo private, selecciona el **Worker** destino
2. Haz clic en **"Launch Study"**
3. Copia el **Study ID**returned para hacer seguimiento

### 4. Verificar Estado

Consulta el estado del estudio en la pestaña **"Monitor"**:

---

## Monitoreo

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Gradio UI** | http://localhost:7860 | Interfaz simple de control |
| **MLflow** | http://localhost:23435 | Tracking de experimentos |
| **Optuna Dashboard** | http://localhost:8080 | Visualización de estudios |
| **Flower** | http://localhost:5555 | Monitoreo de Celery |

---

**William R.** - AI Leader & Solutions Architect
