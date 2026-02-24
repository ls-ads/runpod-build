# runpod-build

A powerful CLI tool to deploy RunPod templates to specific GPUs with automatic data extraction via S3.

## Features

- **Parallel Deployment**: Deploy to multiple GPUs concurrently.
- **Resource Management**: Automatically creates and cleans up pods and temporary network volumes.
- **Data Extraction**: Automatically syncs `/output` from the pod to a local path via S3.
- **Dependency Management**: Built with `uv` for fast, reproducible environments.

## Prerequisites

- [uv](https://github.com/astral-sh/uv)
- RunPod API Key
- AWS S3 Credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`). These are **provided by RunPod** for your account (find them in the RunPod console under Settings > S3 Settings). These are used to access the S3-compatible API of your RunPod network volumes.

## Setup

1. Clone the repository.
2. Create a `.env` file from the template:
   ```bash
   cp .env.example .env
   ```
3. Fill in your credentials:
   ```env
   RUNPOD_API_KEY=your_runpod_key
   AWS_ACCESS_KEY_ID=your_runpod_user_id
   AWS_SECRET_ACCESS_KEY=your_runpod_s3_secret
   ```

*Note: S3 bucket names and endpoint URLs are now automatically detected from your RunPod deployment.*

## Usage

```bash
# List available GPUs
uv run runpod-build gpus

# Deploy to specific GPUs
uv run runpod-build deploy <template_id> <gpu_id_or_list> [options]
```

### Examples

List all available GPU options:
```bash
uv run runpod-build gpus
```

Deploy to a single 4090:
```bash
uv run runpod-build deploy n6m0htekvq "NVIDIA GeForce RTX 4090"
```

Deploy to multiple GPUs in parallel:
```bash
uv run runpod-build deploy n6m0htekvq "NVIDIA GeForce RTX 4090,NVIDIA RTX A5000" --max-workers 5
```

Deploy in a specific region (data center):
```bash
uv run runpod-build deploy n6m0htekvq "NVIDIA GeForce RTX 4090" --region US-CA-2
```

Deploy with a custom sentinel file (e.g., the actual build artifact):
```bash
uv run runpod-build deploy n6m0htekvq "NVIDIA GeForce RTX 4090" --sentinel path/to/build_artifact
```

### Options

- `--volume-size`: Size of the temporary network volume (default: 10GB).
- `--output-path`: Local directory to save extracted results (default: `./results`).
- `--max-workers`: Maximum concurrent deployments (default: 5).
- `--sentinel`: Name of the file the container creates to signal completion (default: `DONE`).
- `--region`: RunPod data center ID (e.g., `EU-RO-1`, `US-CA-2`).
- `--timeout`: Max time (seconds) to wait for completion. Defaults to infinite polling until pod is deleted or sentinel is found.

## Development

### Running Tests

We use `pytest` for testing. To run the tests, use:

```bash
uv run pytest
```

To run a specific test file or with more verbose output:

```bash
uv run pytest tests/test_runpod_manager.py -v
```

### Adding New Tests

New tests should be added to the `tests/` directory with the `test_*.py` naming convention. For tests involving external services (RunPod, S3), use `unittest.mock` to avoid side effects.

Example:
```python
from unittest.mock import patch

@patch("runpod_build.runpod_manager.requests.post")
def test_something(mock_post):
    # Your test here
```

## Container Workflow

The tool jumps directly to polling S3 for this file after pod creation. It no longer waits for a specific pod status (like `RUNNING`), but it will continuously verify that the pod still exists. If the pod is deleted or disappears, the tool will automatically clean up the resources and exit.

Once the sentinel is found, the tool downloads all contents of the output directory and then **immediately terminates the pod** to prevent billing or unexpected restarts.

### Output Structure

Results are saved to your `--output-path` (default: `./results`) using a descriptive subfolder naming scheme:

```
{output-path}/{template_id}-{sanitized_gpu}-{timestamp}/
```

For example: `results/qn96ymnjpd-nvidia-rtx-a4500-1708871234/`. This makes it easy to track artifacts for specific GPU builds and templates.

### Bash Example

In your build script or Dockerfile `CMD`:

```bash
# ... run build commands ...
# e.g., gcc main.c -o /output/myapp

# Signal completion
touch /output/DONE
```

### Python Example

```python
import os

# ... perform build ...
with open("/output/myapp", "wb") as f:
    f.write(data)

# Signal completion
with open("/output/DONE", "w") as f:
    f.write("finished")
```

## Cleanup

The tool automatically deletes pods and network volumes once the task is complete or if an error occurs.
