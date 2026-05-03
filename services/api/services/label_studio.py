import httpx
from typing import List, Dict, Optional
from core.config import settings

TASK_TEMPLATES = {
    "detect": """<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    {labels}
  </RectangleLabels>
</View>""",
    "segment": """<View>
  <Image name="image" value="$image"/>
  <PolygonLabels name="label" toName="image">
    {labels}
  </PolygonLabels>
</View>""",
    "classify": """<View>
  <Image name="image" value="$image"/>
  <Choices name="choice" toName="image" showInLine="true">
    {labels}
  </Choices>
</View>""",
}


def _label_tags(class_names: List[str], task: str) -> str:
    tag = "Label" if task in ("detect", "segment") else "Choice"
    return "\n    ".join(f'<{tag} value="{c}"/>' for c in class_names)


class LabelStudioClient:
    def __init__(self):
        self.base = settings.label_studio_host.rstrip("/")
        self.headers = {"Authorization": f"Token {settings.label_studio_api_key}"}

    def _url(self, path: str) -> str:
        return f"{self.base}/api/{path.lstrip('/')}"

    async def create_project(self, name: str, task_type: str, class_names: List[str]) -> Dict:
        template = TASK_TEMPLATES[task_type]
        label_config = template.format(labels=_label_tags(class_names, task_type))
        payload = {"title": name, "label_config": label_config}
        async with httpx.AsyncClient() as client:
            r = await client.post(self._url("projects"), json=payload, headers=self.headers, timeout=30)
            r.raise_for_status()
            return r.json()

    async def list_projects(self) -> List[Dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(self._url("projects"), headers=self.headers, timeout=30)
            r.raise_for_status()
            return r.json().get("results", [])

    async def import_tasks(self, project_id: int, image_urls: List[str]) -> Dict:
        tasks = [{"data": {"image": url}} for url in image_urls]
        async with httpx.AsyncClient() as client:
            r = await client.post(
                self._url(f"projects/{project_id}/import"),
                json=tasks,
                headers=self.headers,
                timeout=60,
            )
            r.raise_for_status()
            return r.json()

    async def get_project_stats(self, project_id: int) -> Dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(self._url(f"projects/{project_id}`"), headers=self.headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            return {
                "total": data.get("task_number", 0),
                "completed": data.get("num_tasks_with_annotations", 0),
                "skipped": data.get("skipped_annotations_number", 0),
            }

    async def export_annotations(self, project_id: int, export_format: str = "YOLO") -> bytes:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.get(
                self._url(f"projects/{project_id}/export"),
                params={"exportType": export_format},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.content

    async def setup_webhook(self, project_id: int, webhook_url: str) -> Dict:
        payload = {
            "project": project_id,
            "url": webhook_url,
            "send_payload": True,
            "actions": ["ANNOTATION_CREATED", "ANNOTATION_UPDATED"],
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(self._url("webhooks"), json=payload, headers=self.headers, timeout=30)
            r.raise_for_status()
            return r.json()


ls_client = LabelStudioClient()
