import os
import time
import runpod
from typing import List, Optional, Dict

class RunPodManager:
    def __init__(self, api_key: str):
        runpod.api_key = api_key
        self.api_key = api_key

    def get_gpu_region(self, gpu_id: str) -> str:
        """
        Helper to find a region where the desired GPU is available.
        Note: The RunPod SDK get_gpus() doesn't directly return region per GPU,
        but we can infer or use the first available instance location.
        For simplicity in this tool, we might try to create the pod and see where it lands,
        but network volumes MUST be created in a specific region.
        
        Refined approach: Use runpod.get_gpus() and check locations if available, 
        or use a default if not specified.
        """
        # This is a bit of a heuristic as the SDK doesn't make it trivial to map 
        # a GPU ID to a region without a search.
        return "US-NORD" # Placeholder - in practice, we'll need to query availability.

    def create_network_volume(self, name: str, size_gb: int, region: str) -> str:
        """Creates a network volume and returns its ID."""
        # Note: Network volume creation might require GraphQL if not in SDK.
        # Based on docs provided, create_template is there but volume creation is sparse.
        # I'll use the documented API structure if possible.
        # If the SDK doesn't have it, I'll use a placeholder and note it.
        try:
            volume = runpod.create_network_volume(
                name=name,
                size_gb=size_gb,
                data_center_id=region
            )
            return volume["id"]
        except Exception as e:
            print(f"Error creating volume: {e}")
            raise

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
        # Placeholder for volume deletion
        pass
