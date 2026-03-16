# Manager - Study Orchestrator

The Manager is the "brain" of the cluster. It utilizes **Optuna** to orchestrate distributed hyperparameter optimization.

## Operation
1.  **Ingestion**: Listens to the `managers` queue and receives the full parsed YAML configuration.
2.  **Study Initialization**: Creates or loads an Optuna study, using a local SQLite database for state persistence.
3.  **Optimization Loop**: 
    *   Optuna suggests a set of hyperparameters based on the `search_space`.
    *   The Manager dispatches a `tasks.train_on_gpu` task to the specified worker queue (`gpus_high/medium/low` or private queue).
    *   **Controlled Blocking**: The Manager waits for the worker's result via a polling loop (`wait_for_result`). This ensures that trials are processed sequentially and prevents the orchestrator from being overwhelmed.
4.  **Completion**: Once all trials are finished, it returns the best parameters found.

## Configuration (`config.yaml`)
Defines default values for Optuna (number of trials, direction) and Redis connection URLs if not provided via environment variables.

## Why use `-P solo`?
The Manager runs with Celery's `solo` pool (`-P solo`). This is **critical** as it allows a Celery task (the study) to wait for the result of other tasks (the trials) without causing a deadlock, maintaining execution within a single control thread for Optuna.
