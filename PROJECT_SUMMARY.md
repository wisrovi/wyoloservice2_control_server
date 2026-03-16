# Control Server - API Gateway + Gradio Interface

Este componente es el **punto de entrada** del cluster NeuralForgeAI. Proporciona una API REST y una interfaz Gradio para que los usuarios puedan lanzar estudios de entrenamiento.

## Funcionalidades

- **API REST (FastAPI)**: Endpoints para lanzar estudios, consultar estado, listar workers y gestionar tareas
- **Interfaz Gradio**: UI visual para subir archivos YAML y lanzar estudios sin código
- **Integración Celery**: Envía tareas al Manager para orquestación de estudios Optuna

## Endpoints Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/train` | POST | Lanzar nuevo estudio de entrenamiento |
| `/workers` | GET | Listar workers activos |
| `/status/{study_id}` | GET | Consultar estado de un estudio |
| `/tasks` | GET | Listar tareas en cola |
| `/tasks/{id}` | DELETE | Revocar tarea |
| `/tasks/{id}/requeue` | POST | Recolar tarea con prioridad |

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

### Enviar estudio por API

```python
import requests

files = {'config_file': open('config_train.yaml', 'rb')}
data = {
    'mode': 'public',
    'priority': 'high'
}

response = requests.post("http://localhost:8000/train", files=files, data=data)
print(response.json())
```

### Usar Gradio

Abre **http://localhost:7860** en tu navegador.

## Configuración

Las variables de entorno se configuran en `docker-compose.yml` o `.env`:

```yaml
environment:
  - REDIS_URL=redis://192.168.10.252:23437/0
  - OPTUNA_DB_URL=postgresql://postgres:postgres@192.168.10.252:23436/wyoloservice
```

## Arquitectura Interna

```
control_server/
├── api/
│   ├── main.py          # FastAPI app
│   ├── celery_config.py # Configuración de Celery
│   └── requirements.txt
├── interfaz/
│   ├── app.py          # Aplicación Gradio
│   └── requirements.txt
├── environment/         # Docker Compose para servicios
├── docker-compose.yml   # Orquestación principal
└── flow.md            # Diagrama del flujo
```

---

**William R.** - AI Leader & Solutions Architect
