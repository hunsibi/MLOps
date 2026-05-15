import json
import time
import logging
import httpx
from pathlib import Path
from core.database import SessionLocal, TrainingJob, JobStatus
from core.config import settings

logger = logging.getLogger(__name__)

ML_BACKEND = settings.ml_backend_url.rstrip("/")


def detect_device() -> str:
    try:
        import torch
        import intel_extension_for_pytorch as ipex  # noqa: F401
        if torch.xpu.is_available():
            return "xpu"
    except (ImportError, AttributeError):
        pass
    try:
        import torch_directml
        return str(torch_directml.device())
    except ImportError:
        pass
    return "cpu"


def start_training_job(
    job_id: str,
    dataset_id: str,
    task_type: str,
    model_size: str,
    epochs: int,
    class_names: list,
) -> None:
    log_path = str(Path(settings.data_root) / "logs" / f"{job_id}.log")
    db = SessionLocal()

    try:
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            job.status = JobStatus.running
            job.log_path = log_path
            db.commit()

        # Look up ls_project_id from datasets.json
        datasets_meta_path = Path(settings.data_root) / "datasets.json"
        ls_project_id = 0
        if datasets_meta_path.exists():
            meta = json.loads(datasets_meta_path.read_text())
            ds = meta.get(dataset_id, {})
            ls_project_id = ds.get("ls_project_id", 0)

        device = detect_device()
        payload = {
            "job_id":        job_id,
            "dataset_id":    dataset_id,
            "task_type":     task_type,
            "model_size":    model_size,
            "epochs":        epochs,
            "device":        device,
            "data_root":     settings.data_root,
            "mlflow_uri":    settings.mlflow_tracking_uri,
            "classes":       ",".join(class_names),
            "ls_project_id": ls_project_id,
            "ls_host":       settings.label_studio_host,
            "ls_api_key":    settings.label_studio_api_key,
        }

        resp = httpx.post(f"{ML_BACKEND}/train", json=payload, timeout=30)
        resp.raise_for_status()

        mlflow_run_id = None
        while True:
            time.sleep(15)
            try:
                status_resp = httpx.get(
                    f"{ML_BACKEND}/train/status/{job_id}", timeout=10
                )
                status_resp.raise_for_status()
                info = status_resp.json()
            except Exception:
                continue

            if info.get("status") in ("completed", "failed"):
                final = info["status"]
                rc = info.get("returncode", -1)
                mlflow_run_id = info.get("mlflow_run_id")
                break

        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            job.status = JobStatus.completed if final == "completed" else JobStatus.failed
            job.mlflow_run_id = mlflow_run_id
            if final == "failed":
                job.error_msg = f"Process exited with code {rc}"
            db.commit()

    except Exception as e:
        logger.error(f"Training job {job_id} dispatch failed: {e}")
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            job.status = JobStatus.failed
            job.error_msg = str(e)
            db.commit()
    finally:
        db.close()
