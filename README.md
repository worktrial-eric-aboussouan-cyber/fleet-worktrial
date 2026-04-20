# Fleet Work Trial: Task Generation Pipeline

This repository contains the end-to-end pipeline for generating, validating, and deploying coding tasks derived from real-world GitHub Pull Requests. These tasks are designed to benchmark and train agentic coding models like Harbor/SkyRL.

## Overview

The pipeline follows these steps:
1. **Scrape**: Identify high-quality candidate PRs from target repositories (`requests`, `click`, `flask`, `httpx`).
2. **Build**: Materialize candidates into self-contained task directories containing a `task.json`, `Dockerfile`, and `eval_script.sh`.
3. **Validate**: Perform a "two-canary" validation check using Docker to ensure the task is solvable (gold patch passes) and non-trivial (base state fails).
4. **Deploy**: Build and push the validated task images to a container registry.

## Project Structure

```text
.
├── scripts/
│   ├── scrape_prs.py      # Scrapes candidate PRs using GitHub API
│   ├── build_task.py      # Generates task folders from scraped candidates
│   ├── validate_task.py   # Runs Docker-based two-canary validation
│   └── push_images.py     # Parallel build & push to registry
├── templates/
│   ├── Dockerfile.*       # Repo-specific Docker templates
│   └── README.md          # Documentation on repo extras chosen
├── tasks/                 # Generated task instances (task_001, etc.)
└── status.md              # Current project status and roadmap
```

## Getting Started

### Prerequisites
- Python 3.11+
- Docker Desktop
- GitHub Personal Access Token (for scraping)
- `uv` for dependency management (optional but recommended)

### Setup
1. Clone the repository.
2. Set up your environment variables in `.env` (refer to `.env.example` if available):
   ```bash
   GITHUB_TOKEN=your_token
   DOCKER_REGISTRY=gcr.io/your-project
   ```

## Usage

### 1. Scrape Candidates
Identify merged PRs that include new tests and clear fixes.
```bash
python scripts/scrape_prs.py psf/requests pallets/click
```

### 2. Build Tasks
Materialize the JSON candidates into directory-based task instances.
```bash
python scripts/build_task.py tasks/candidates_psf_requests.json
```

### 3. Validate Tasks
Run the "Two-Canary" check:
- **Canary 1**: Gold patch applied -> Tests MUST pass.
- **Canary 2**: No patch applied -> Tests MUST fail.
```bash
python scripts/validate_task.py
```

### 4. Push Images
Build and push the validated task images to your registry for use in training.
```bash
python scripts/push_images.py
```

## Task Design

Each task uses a `python:3.11-slim` base image and includes:
- **Editable Install**: The repository is installed in editable mode with appropriate test extras (e.g., `socks` for requests, `async,dotenv` for flask).
- **Evaluation Script**: A standalone `eval_script.sh` that targets specific test files and functions affected by the PR.
- **Parametrized Commits**: Dockerfiles are built using a `BASE_COMMIT` build argument to ensure reproducibility.
