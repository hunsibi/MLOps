from fastapi import APIRouter, HTTPException
from typing import List
from schemas.model import RegisteredModel, ModelVersion, StageTransition
import services.mlflow_service as mlflow_svc

router = APIRouter(prefix="/api/v1/models", tags=["models"])


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
def transition_stage(model_name: str, body: StageTransition):
    return mlflow_svc.transition_model_stage(model_name, body.version, body.stage)
