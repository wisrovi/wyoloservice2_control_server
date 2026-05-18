import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Añadir la raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manager.user_orchestrator import manage_study
from worker.worker_gpu import train_on_gpu

def test_train_on_gpu():
    """
    Test the GPU training task in isolation.
    """
    config = {"lr": 0.01, "user_id": "tester"}
    result = train_on_gpu(config)
    assert result["status"] == "done"
    assert "accuracy" in result
    assert result["accuracy"] == 0.85 + (0.01 * 0.1)

@patch('manager.user_orchestrator.optuna.create_study')
@patch('manager.user_orchestrator.app.send_task')
def test_manage_study(mock_send_task, mock_create_study):
    """
    Test the manage_study task in the manager.
    """
    # Mock Optuna study
    mock_study = MagicMock()
    mock_study.best_params = {"lr": 0.001}
    mock_study.best_value = 0.9
    mock_create_study.return_value = mock_study
    
    request_data = {"user_id": "tester", "priority": 5, "n_trials": 1}
    
    result = manage_study(request_data)
    
    assert result["user_id"] == "tester"
    assert "best_params" in result
    assert result["best_value"] == 0.9
    assert mock_create_study.called
    assert mock_study.optimize.called
