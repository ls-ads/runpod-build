import concurrent.futures
import uuid
import os
from typing import List, Dict
from .runpod_manager import RunPodManager
from .s3_manager import S3Manager

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
        output_local_path: str,
        sentinel_filename: str = "DONE",
        region: str = None,
        timeout: int = None,
        keep_failed: bool = False
    ) -> Dict:
        """Handles the full lifecycle for a single GPU deployment."""
        deployment_id = str(uuid.uuid4())[:8]
        pod_name = f"build-{deployment_id}"
        volume_name = f"vol-{deployment_id}"
        
        pod_id = None
        volume_id = None
        s3_endpoint = None
        
        try:
            # 1. Create Volume
            region = self.runpod_mgr.get_gpu_region(gpu_id, region)
            volume_id = self.runpod_mgr.create_network_volume(volume_name, volume_size, region)
            s3_endpoint = self.runpod_mgr.get_s3_endpoint(region)
            print(f"[{pod_name}] Created volume: {volume_id} in {region}")
            print(f"[{pod_name}] S3 Endpoint: {s3_endpoint}")

            # Settle time to ensure volume is fully registered in RunPod's backend
            import time
            time.sleep(5)

            # 2. Create Pod
            pod = self.runpod_mgr.create_pod_with_template(
                name=pod_name,
                template_id=template_id,
                gpu_id=gpu_id,
                volume_id=volume_id,
                region=region
            )
            pod_id = pod["id"]
            print(f"[{pod_name}] Started pod: {pod_id} on {gpu_id}")

            # 3. Poll S3 for sentinel file with pod exit check
            print(f"[{pod_name}] Waiting for sentinel file '{sentinel_filename}' in S3 volume {volume_id}...")
            found_sentinel = False
            start_time = time.time()
            
            while True:
                # Check for timeout if one is set
                if timeout and (time.time() - start_time > timeout):
                    break

                # Check for sentinel file
                if self.s3_mgr.object_exists(s3_endpoint, volume_id, sentinel_filename, region_name=region):
                    found_sentinel = True
                    break
                
                # Verify pod still exists
                status = self.runpod_mgr.wait_for_pod(pod_id, timeout=0)
                if status == "NOT_FOUND":
                    raise Exception("Pod disappeared during build (likely system removal or manual deletion)")
                
                time.sleep(15)
            
            if not found_sentinel:
                raise Exception(f"Timed out after {timeout}s" if timeout else "Polling timed out unexpectedly")

            # 4. Download results
            print(f"[{pod_name}] Sentinel found! Downloading results to {output_local_path}...")
            # We use the deployment name (minus the build- prefix) as the subfolder
            local_dest = os.path.join(output_local_path, deployment_id)
            self.s3_mgr.download_directory(s3_endpoint, volume_id, "", local_dest, region_name=region)
            
            # 5. Cleanup S3 sentinel (optional but good practice)
            # self.s3_mgr.delete_prefix(s3_endpoint, volume_id, sentinel_filename, region_name=region)
            
            return {"status": "SUCCESS", "pod_id": pod_id, "gpu": gpu_id}

        except Exception as e:
            print(f"[{pod_name}] Deployment failed: {e}")
            return {"status": "FAILED", "gpu": gpu_id, "error": str(e)}
        
        finally:
            # 6. Cleanup (Immediate termination unless keep_failed is set)
            # We ONLY keep resources if it failed AND keep_failed is True
            should_cleanup = (res.get("status") == "SUCCESS" if 'res' in locals() else False) or not keep_failed
            
            # Since 'res' might not be in locals if we failed before returning, 
            # we need to be careful. If we are in the 'finally' block, we either succeeded or caught an exception.
            # Let's adjust the logic slightly.
            
            # Re-calculating success based on the current context (within try/except)
            is_success = 'found_sentinel' in locals() and found_sentinel
            should_cleanup = is_success or not keep_failed

            if should_cleanup:
                if pod_id:
                    try:
                        print(f"[{pod_name}] Terminating pod: {pod_id}")
                        self.runpod_mgr.terminate_pod(pod_id)
                    except Exception as e:
                        print(f"[{pod_name}] Failed to terminate pod {pod_id}: {e}")
                        
                if volume_id:
                    try:
                        print(f"[{pod_name}] Deleting volume: {volume_id}")
                        self.runpod_mgr.delete_volume(volume_id)
                    except Exception as e:
                        print(f"[{pod_name}] Failed to delete volume {volume_id}: {e}")
            else:
                print(f"[{pod_name}] KEEP-FAILED: Skipping resource cleanup. Pod: {pod_id}, Volume: {volume_id}")

    def run_parallel(
        self, 
        template_id: str, 
        gpu_ids: List[str], 
        volume_size: int, 
        output_local_path: str,
        sentinel_filename: str = "DONE",
        region: str = None,
        timeout: int = None,
        keep_failed: bool = False
    ):
        results = []
        actual_workers = min(len(gpu_ids), self.max_workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
            future_to_gpu = {
                executor.submit(
                    self.deploy_single, 
                    template_id, 
                    gpu_id, 
                    volume_size, 
                    output_local_path,
                    sentinel_filename,
                    region,
                    timeout,
                    keep_failed
                ): gpu_id for gpu_id in gpu_ids
            }
            for future in concurrent.futures.as_completed(future_to_gpu):
                results.append(future.result())
        
        return results
