from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class DatasetCreate(BaseModel):
    name: str
    task_type: str  # detect | segment | classify
    class_names: List[str]


class DatasetResponse(BaseModel):
    id: str
    name: str
    task_type: str
    class_names: List[str]
    image_count: int
    ls_project_id: Optional[int] = None
    created_at: datetime
