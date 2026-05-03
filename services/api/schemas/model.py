from pydantic import BaseModel
from typing import List, Optional


class ModelVersion(BaseModel):
    version: str
    stage: str
    run_id: str
    status: str
    description: Optional[str] = None


class RegisteredModel(BaseModel):
    name: str
    latest_versions: List[ModelVersion]


class StageTransition(BaseModel):
    version: str
    stage: str  # Staging | Production | Archived
