import shutil
import logging
import httpx
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from schemas.model import RegisteredModel, ModelVersion, StageTransition
from core.database import get_db, TrainingJob
from core.config import settings
import services.mlflow_service as mlflow_svc

router = APIRouter(prefix="/api/v1/models", tags=["models"])
logger = logging.getLogger(__name__)

PRODUCTION_MODEL_PATH = Path(settings.models_root) / "production" / "best.pt"


def _export_to_production(run_id: str, db: Session) -> bool:
    """run_id에 해당하는 best.pt를 production 경로로 복사. 성공 여부 반환."""
    job = db.query(TrainingJob).filter(TrainingJob.mlflow_run_id == run_id).first()
    if not job:
        logger.warning(f"No job found for run_id={run_id}")
        return False

    src = Path(settings.data_root) / "runs" / job.id / "weights" / "best.pt"
    if not src.exists():
        logger.warning(f"best.pt not found at {src}")
        return False

    PRODUCTION_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, PRODUCTION_MODEL_PATH)
    logger.info(f"Exported {src} → {PRODUCTION_MODEL_PATH}")

    # ML Backend 모델 재로드
    try:
        ml_backend = settings.ml_backend_url.rstrip("/")
        httpx.post(f"{ml_backend}/reload", timeout=10)
        logger.info("ML Backend reload triggered")
    except Exception as e:
        logger.warning(f"ML Backend reload failed (non-critical): {e}")

    return True


@router.get("/", response_model=List[RegisteredModel])
def list_models():
    return mlflow_svc.list_registered_models()


@router.get("/{model_name}/versions", response_model=List[ModelVersion])
def get_model_versions(model_name: str):
    versions = mlflow_svc.get_model_versions(model_name)
    if not versions:
        raise HTTPException(status_code=404, detail="Model not found")
    return versions


@router.post("/{model_name}/stage")
def transition_stage(model_name: str, body: StageTransition, db: Session = Depends(get_db)):
    result = mlflow_svc.transition_model_stage(model_name, body.version, body.stage)

    if body.stage == "Production":
        version_info = mlflow_svc.get_model_versions(model_name)
        run_id = next((v["run_id"] for v in version_info if v["version"] == body.version), None)
        if run_id:
            exported = _export_to_production(run_id, db)
            result["exported"] = exported

    return result
