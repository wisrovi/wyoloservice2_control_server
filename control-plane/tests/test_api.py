import pytest
from fastapi.testclient import TestClient
import sys
import os

# Añadir la raíz al path para encontrar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

import io
import yaml

client = TestClient(app)


def test_start_training_with_yaml():
    """
    Test the /train endpoint with a sample YAML file.
    """
    sample_config = {
        "sweeper": {
            "study_name": "test_study",
            "n_trials": 2,
            "search_space": {"lr": ["uniform", 0.001, 0.01]},
        }
    }
    yaml_content = yaml.dump(sample_config)

    # Create a file-like object
    config_file = (io.BytesIO(yaml_content.encode("utf-8")), "config_train.yaml")

    response = client.post("/train", files={"config_file": config_file})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Queued"
    assert "study_id" in data
    assert data["study_name"] == "test_study"


def test_invalid_file_extension():
    """
    Test that uploading a non-YAML file fails.
    """
    config_file = (io.BytesIO(b"content"), "test.txt")
    response = client.post("/train", files={"config_file": config_file})
    assert response.status_code == 400
    assert "YAML" in response.json()["detail"]
