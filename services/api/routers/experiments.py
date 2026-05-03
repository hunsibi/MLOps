from fastapi import APIRouter, HTTPException
from typing import List
import services.mlflow_service as mlflow_svc

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


@router.get("/")
def list_experiments():
    return mlflow_svc.list_experiments()


@router.get("/{experiment_id}/runs")
def list_runs(experiment_id: str):
    return mlflow_svc.list_runs(experiment_id)


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    run = mlflow_svc.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
