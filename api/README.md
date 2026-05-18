# API - ML Training Gateway

This API serves as the entry point for the training cluster. it allows users to submit complex training configurations via YAML files and monitor the status of their optimization studies.

## Endpoints

### 1. `POST /train`
Launches a new hyperparameter optimization study.

*   **Type**: Multipart Form Data
*   **Parameters**:
    *   `config_file`: A `.yaml` file containing the search space and training definition (e.g., `config_train.yaml`).
    *   `mode`: `"public"` (default) or `"private"`.
    *   `worker_name`: Required if mode is `"private"`. Name of the target worker's specific queue (e.g., `worker_1`).
    *   `priority`: `"high"`, `"medium"`, `"low"`. Only applies in public mode.

### 2. `GET /status/{study_id}`
Queries the current status of a study. Returns the Celery state (`PENDING`, `STARTED`, `SUCCESS`, etc.) and the result if completed.

### 3. `GET /workers`
Lists active workers that have a private queue (prefix `worker_`). Useful for identifying target workers for private mode dispatch.

## Usage Example (Python)

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

## Internal Architecture
The API performs minimal YAML validation and injects routing metadata into a Celery task sent to the `managers` queue. It does not process training directly, ensuring fast response times.
