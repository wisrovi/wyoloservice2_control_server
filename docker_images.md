# Docker Image Naming Convention

All project images follow a standardized naming pattern for consistency across registries and deployments.

## Pattern
`wisrovi/train_service:xxx_vzzz`

- **`xxx`**: The functional block or component (e.g., `control_server`, `manager`, `worker_invoker`, `worker_executor`, `neuralforgeai`).
- **`vzzz`**: The version tag (e.g., `v1.0.0`).

## Image Registry

| Component | Image Name | Description |
| :--- | :--- | :--- |
| **API Gateway** | `wisrovi/train_service:api_server_v1.0.0` | FastAPI (Movido a NeuralForgeAI/api) |
| **Monitoring GUI** | `wisrovi/train_service:interfaz_ui_v1.0.0` | Gradio Interface (En este repo) |
| **Manager** | `wisrovi/train_service/manager:orchestrator_v1.0.0` | Optuna-based orchestrator |
| **Worker Invoker** | `wisrovi/train_service:worker_invoker_v1.0.0` | Celery worker (Docker manager) |
| **Worker Executor** | `wisrovi/train_service:worker_executor_v1.0.0` | Ephemeral training container |
| **NeuralForgeAI** | `wisrovi/train_service:w_darwin_ops_frontend_v1.1.0` | React frontend UI |

## Build and Push Commands (Este Repo)

```bash
# Gradio Monitoring Interface
docker build -t wisrovi/train_service:interfaz_ui_v1.0.0 ./interfaz
docker push wisrovi/train_service:interfaz_ui_v1.0.0
```

## Referencias Externas

```bash
# API Gateway (Desde NeuralForgeAI/api)
docker build -t wisrovi/train_service:api_server_v1.0.0 ./NeuralForgeAI/api
```
