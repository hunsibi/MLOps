import mlflow
from mlflow.tracking import MlflowClient
from typing import List, Dict, Optional
from core.config import settings

mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
_client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)


def list_experiments() -> List[Dict]:
    experiments = _client.search_experiments()
    return [
        {
            "id": e.experiment_id,
            "name": e.name,
            "artifact_location": e.artifact_location,
            "lifecycle_stage": e.lifecycle_stage,
        }
        for e in experiments
    ]


def list_runs(experiment_id: str) -> List[Dict]:
    runs = _client.search_runs(experiment_ids=[experiment_id], order_by=["start_time DESC"])
    return [_serialize_run(r) for r in runs]


def get_run(run_id: str) -> Optional[Dict]:
    try:
        run = _client.get_run(run_id)
        return _serialize_run(run)
    except Exception:
        return None


def list_registered_models() -> List[Dict]:
    models = _client.search_registered_models()
    return [
        {
            "name": m.name,
            "latest_versions": [
                {
                    "version": v.version,
                    "stage": v.current_stage,
                    "run_id": v.run_id,
                    "status": v.status,
                }
                for v in m.latest_versions
            ],
        }
        for m in models
    ]


def get_model_versions(model_name: str) -> List[Dict]:
    versions = _client.search_model_versions(f"name='{model_name}'")
    return [
        {
            "version": v.version,
            "stage": v.current_stage,
            "run_id": v.run_id,
            "status": v.status,
            "description": v.description,
        }
        for v in versions
    ]


def transition_model_stage(model_name: str, version: str, stage: str) -> Dict:
    _client.transition_model_version_stage(name=model_name, version=version, stage=stage)
    return {"name": model_name, "version": version, "stage": stage}


def _serialize_run(run) -> Dict:
    return {
        "run_id": run.info.run_id,
        "experiment_id": run.info.experiment_id,
        "status": run.info.status,
        "start_time": run.info.start_time,
        "end_time": run.info.end_time,
        "params": dict(run.data.params),
        "metrics": dict(run.data.metrics),
        "tags": dict(run.data.tags),
    }
