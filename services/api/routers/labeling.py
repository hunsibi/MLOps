from fastapi import APIRouter, Request, HTTPException
from services.label_studio import ls_client

router = APIRouter(prefix="/api/v1/labeling", tags=["labeling"])


@router.get("/projects")
async def list_projects():
    return await ls_client.list_projects()


@router.get("/projects/{project_id}/stats")
async def get_project_stats(project_id: int):
    return await ls_client.get_project_stats(project_id)


@router.post("/projects/{project_id}/webhook")
async def setup_webhook(project_id: int, webhook_url: str):
    return await ls_client.setup_webhook(project_id, webhook_url)


@router.post("/webhooks/complete")
async def handle_annotation_webhook(request: Request):
    payload = await request.json()
    action = payload.get("action", "")
    task = payload.get("task", {})
    annotation = payload.get("annotation", {})
    project_id = payload.get("project", {}).get("id")

    # TODO: trigger active learning pipeline on annotation completion
    return {"received": True, "action": action, "project_id": project_id}
