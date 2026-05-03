import uuid
import json
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from core.config import settings
from services.label_studio import ls_client

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])

DATASETS_META = Path(settings.data_root) / "datasets.json"


def _load_meta() -> dict:
    if DATASETS_META.exists():
        return json.loads(DATASETS_META.read_text())
    return {}


def _save_meta(meta: dict):
    DATASETS_META.parent.mkdir(parents=True, exist_ok=True)
    DATASETS_META.write_text(json.dumps(meta, indent=2, default=str))


@router.post("/upload")
async def upload_dataset(
    name: str = Form(...),
    task_type: str = Form(...),
    class_names: str = Form(...),
    files: List[UploadFile] = File(...),
):
    dataset_id = str(uuid.uuid4())[:8]
    class_list = [c.strip() for c in class_names.split(",")]
    raw_dir = Path(settings.data_root) / "raw" / dataset_id
    raw_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for f in files:
        dest = raw_dir / f.filename
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(f.filename)

    project = await ls_client.create_project(name, task_type, class_list)
    project_id = project["id"]

    image_urls = [f"http://api:8000/data/raw/{dataset_id}/{fn}" for fn in saved]
    await ls_client.import_tasks(project_id, image_urls)

    meta = _load_meta()
    from datetime import datetime, timezone
    meta[dataset_id] = {
        "id": dataset_id,
        "name": name,
        "task_type": task_type,
        "class_names": class_list,
        "image_count": len(saved),
        "ls_project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_meta(meta)

    return meta[dataset_id]


@router.get("/")
async def list_datasets():
    return list(_load_meta().values())


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    meta = _load_meta()
    if dataset_id not in meta:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return meta[dataset_id]


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    meta = _load_meta()
    if dataset_id not in meta:
        raise HTTPException(status_code=404, detail="Dataset not found")
    raw_dir = Path(settings.data_root) / "raw" / dataset_id
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    del meta[dataset_id]
    _save_meta(meta)
    return {"deleted": dataset_id}
