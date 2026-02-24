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

    def get_s3_endpoint(self, region: str) -> str:
        """Generates the S3-compatible API endpoint for a specific region."""
        # e.g., US-NORD -> https://s3api-us-nord.runpod.io/
        region_clean = region.lower().replace("_", "-")
        return f"https://s3api-{region_clean}.runpod.io/"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_gpu_region(self, gpu_id: str, region: str = None) -> str:
        """
        Finds a region where the desired GPU is available.
        Uses region if provided, otherwise defaults to EU-RO-1.
        """
        valid_regions = [
            "EU-RO-1", "CA-MTL-1", "EU-SE-1", "US-IL-1", "EUR-IS-1", "EU-CZ-1",
            "US-TX-3", "EUR-IS-2", "US-KS-2", "US-GA-2", "US-WA-1", "US-TX-1",
            "CA-MTL-3", "EU-NL-1", "US-TX-4", "US-CA-2", "US-NC-1", "OC-AU-1",
            "US-DE-1", "EUR-IS-3", "CA-MTL-2", "AP-JP-1", "EUR-NO-1", "EU-FR-1",
            "US-KS-3", "US-GA-1"
        ]
        
        if region:
            if region not in valid_regions:
                print(f"Warning: {region} is not in the list of standard RunPod data centers.")
            return region
            
        # Default to EU-RO-1 which typically has high availability for GPUs like 4090
        return "EU-RO-1"

    def create_network_volume(self, name: str, size_gb: int, region: str) -> str:
        """Creates a network volume via REST API."""
        url = f"{self.base_url}/networkvolumes"
        payload = {
            "name": name,
            "size": size_gb,
            "dataCenterId": region
        }
        
        response = requests.post(url, json=payload, headers=self._get_headers())
        if response.status_code not in range(200, 300):
            raise Exception(f"Failed to create network volume: {response.status_code} - {response.text}")
            
        volume_data = response.json()
        return volume_data["id"]

    def create_pod_with_template(
        self, 
        name: str, 
        template_id: str, 
        gpu_id: str, 
        volume_id: str, 
        region: str,
        mount_path: str = "/output"
    ) -> Dict:
        """Creates a pod via REST API with strict region and volume placement."""
        url = f"{self.base_url}/pods"
        payload = {
            "name": name,
            "templateId": template_id,
            "gpuTypeIds": [gpu_id],
            "gpuTypePriority": "custom",
            "gpuCount": 1,
            "networkVolumeId": volume_id,
            "volumeMountPath": mount_path,
            "dataCenterIds": [region],
            "dataCenterPriority": "custom"
        }
        
        response = requests.post(url, json=payload, headers=self._get_headers())
        if response.status_code != 201:
            raise Exception(f"Failed to create pod: {response.status_code} - {response.text}")
            
        return response.json()

    def delete_endpoint(self, endpoint_id: str):
        """Deletes a serverless endpoint."""
        url = f"{self.base_url}/endpoints/{endpoint_id}"
        response = requests.delete(url, headers=self._get_headers())
        if response.status_code != 204:
            raise Exception(f"Failed to delete endpoint: {response.status_code} - {response.text}")

    def wait_for_pod(self, pod_id: str, timeout: int = 1800) -> str:
        """Waits for pod to be running or finished and returns its status."""
        url = f"{self.base_url}/pods/{pod_id}"
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                pod = response.json()
                status = pod.get("status")
                desired_status = pod.get("desiredStatus")
                runtime = pod.get("runtime", {})
                uptime = runtime.get("uptimeInSeconds", 0) if runtime else 0
                
                # Debug print to help identify real status fields
                print(f"[DEBUG] Pod {pod_id}: status={status}, desiredStatus={desired_status}, uptime={uptime}")

                # High-confidence "running" if uptime is positive
                if uptime > 0:
                    return "RUNNING"
                
                # Fallback to status fields
                if status in ["RUNNING", "COMPLETED"] or desired_status in ["RUNNING", "COMPLETED"]:
                    return "RUNNING"
                
                if status in ["EXITED", "TERMINATED"] or desired_status in ["EXITED", "TERMINATED"]:
                    # If it exited/terminated but never had uptime, it might have failed early
                    return status or desired_status
            elif response.status_code == 404:
                return "NOT_FOUND"
                
            time.sleep(5)
        return "TIMEOUT"

    def stop_pod(self, pod_id: str):
        runpod.stop_pod(pod_id)

    def terminate_pod(self, pod_id: str):
        """Terminates a pod via REST API."""
        url = f"{self.base_url}/pods/{pod_id}"
        response = requests.delete(url, headers=self._get_headers())
        if response.status_code not in [200, 204]:
            print(f"Warning: Failed to terminate pod {pod_id}: {response.status_code} - {response.text}")

    def delete_volume(self, volume_id: str):
        """Deletes a network volume via REST API."""
        url = f"{self.base_url}/networkvolumes/{volume_id}"
        response = requests.delete(url, headers=self._get_headers())
        if response.status_code not in [200, 204]:
            print(f"Warning: Failed to delete volume {volume_id}: {response.status_code} - {response.text}")

