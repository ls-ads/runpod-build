import concurrent.futures
import uuid
import os
from typing import List, Dict
from runpod_manager import RunPodManager
from s3_manager import S3Manager

class DeploymentOrchestrator:
    def __init__(
        self, 
        runpod_mgr: RunPodManager, 
        s3_mgr: S3Manager, 
        max_workers: int = 5
    ):
        self.runpod_mgr = runpod_mgr
        self.s3_mgr = s3_mgr
        self.max_workers = max_workers

    def deploy_single(
        self, 
        template_id: str, 
        gpu_id: str, 
        volume_size: int, 
        output_local_path: str
    ) -> Dict:
        """Handles the full lifecycle for a single GPU deployment."""
        deployment_id = str(uuid.uuid4())[:8]
        pod_name = f"build-{deployment_id}"
        volume_name = f"vol-{deployment_id}"
        s3_prefix = f"runpod-build/{deployment_id}/"
        
        pod_id = None
        volume_id = None
        
        try:
            # 1. Create Volume (In practice, region selection is needed)
            # For now, using a default region or querying for the GPU availability.
            region = "US-NORD" # This should ideally be dynamic based on GPU
            volume_id = self.runpod_mgr.create_network_volume(volume_name, volume_size, region)
            print(f"[{pod_name}] Created volume: {volume_id}")

            # 2. Create Pod
            # Injecting AWS credentials and S3 target for the pod to use.
            pod = self.runpod_mgr.create_pod_with_template(
                name=pod_name,
                template_id=template_id,
                gpu_id=gpu_id,
                volume_id=volume_id
            )
            pod_id = pod["id"]
            print(f"[{pod_name}] Started pod: {pod_id} on {gpu_id}")

            # 3. Wait for completion
            status = self.runpod_mgr.wait_for_pod(pod_id)
            print(f"[{pod_name}] Pod finished with status: {status}")

            # 4. Extract from S3
            # We assume the pod uploaded its /output to s3://bucket/runpod-build/<id>/
            print(f"[{pod_name}] Downloading results from S3...")
            self.s3_mgr.download_directory(s3_prefix, os.path.join(output_local_path, deployment_id))
            
            return {"status": "SUCCESS", "pod_id": pod_id, "gpu": gpu_id}

        except Exception as e:
            print(f"[{pod_name}] Deployment failed: {e}")
            return {"status": "FAILED", "gpu": gpu_id, "error": str(e)}
        
        finally:
            # 5. Cleanup
            if pod_id:
                print(f"[{pod_name}] Terminating pod...")
                self.runpod_mgr.terminate_pod(pod_id)
            if volume_id:
                print(f"[{pod_name}] Deleting volume...")
                self.runpod_mgr.delete_volume(volume_id)
            # Cleanup S3 transit data
            self.s3_mgr.delete_prefix(s3_prefix)

    def run_parallel(
        self, 
        template_id: str, 
        gpu_ids: List[str], 
        volume_size: int, 
        output_local_path: str
    ):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_gpu = {
                executor.submit(
                    self.deploy_single, 
                    template_id, 
                    gpu_id, 
                    volume_size, 
                    output_local_path
                ): gpu_id for gpu_id in gpu_ids
            }
            for future in concurrent.futures.as_completed(future_to_gpu):
                results.append(future.result())
        
        return results
