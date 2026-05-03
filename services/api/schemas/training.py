from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from core.database import JobStatus


class TrainingJobCreate(BaseModel):
    dataset_id: str
    task_type: str
    model_size: str = "yolo11n"
    epochs: int = 100
    class_names: List[str]


class TrainingJobResponse(BaseModel):
    id: str
    dataset_id: str
    task_type: str
    model_size: str
    epochs: int
    status: JobStatus
    mlflow_run_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    error_msg: Optional[str] = None

    model_config = {"from_attributes": True}
