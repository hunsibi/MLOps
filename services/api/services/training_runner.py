import subprocess
import sys
import os
import uuid
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from core.database import TrainingJob, JobStatus
from core.config import settings

logger = logging.getLogger(__name__)

TRAINER_SCRIPT = Path(__file__).parent.parent.parent / "trainer" / "train.py"


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
    db: Session,
    job_id: str,
    dataset_id: str,
    task_type: str,
    model_size: str,
    epochs: int,
    class_names: list,
) -> None:
    log_dir = Path(settings.data_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = str(log_dir / f"{job_id}.log")

    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if job:
        job.status = JobStatus.running
        job.log_path = log_path
        db.commit()

    device = detect_device()
    cmd = [
        sys.executable,
        str(TRAINER_SCRIPT),
        "--job-id", job_id,
        "--dataset-id", dataset_id,
        "--task-type", task_type,
        "--model-size", model_size,
        "--epochs", str(epochs),
        "--device", device,
        "--data-root", settings.data_root,
        "--mlflow-uri", settings.mlflow_tracking_uri,
        "--classes", ",".join(class_names),
    ]

    try:
        with open(log_path, "w") as log_file:
            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
        proc.wait()

        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            job.status = JobStatus.completed if proc.returncode == 0 else JobStatus.failed
            if proc.returncode != 0:
                job.error_msg = f"Process exited with code {proc.returncode}"
            db.commit()

    except Exception as e:
        logger.error(f"Training job {job_id} failed: {e}")
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        if job:
            job.status = JobStatus.failed
            job.error_msg = str(e)
            db.commit()
