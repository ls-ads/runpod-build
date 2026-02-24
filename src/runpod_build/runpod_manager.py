import os
import time
import requests
import runpod
from typing import List, Optional, Dict

class RunPodManager:
    def __init__(self, api_key: str):
        runpod.api_key = api_key
        self.api_key = api_key
        self.base_url = "https://rest.runpod.io/v1"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_gpu_region(self, gpu_id: str) -> str:
        """
        Helper to find a region where the desired GPU is available.
        For now, returns US-NORD as a default.
        """
        return "US-NORD"

    def create_network_volume(self, name: str, size_gb: int, region: str) -> str:
        """Creates a network volume via REST API."""
        url = f"{self.base_url}/networkvolumes"
        payload = {
            "name": name,
            "size": size_gb,
            "dataCenterId": region
        }
        
        response = requests.post(url, json=payload, headers=self._get_headers())
        if response.status_code != 200:
            raise Exception(f"Failed to create network volume: {response.status_code} - {response.text}")
            
        volume_data = response.json()
        return volume_data["id"]

    def create_pod_with_template(
        self, 
        name: str, 
        template_id: str, 
        gpu_id: str, 
        volume_id: str, 
        mount_path: str = "/output"
    ) -> Dict:
        """Creates a pod using a template and attaches a network volume."""
        try:
            pod = runpod.create_pod(
                name=name,
                template_id=template_id,
                gpu_type_id=gpu_id,
                network_volume_id=volume_id,
                volume_mount_path=mount_path,
                gpu_count=1
            )
            return pod
        except Exception as e:
            print(f"Error creating pod: {e}")
            raise

    def wait_for_pod(self, pod_id: str, timeout: int = 600) -> str:
        """Waits for pod to be running and returns its status."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            pod = runpod.get_pod(pod_id)
            status = pod.get("status")
            if status == "RUNNING":
                return "RUNNING"
            if status == "EXITED":
                return "EXITED"
            time.sleep(10)
        return "TIMEOUT"

    def stop_pod(self, pod_id: str):
        runpod.stop_pod(pod_id)

    def terminate_pod(self, pod_id: str):
        runpod.terminate_pod(pod_id)

    def delete_volume(self, volume_id: str):
        """Deletes a network volume via REST API."""
        url = f"{self.base_url}/networkvolumes/{volume_id}"
        response = requests.delete(url, headers=self._get_headers())
        if response.status_code not in [200, 204]:
            print(f"Warning: Failed to delete volume {volume_id}: {response.status_code} - {response.text}")

