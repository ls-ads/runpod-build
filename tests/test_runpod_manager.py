import pytest
from unittest.mock import patch, MagicMock
from runpod_build.runpod_manager import RunPodManager

@pytest.fixture
def runpod_manager():
    return RunPodManager(api_key="test_key")

@patch("runpod_build.runpod_manager.requests.post")
def test_create_network_volume(mock_post, runpod_manager):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "vol-123"}
    mock_post.return_value = mock_response

    # Call the method
    vol_id = runpod_manager.create_network_volume("test-vol", 10, "US-NORD")

    # Verify calls
    assert vol_id == "vol-123"
    mock_post.assert_called_once_with(
        "https://rest.runpod.io/v1/networkvolumes",
        json={"name": "test-vol", "size": 10, "dataCenterId": "US-NORD"},
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json"
        }
    )

@patch("runpod_build.runpod_manager.requests.delete")
def test_delete_volume(mock_delete, runpod_manager):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_delete.return_value = mock_response

    # Call the method
    runpod_manager.delete_volume("vol-123")

    # Verify calls
    mock_delete.assert_called_once_with(
        "https://rest.runpod.io/v1/networkvolumes/vol-123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json"
        }
    )

@patch("runpod_build.runpod_manager.requests.post")
def test_create_pod_with_template(mock_post, runpod_manager):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "pod-123"}
    mock_post.return_value = mock_response

    # Call the method
    pod = runpod_manager.create_pod_with_template(
        name="test-pod",
        template_id="tmpl-123",
        gpu_id="4090",
        volume_id="vol-123",
        region="US-NORD"
    )

    # Verify
    assert pod["id"] == "pod-123"
    mock_post.assert_called_once_with(
        "https://rest.runpod.io/v1/pods",
        json={
            "name": "test-pod",
            "templateId": "tmpl-123",
            "gpuTypeIds": ["4090"],
            "gpuTypePriority": "custom",
            "gpuCount": 1,
            "networkVolumeId": "vol-123",
            "volumeMountPath": "/output",
            "dataCenterIds": ["US-NORD"],
            "dataCenterPriority": "custom"
        },
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json"
        }
    )

@patch("runpod_build.runpod_manager.requests.delete")
def test_delete_endpoint(mock_delete, runpod_manager):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_delete.return_value = mock_response

    # Call the method
    runpod_manager.delete_endpoint("endpoint-123")

    # Verify calls
    mock_delete.assert_called_once_with(
        "https://rest.runpod.io/v1/endpoints/endpoint-123",
        headers={
            "Authorization": "Bearer test_key",
            "Content-Type": "application/json"
        }
    )
