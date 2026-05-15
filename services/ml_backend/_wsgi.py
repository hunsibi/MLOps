"""
Simple Flask ML backend for Label Studio, bypassing label-studio-ml's
buggy v1/v2 manager to serve YOLO predictions directly.
Also hosts the training endpoint so the API can dispatch train jobs here
(ml-backend already has ultralytics + torch installed).
"""
import os
import sys
import logging
import io
import subprocess
import threading
import requests
from flask import Flask, request, jsonify
from model import YOLOMLBackend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_model = None
PRODUCTION_MODEL_PATH = "/models/production/best.pt"

# In-memory store for training job statuses
_train_jobs: dict = {}
_train_lock = threading.Lock()


def get_model():
    global _model
    if _model is None:
        _model = YOLOMLBackend()
        # Production 모델이 있으면 우선 사용
        if os.path.exists(PRODUCTION_MODEL_PATH):
            os.environ["YOLO_PRETRAINED_MODEL"] = PRODUCTION_MODEL_PATH
            logger.info(f"Loading production model: {PRODUCTION_MODEL_PATH}")
        _model.setup()
        logger.info("YOLO model initialized")
    return _model


# ── Prediction endpoints ────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "model_dir": None, "v2": False})


@app.route("/setup", methods=["POST"])
def setup():
    model = get_model()
    loaded = os.environ.get("YOLO_PRETRAINED_MODEL", "yolo11n.pt")
    return jsonify({"model_version": "yolo11n", "loaded_model": loaded})


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json or {}
        tasks = data.get("tasks", [])
        label_config = data.get("label_config", "")
        model = get_model()
        predictions = model.predict(tasks, context={"label_config": label_config})
        return jsonify({"results": predictions, "model_version": "yolo11n"})
    except Exception as e:
        logger.exception("Prediction failed")
        return jsonify({"detail": str(e), "status": 500}), 500


@app.route("/versions", methods=["GET"])
def versions():
    return jsonify({"versions": ["yolo11n"]})


@app.route("/webhook", methods=["POST"])
def webhook():
    return jsonify({"status": "ok"})


@app.route("/reload", methods=["POST"])
def reload_model():
    """Production 모델로 교체 후 ML Backend에 /reload를 호출하면 즉시 적용."""
    global _model
    _model = None
    logger.info("Model reset — will reload on next predict request")
    new_path = PRODUCTION_MODEL_PATH if os.path.exists(PRODUCTION_MODEL_PATH) else "pretrained"
    return jsonify({"status": "reloading", "model": new_path})


# ── Training endpoints ──────────────────────────────────────────────────────

def _run_training(job_id: str, cmd: list, log_path: str):
    """Background thread: runs train.py and updates job status."""
    with _train_lock:
        _train_jobs[job_id] = {"status": "running", "returncode": None, "mlflow_run_id": None}

    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w") as log_file:
            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
        proc.wait()

        # Parse MLflow run ID from log output (train.py prints MLFLOW_RUN_ID=<id>)
        mlflow_run_id = None
        try:
            with open(log_path, "r") as f:
                for line in f:
                    if "MLFLOW_RUN_ID=" in line:
                        mlflow_run_id = line.strip().split("MLFLOW_RUN_ID=", 1)[-1]
                        break
        except Exception:
            pass

        status = "completed" if proc.returncode == 0 else "failed"
        with _train_lock:
            _train_jobs[job_id] = {
                "status": status,
                "returncode": proc.returncode,
                "mlflow_run_id": mlflow_run_id,
            }
        logger.info(f"Training job {job_id} finished with status={status}, mlflow_run_id={mlflow_run_id}")
    except Exception as e:
        logger.exception(f"Training job {job_id} crashed")
        with _train_lock:
            _train_jobs[job_id] = {"status": "failed", "returncode": -1, "error": str(e), "mlflow_run_id": None}


@app.route("/train", methods=["POST"])
def train():
    data = request.json or {}
    job_id        = data.get("job_id")
    dataset_id    = data.get("dataset_id")
    task_type     = data.get("task_type", "detect")
    model_size    = data.get("model_size", "yolo11n")
    epochs        = str(data.get("epochs", 100))
    device        = data.get("device", "cpu")
    data_root     = data.get("data_root", "/data")
    mlflow_uri    = data.get("mlflow_uri", "http://mlflow:5000")
    classes       = data.get("classes", "")
    ls_project_id = str(data.get("ls_project_id", "0"))
    ls_host       = data.get("ls_host", os.environ.get("LABEL_STUDIO_HOST", "http://label-studio:8080"))
    ls_api_key    = data.get("ls_api_key", os.environ.get("LABEL_STUDIO_API_KEY", ""))

    if not job_id or not dataset_id:
        return jsonify({"error": "job_id and dataset_id are required"}), 400

    log_path = os.path.join(data_root, "logs", f"{job_id}.log")

    cmd = [
        sys.executable, "/trainer/train.py",
        "--job-id",        job_id,
        "--dataset-id",    dataset_id,
        "--task-type",     task_type,
        "--model-size",    model_size,
        "--epochs",        epochs,
        "--device",        device,
        "--data-root",     data_root,
        "--mlflow-uri",    mlflow_uri,
        "--classes",       classes,
        "--ls-project-id", ls_project_id,
        "--ls-host",       ls_host,
        "--ls-api-key",    ls_api_key,
    ]

    thread = threading.Thread(
        target=_run_training, args=(job_id, cmd, log_path), daemon=True
    )
    thread.start()

    return jsonify({"started": True, "job_id": job_id, "log_path": log_path})


@app.route("/train/status/<job_id>", methods=["GET"])
def train_status(job_id):
    with _train_lock:
        info = _train_jobs.get(job_id)
    if info is None:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(info)
