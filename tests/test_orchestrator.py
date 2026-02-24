import py
import pytest
import uuid
from unittest.mock import MagicMock, patch
from runpod_build.orchestrator import DeploymentOrchestrator

@pytest.fixture
def orchestrator():
    runpod_mgr = MagicMock()
    s3_mgr = MagicMock()
    return DeploymentOrchestrator(runpod_mgr, s3_mgr)

@patch("uuid.uuid4")
@patch("time.sleep")
def test_deploy_single_sentinel(mock_sleep, mock_uuid, orchestrator):
    # Setup mocks
    mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')    # Mock RunPodManager methods
    orchestrator.runpod_mgr.get_gpu_region.return_value = "US-NORD"
    orchestrator.runpod_mgr.create_network_volume.return_value = "vol-123"
    orchestrator.runpod_mgr.get_s3_endpoint.return_value = "https://s3api-us-nord.runpod.io/"
    orchestrator.runpod_mgr.create_pod_with_template.return_value = {"id": "pod-123"}
    orchestrator.runpod_mgr.wait_for_pod.return_value = "RUNNING"
    orchestrator.s3_mgr.object_exists.return_value = True
    
    # Call method
    result = orchestrator.deploy_single(
        template_id="tmpl-123",
        gpu_id="4090",
        volume_size=10,
        output_local_path="/tmp/results"
    )
    
    # Verify
    assert result["status"] == "SUCCESS"
    orchestrator.s3_mgr.object_exists.assert_called_with(
        "https://s3api-us-nord.runpod.io/", "vol-123", "DONE"
    )
    orchestrator.s3_mgr.download_directory.assert_called_once_with(
        "https://s3api-us-nord.runpod.io/", "vol-123", "", "/tmp/results/12345678"
    )
    
    # Verify sequential deployment
    orchestrator.runpod_mgr.create_network_volume.assert_called_once()
    assert mock_sleep.call_args_list[0][0][0] == 5
    orchestrator.runpod_mgr.create_pod_with_template.assert_called_once()
    
    # Verify cleanup
    orchestrator.runpod_mgr.terminate_pod.assert_called_once_with("pod-123")
    orchestrator.runpod_mgr.delete_volume.assert_called_once_with("vol-123")
