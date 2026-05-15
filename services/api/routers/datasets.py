import uuid
import json
import re
import shutil
from datetime import datetime, timezone
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


def _infer_task_type(label_config: str) -> str:
    if "RectangleLabels" in label_config:
        return "detect"
    if "PolygonLabels" in label_config:
        return "segment"
    if "Choices" in label_config:
        return "classify"
    return "detect"


def _extract_class_names(label_config: str) -> List[str]:
    labels = re.findall(r'<(?:Label|Choice)\s+value="([^"]+)"', label_config)
    return labels if labels else ["unknown"]


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
        # Prevent path traversal: take only the filename component
        safe_name = Path(f.filename).name
        dest = raw_dir / safe_name
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(safe_name)

    try:
        project = await ls_client.create_project(name, task_type, class_list)
        project_id = project["id"]

        # Use localhost:8000 so the browser can load images directly from FastAPI's
        # static file mount. FastAPI has wide-open CORS so Label Studio can fetch them.
        image_urls = [f"http://localhost:8000/data/raw/{dataset_id}/{fn}" for fn in saved]
        await ls_client.import_tasks(project_id, image_urls)
    except Exception as e:
        shutil.rmtree(raw_dir, ignore_errors=True)
        raise HTTPException(status_code=502, detail=f"Label Studio error: {e}")

    meta = _load_meta()
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


@router.post("/sync")
async def sync_from_label_studio():
    """Import Label Studio projects that aren't registered in datasets.json yet."""
    try:
        projects = await ls_client.list_projects()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Label Studio unreachable: {e}")

    meta = _load_meta()
    known_ls_ids = {str(v["ls_project_id"]) for v in meta.values() if v.get("ls_project_id")}

    added = []
    for project in projects:
        if str(project["id"]) in known_ls_ids:
            continue
        label_config = project.get("label_config", "")
        task_type = _infer_task_type(label_config)
        class_names = _extract_class_names(label_config)
        dataset_id = str(uuid.uuid4())[:8]
        meta[dataset_id] = {
            "id": dataset_id,
            "name": project["title"],
            "task_type": task_type,
            "class_names": class_names,
            "image_count": project.get("task_number", 0),
            "ls_project_id": project["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        added.append(dataset_id)

    _save_meta(meta)
    return {"synced": len(added), "datasets": [meta[i] for i in added]}


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
