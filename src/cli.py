import click
import os
from dotenv import load_dotenv
from runpod_manager import RunPodManager
from s3_manager import S3Manager
from orchestrator import DeploymentOrchestrator

@click.group()
def main():
    """RunPod Deployment Tool CLI."""
    pass

@main.command()
@click.argument('template_id')
@click.argument('gpu_ids')
@click.option('--volume-size', default=10, help='Size of the network volume in GB.')
@click.option('--output-path', default='./results', help='Local path to save results.')
@click.option('--max-workers', default=5, help='Max parallel deployments.')
@click.option('--s3-bucket', envvar='S3_BUCKET_NAME', help='S3 bucket for extraction.')
@click.option('--aws-region', envvar='AWS_REGION', default='us-east-1', help='AWS region.')
def deploy(template_id, gpu_ids, volume_size, output_path, max_workers, s3_bucket, aws_region):
    """
    Deploy a RunPod template to target GPUs and extract results.
    GPU_IDS can be a single ID or a comma-separated list.
    """
    load_dotenv()
    
    runpod_api_key = os.getenv("RUNPOD_API_KEY")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not all([runpod_api_key, aws_access_key, aws_secret_key, s3_bucket]):
        click.echo("Error: Missing required environment variables or --s3-bucket.")
        click.echo("Check RUNPOD_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME.")
        return

    # Parse GPU list
    gpu_list = [g.strip() for g in gpu_ids.split(',')]
    
    # Initialize Managers
    rp_mgr = RunPodManager(runpod_api_key)
    s3_mgr = S3Manager(aws_access_key, aws_secret_key, aws_region, s3_bucket)
    
    # Optional: Check account balance for worker limit suggestion
    try:
        user = runpod.get_user()
        balance = user.get('balance', 0)
        if balance < 100 and max_workers > 5:
            click.echo(f"Warning: Low balance (${balance}). Capping parallel builds to 5.")
            max_workers = 5
    except Exception:
        pass # Ignore if API doesn't support get_user or balance

    # Initialize Orchestrator
    orchestrator = DeploymentOrchestrator(rp_mgr, s3_mgr, max_workers=max_workers)
    
    click.echo(f"Starting deployment for template {template_id} on GPUs: {gpu_list}")
    results = orchestrator.run_parallel(template_id, gpu_list, volume_size, output_path)
    
    click.echo("\n--- Deployment Results ---")
    for res in results:
        status = res['status']
        gpu = res['gpu']
        if status == "SUCCESS":
            click.echo(f"SUCCESS: {gpu} (Pod: {res['pod_id']})")
        else:
            click.echo(f"FAILED: {gpu} - {res.get('error')}")

@main.command()
def gpus():
    """List all available GPU options."""
    gpus_list = [
        "NVIDIA GeForce RTX 4090", "NVIDIA A40", "NVIDIA RTX A5000", 
        "NVIDIA GeForce RTX 5090", "NVIDIA H100 80GB HBM3", "NVIDIA GeForce RTX 3090", 
        "NVIDIA RTX A4500", "NVIDIA L40S", "NVIDIA H200", "NVIDIA L4", 
        "NVIDIA RTX 6000 Ada Generation", "NVIDIA A100-SXM4-80GB", 
        "NVIDIA RTX 4000 Ada Generation", "NVIDIA RTX A6000", "NVIDIA A100 80GB PCIe", 
        "NVIDIA RTX 2000 Ada Generation", "NVIDIA RTX A4000", 
        "NVIDIA RTX PRO 6000 Blackwell Server Edition", "NVIDIA H100 PCIe", 
        "NVIDIA H100 NVL", "NVIDIA L40", "NVIDIA B200", "NVIDIA GeForce RTX 3080 Ti", 
        "NVIDIA RTX PRO 6000 Blackwell Workstation Edition", "NVIDIA GeForce RTX 3080", 
        "NVIDIA GeForce RTX 3070", "AMD Instinct MI300X OAM", "NVIDIA GeForce RTX 4080 SUPER", 
        "Tesla V100-PCIE-16GB", "Tesla V100-SXM2-32GB", "NVIDIA RTX 5000 Ada Generation", 
        "NVIDIA GeForce RTX 4070 Ti", "NVIDIA RTX 4000 SFF Ada Generation", 
        "NVIDIA GeForce RTX 3090 Ti", "NVIDIA RTX A2000", "NVIDIA GeForce RTX 4080", 
        "NVIDIA A30", "NVIDIA GeForce RTX 5080", "Tesla V100-FHHL-16GB", 
        "NVIDIA H200 NVL", "Tesla V100-SXM2-16GB", 
        "NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition", "NVIDIA A5000 Ada", 
        "Tesla V100-PCIE-32GB", "NVIDIA  RTX A4500", "NVIDIA  A30", 
        "NVIDIA GeForce RTX 3080TI", "Tesla T4", "NVIDIA RTX A30"
    ]
    # Remove duplicates and sort
    gpus_list = sorted(list(set([g.strip() for g in gpus_list])))
    click.echo("Available GPU options:")
    for gpu in gpus_list:
        click.echo(f"- {gpu}")

if __name__ == '__main__':
    main()
