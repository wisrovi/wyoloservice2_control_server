# NeuralForgeAI - Communication Flow

Este documento describe cómo interactúan los componentes del ecosistema tras la consolidación de la API en el repositorio NeuralForgeAI.

## 1. Diagrama de Secuencia General

```mermaid
sequenceDiagram
    participant U as Usuario (React UI / Gradio)
    participant API as API Gateway (NeuralForgeAI/api)
    participant R as Redis (Infrastructure)
    participant M as Manager (Orchestrator)
    participant W as Workers (GPU Invoker)

    U->>API: 1. POST /train (config.yaml)
    API->>API: 2. Valida & Encola
    API->>R: 3. Publica Tarea (managers)
    R->>M: 4. Consume Tarea
    M->>API: 5. Consulta estado Optuna
    M->>R: 6. Encola Trials (gpus_*)
    R->>W: 7. Ejecuta Entrenamiento
    W-->>R: 8. Reporta Resultados
    M-->>API: 9. Actualiza Estudio
    API-->>U: 10. Status: Completed
```

## 2. Responsabilidades por Repositorio

### [NeuralForgeAI](https://github.com/wisrovi/NeuralForgeAI)
- **UI**: Interfaz principal para el usuario final.
- **API Gateway**: El único punto de contacto para lanzar y monitorear estudios. Maneja la lógica de validación y encolado.

### [wyoloservice2_control_server](https://github.com/wisrovi/wyoloservice2_control_server)
- **Infrastructure**: Hosting de Redis y PostgreSQL.
- **Monitoring GUI**: Interfaz Gradio para diagnósticos rápidos de bajo nivel.

### [wyoloservice2_manager](https://github.com/wisrovi/wyoloservice2_manager)
- **Orchestration**: Lógica de Optuna y gestión del ciclo de vida de los estudios.

### [wyoloservice2_invoker](https://github.com/wisrovi/wyoloservice2_invoker)
- **Execution**: Gestión de contenedores Docker en nodos GPU y montaje de datasets.
