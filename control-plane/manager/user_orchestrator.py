"""Manager Orchestrator Module.

This module coordinates Optuna studies, suggesting hyperparameters and
dispatching training trials to workers through Celery. It ensures sequential
execution and supports dynamic search spaces.
"""

import time
from typing import Any, Callable, Optional

import optuna
from optuna.trial import Trial
from celery.result import AsyncResult

# Import the Celery app configuration
from celery_config import app


def wait_for_result(job: AsyncResult) -> Any:
    """Blocks until the Celery task is ready and returns the result.

    Args:
        job (AsyncResult): The Celery task to wait for.

    Returns:
        Any: The result of the Celery task.
    """
    while not job.ready():
        time.sleep(2)
    return job.result


def create_objective(full_config: dict[str, Any]) -> Callable[[Trial], float]:
    """Creates a closure for the Optuna objective function.

    Args:
        full_config (dict[str, Any]): The full YAML configuration for the study.

    Returns:
        Callable[[Trial], float]: The objective function for Optuna optimize.
    """
    sweeper_cfg: dict[str, Any] = full_config.get("sweeper", {})
    worker_queue: str = sweeper_cfg.get("target_worker_queue", "gpus_medium")
    search_space: dict[str, Any] = sweeper_cfg.get("search_space", {})

    def objective(trial: Trial) -> float:
        """The actual objective function called by Optuna.

        Args:
            trial (Trial): The Optuna trial object.

        Returns:
            float: The accuracy (or metric) achieved in the trial.
        """
        trial_config: dict[str, Any] = full_config.copy()

        def parse_space(space: dict[str, Any], prefix: str = "") -> dict[str, Any]:
            """Recursively parses the search space into Optuna suggestions.

            Args:
                space (dict[str, Any]): The search space definition.
                prefix (str, optional): Prefix for nested keys. Defaults to "".

            Returns:
                dict[str, Any]: The suggested hyperparameters for this trial.
            """
            params: dict[str, Any] = {}
            for key, value in space.items():
                if isinstance(value, dict):
                    params[key] = parse_space(value, f"{prefix}{key}_")
                elif isinstance(value, list) and len(value) >= 2:
                    dist_type: str = value[0]
                    args: list[Any] = value[1:]
                    # Ensure numeric arguments are properly typed
                    processed_args: list[Any] = []
                    for arg in args:
                        if isinstance(arg, str):
                            try:
                                processed_args.append(float(arg))
                            except ValueError:
                                processed_args.append(arg)
                        else:
                            processed_args.append(arg)

                    if dist_type == "choice":
                        params[key] = trial.suggest_categorical(f"{prefix}{key}", args)
                    elif dist_type == "uniform":
                        params[key] = trial.suggest_float(
                            f"{prefix}{key}", processed_args[0], processed_args[1]
                        )
                    elif dist_type == "loguniform":
                        params[key] = trial.suggest_float(
                            f"{prefix}{key}",
                            processed_args[0],
                            processed_args[1],
                            log=True,
                        )
                    elif dist_type == "range":
                        step: int = (
                            int(processed_args[2]) if len(processed_args) > 2 else 1
                        )
                        params[key] = trial.suggest_int(
                            f"{prefix}{key}",
                            int(processed_args[0]),
                            int(processed_args[1]),
                            step=step,
                        )
                    else:
                        params[key] = args[0]
                else:
                    params[key] = value
            return params

        # Generate overrides from the search space
        overrides: dict[str, Any] = parse_space(search_space)
        for key, value in overrides.items():
            if isinstance(value, dict) and key in trial_config:
                trial_config[key].update(value)
            else:
                trial_config[key] = value

        # Dispatch the trial task to the worker
        job: AsyncResult = app.send_task(
            "tasks.train_on_gpu", args=[trial_config], queue=worker_queue
        )

        # Wait for completion and extract the metric
        result: Optional[dict[str, Any]] = wait_for_result(job)
        if result and "accuracy" in result:
            return float(result["accuracy"])
        return 0.0

    return objective


@app.task(name="tasks.manage_study")
def manage_study(full_config: dict[str, Any]) -> dict[str, Any]:
    """Orchestrates an entire Optuna study.

    Args:
        full_config (dict[str, Any]): The complete study configuration.

    Returns:
        dict[str, Any]: The study results including the best parameters found.
    """
    sweeper_cfg: dict[str, Any] = full_config.get("sweeper", {})
    study_name: str = sweeper_cfg.get("study_name", "default_study")
    direction: str = sweeper_cfg.get("direction", "maximize")
    n_trials: int = int(sweeper_cfg.get("n_trials", 10))

    storage_url: str = "sqlite:///optuna_study.db"
    study: optuna.Study = optuna.create_study(
        study_name=study_name,
        direction=direction,
        storage=storage_url,
        load_if_exists=True,
    )

    # Run the optimization loop
    study.optimize(create_objective(full_config), n_trials=n_trials)

    return {
        "status": "completed",
        "study_name": study_name,
        "best_params": study.best_params,
        "best_value": study.best_value,
    }
