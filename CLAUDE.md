# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| Next.js UI | 3000 (or 3001 if taken) | Frontend dashboard |
| FastAPI | 8000 | Orchestration backend |
| Label Studio | 8080 | Annotation tool |
| YOLO ML Backend | 9090 | Auto-labeling service |
| MLflow | 5000 | Experiment tracking |
| PostgreSQL | 5432 | Label Studio database |

## Essential Commands

### Start the full stack
```bash
docker compose up -d
cd ui && npm run dev
```

### Start services in the correct order (avoids memory issues)
```bash
docker compose up postgres mlflow -d
docker compose up label-studio -d
docker compose up api ml-backend -d
```

### Rebuild a specific service after code changes
```bash
docker compose build <service>   # api | ml-backend
docker compose up <service> --force-recreate -d
```

### View service logs
```bash
docker logs mlops-<service> --tail=50 -f
# service = api | ml-backend | mlflow | label-studio | postgres
```

### After first start: get Label Studio API key
```bash
curl -s http://localhost:8080/user/login -c /tmp/ls_cookies.txt -o /dev/null
CSRF=$(grep csrftoken /tmp/ls_cookies.txt | awk '{print $NF}')
curl -s -b /tmp/ls_cookies.txt -c /tmp/ls_cookies.txt \
  -X POST http://localhost:8080/user/login \
  -H "X-CSRFToken: ${CSRF}" -H "Referer: http://localhost:8080/" \
  -d "csrfmiddlewaretoken=${CSRF}&email=admin%40mlops.local&password=adminpassword" -L -o /dev/null
curl -s -b /tmp/ls_cookies.txt http://localhost:8080/api/current-user/token
# Copy the token to .env as LABEL_STUDIO_API_KEY
# Then enable legacy token auth (required for Label Studio 1.23+):
CSRF=$(grep csrftoken /tmp/ls_cookies.txt | awk '{print $NF}')
curl -s -b /tmp/ls_cookies.txt -X POST http://localhost:8080/api/jwt/settings \
  -H "Content-Type: application/json" -H "X-CSRFToken: ${CSRF}" -H "Referer: http://localhost:8080/" \
  -d '{"legacy_api_tokens_enabled": true}'
```

### FastAPI development (local, no Docker)
```bash
cd services/api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Next.js development
```bash
cd ui
npm install
npm run dev        # dev server
npm run build      # production build
npm run lint       # ESLint
```

## Architecture Overview

### Data Flow

**Upload → Auto-label:**
1. User uploads images via `POST /api/v1/datasets/upload`
2. FastAPI saves images to `/data/raw/{dataset_id}/`, creates Label Studio project and tasks
3. Image URLs are served as `http://api:8000/data/raw/{dataset_id}/{filename}` (static mount)
4. Label Studio calls `POST http://ml-backend:9090/predict` for each task (auto-annotation)

**Label → Train:**
1. User starts training via `POST /api/v1/training/jobs`
2. FastAPI exports annotations from Label Studio, runs `dataset_builder.py` for train/val/test split
3. Spawns `train.py` subprocess with device auto-detection (XPU → DirectML → CPU)
4. `train.py` logs metrics to MLflow and registers the final model to MLflow Model Registry
5. Logs are streamed to the UI via SSE at `GET /api/v1/training/jobs/{id}/logs`

**Model Registry:**
1. Trained models appear in MLflow Model Registry under `GET /api/v1/models/`
2. Stage transitions (None → Staging → Production) via `POST /api/v1/models/{name}/stage`
3. Production models are used for the next auto-labeling cycle

### Service Responsibilities

- **FastAPI** (`services/api/`): Orchestrator. Routes all UI requests, manages job state in SQLite, calls Label Studio and MLflow APIs.
- **ML Backend** (`services/ml_backend/`): Flask/Gunicorn app. Receives Label Studio predict requests, runs YOLO inference, returns annotations in Label Studio format. Uses a custom `_wsgi.py` (bypasses label-studio-ml's buggy v1/v2 manager).
- **Trainer** (`services/trainer/`): Not a long-running service — FastAPI spawns `train.py` as a subprocess per training job.
- **Label Studio**: External Docker service. FastAPI uses its REST API; UI embeds it via iframe at `/labeling/[id]`.
- **MLflow**: Runs via `gunicorn -b 0.0.0.0:5000 mlflow.server:app` with env vars `MLFLOW_BACKEND_STORE_URI` and `MLFLOW_DEFAULT_ARTIFACT_ROOT`. Uses SQLite backend at `/mlflow/mlflow.db`.

### Key Implementation Details

**Label Studio Auth (v1.23+):** Uses JWT tokens by default. Legacy token auth is disabled until explicitly enabled via `POST /api/jwt/settings`. The FastAPI client (`services/api/services/label_studio.py`) uses `Authorization: Token <key>` header. After first start, legacy tokens must be re-enabled.

**ML Backend v1/v2 bug:** label-studio-ml 1.0.9 has an inconsistency where `predict()` defaults to v2 behavior and `fetch()` defaults to v1, causing "Model is not loaded" errors. The ML backend bypasses the framework entirely with a custom Flask app in `_wsgi.py`.

**Image serving:** FastAPI mounts `/data` as a static directory, making uploaded images accessible at `http://api:8000/data/raw/{dataset_id}/{filename}`. Label Studio and ML Backend fetch images via this URL.

**Training device detection** (`services/api/services/training_runner.py`):
```python
try: import intel_extension_for_pytorch; return 'xpu'  # Intel Arc GPU
except: pass
try: import torch_directml; return torch_directml.device()  # Intel iGPU
except: pass
return 'cpu'
```

**Dataset metadata** is stored as a JSON file at `/data/datasets.json` (not in the database). Training job state is in SQLite at `/data/jobs.db`.

**YOLO task types** map to Label Studio label configs:
- `detect` → `RectangleLabels` → exports as YOLO txt format
- `segment` → `PolygonLabels` → exports as COCO JSON
- `classify` → `Choices` → exports as ImageNet folder structure

### Environment Variables

Copy `.env.example` to `.env`. The most critical variable is `LABEL_STUDIO_API_KEY` — get this after first start (see commands above). The `.env` file is loaded by Docker Compose and all services.

### Volume Mounts

- `./data:/data` — shared between `api`, `ml-backend`, and `trainer` (read-write)
- `./data:/data:ro` — mounted read-only in `label-studio` for local file serving
- `./models:/models` — pretrained YOLO weights and trained model outputs
- `./mlflow:/mlflow` — MLflow SQLite DB and artifacts
- `./data/label_studio:/label-studio/data` — Label Studio internal storage (PostgreSQL is used, not this)
- `postgres_data` — named volume for PostgreSQL persistence
