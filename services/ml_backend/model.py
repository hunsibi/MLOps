import os
import io
import logging
import requests
from typing import List, Dict, Optional
from label_studio_ml.model import LabelStudioMLBase
from ultralytics import YOLO
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

MODELS_ROOT = os.environ.get("MODELS_ROOT", "/models")
PRETRAINED_MODEL = os.environ.get("YOLO_PRETRAINED_MODEL", "yolo11n.pt")


class YOLOMLBackend(LabelStudioMLBase):
    """
    Label Studio ML Backend wrapping YOLO v11.
    Supports detection, segmentation, and classification pre-annotation.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = None
        self.task = "detect"

    def setup(self):
        # Production 모델 우선, 없으면 pretrained 사용
        production_path = os.environ.get("YOLO_PRETRAINED_MODEL", "")
        if production_path and os.path.exists(production_path):
            model_path = production_path
        else:
            model_path = os.path.join(MODELS_ROOT, "pretrained", PRETRAINED_MODEL)
            if not os.path.exists(model_path):
                model_path = PRETRAINED_MODEL  # ultralytics auto-download
        self.model = YOLO(model_path)
        self.task = self._detect_task()
        logger.info(f"Loaded YOLO model: {model_path}, task: {self.task}")

    def _detect_task(self) -> str:
        task_map = {"detect": "detect", "segment": "segment", "classify": "classify"}
        return task_map.get(self.model.task, "detect")

    def predict(self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs) -> List[Dict]:
        if self.model is None:
            self.setup()
        predictions = []
        label_config = context.get("label_config", "") if context else ""

        for task in tasks:
            image_url = task["data"].get("image")
            if not image_url:
                predictions.append({"result": [], "score": 0.0})
                continue

            image_data = self._resolve_image_path(image_url)
            if isinstance(image_data, io.BytesIO):
                pil_img = Image.open(image_data)
                image_data.seek(0)
            else:
                pil_img = Image.open(image_data)

            results = self.model.predict(pil_img, conf=0.25, verbose=False)

            if self.task == "detect":
                result = self._build_detection_result(results[0], pil_img)
            elif self.task == "segment":
                result = self._build_segmentation_result(results[0], pil_img)
            else:
                result = self._build_classification_result(results[0])

            predictions.append(result)

        return predictions

    def _resolve_image_path(self, url: str):
        # localhost:8000 is unreachable from inside the container; the same ./data
        # volume is mounted at /data, so read the file directly from disk instead.
        if "localhost:8000/data/" in url:
            from urllib.parse import urlparse
            path = urlparse(url).path  # e.g. /data/raw/{id}/{fn}
            return path
        if url.startswith("http://") or url.startswith("https://"):
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return io.BytesIO(resp.content)
        return url

    def _build_detection_result(self, result, img: Image.Image) -> Dict:
        img_w, img_h = img.size
        annotations = []

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = result.names[cls_id]

            annotations.append({
                "id": f"box_{len(annotations)}",
                "type": "rectanglelabels",
                "value": {
                    "x": x1 / img_w * 100,
                    "y": y1 / img_h * 100,
                    "width": (x2 - x1) / img_w * 100,
                    "height": (y2 - y1) / img_h * 100,
                    "rectanglelabels": [label],
                },
                "score": conf,
                "from_name": "label",
                "to_name": "image",
                "original_width": img_w,
                "original_height": img_h,
            })

        score = float(np.mean([a["score"] for a in annotations])) if annotations else 0.0
        return {"result": annotations, "score": score, "model_version": "yolo11"}

    def _build_segmentation_result(self, result, img: Image.Image) -> Dict:
        img_w, img_h = img.size
        annotations = []

        if result.masks is None:
            return self._build_detection_result(result, img)

        for i, mask in enumerate(result.masks):
            cls_id = int(result.boxes.cls[i])
            conf = float(result.boxes.conf[i])
            label = result.names[cls_id]
            xy = mask.xy[0].tolist()

            points = [[x / img_w * 100, y / img_h * 100] for x, y in xy]

            annotations.append({
                "id": f"polygon_{i}",
                "type": "polygonlabels",
                "value": {
                    "points": points,
                    "polygonlabels": [label],
                },
                "score": conf,
                "from_name": "label",
                "to_name": "image",
                "original_width": img_w,
                "original_height": img_h,
            })

        score = float(np.mean([a["score"] for a in annotations])) if annotations else 0.0
        return {"result": annotations, "score": score}

    def _build_classification_result(self, result) -> Dict:
        probs = result.probs
        top1_cls = int(probs.top1)
        top1_conf = float(probs.top1conf)
        label = result.names[top1_cls]

        return {
            "result": [{
                "id": "cls_0",
                "type": "choices",
                "value": {"choices": [label]},
                "score": top1_conf,
                "from_name": "choice",
                "to_name": "image",
            }],
            "score": top1_conf,
        }
