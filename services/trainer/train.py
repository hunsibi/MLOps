"""
YOLO v11 학습 스크립트 + MLflow 자동 로깅
FastAPI training_runner.py → ml-backend /train → 여기 실행
"""
import argparse
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import mlflow
import mlflow.pytorch
import requests
from ultralytics import YOLO

from dataset_builder import build_yolo_dataset, build_classification_dataset


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--job-id",       required=True)
    p.add_argument("--dataset-id",   required=True)
    p.add_argument("--task-type",    required=True, choices=["detect", "segment", "classify"])
    p.add_argument("--model-size",   default="yolo11n")
    p.add_argument("--epochs",       type=int, default=100)
    p.add_argument("--device",       default="cpu")
    p.add_argument("--data-root",    default="/data")
    p.add_argument("--mlflow-uri",   default="http://mlflow:5000")
    p.add_argument("--classes",      default="")
    p.add_argument("--ls-project-id", type=int, default=0)
    p.add_argument("--ls-host",      default="http://label-studio:8080")
    p.add_argument("--ls-api-key",   default="")
    return p.parse_args()


def export_from_label_studio(
    ls_host: str,
    ls_api_key: str,
    project_id: int,
    task_type: str,
    export_dir: Path,
) -> None:
    """Label Studio에서 어노테이션을 export하고 export_dir에 압축 해제."""
    export_format = "YOLO" if task_type in ("detect", "segment") else "JSON"
    headers = {"Authorization": f"Token {ls_api_key}"}
    url = f"{ls_host}/api/projects/{project_id}/export?exportType={export_format}"

    print(f"[train] Exporting from Label Studio: project={project_id}, format={export_format}")
    resp = requests.get(url, headers=headers, timeout=180)
    resp.raise_for_status()

    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True)

    content_type = resp.headers.get("content-type", "")

    if "zip" in content_type or export_format == "YOLO":
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name
        try:
            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(export_dir)
            print(f"[train] Export extracted to {export_dir}")
            _print_dir(export_dir)
        finally:
            os.unlink(tmp_path)
    else:
        # JSON (classification)
        out = export_dir / "annotations.json"
        out.write_bytes(resp.content)
        # Label Studio JSON → 내부 포맷 변환
        _convert_ls_json_to_annotations(out)
        print(f"[train] JSON export saved to {out}")


def _convert_ls_json_to_annotations(json_path: Path) -> None:
    """Label Studio JSON export → dataset_builder가 읽는 포맷으로 변환."""
    import json
    raw = json.loads(json_path.read_text())
    items = []
    for task in raw:
        img_url = task.get("data", {}).get("image", "")
        img_name = img_url.rsplit("/", 1)[-1]
        for ann in task.get("annotations", []):
            for r in ann.get("result", []):
                if r.get("type") == "choices":
                    choices = r["value"].get("choices", [])
                    if choices:
                        items.append({"image": img_name, "choice": choices[0]})
                        break
    json_path.write_text(json.dumps(items, ensure_ascii=False, indent=2))


def _print_dir(path: Path, indent: int = 0) -> None:
    for item in sorted(path.iterdir()):
        print("  " * indent + item.name)
        if item.is_dir() and indent < 2:
            _print_dir(item, indent + 1)


def get_model_name(task_type: str, model_size: str) -> str:
    suffix = {"detect": "", "segment": "-seg", "classify": "-cls"}
    return f"{model_size}{suffix[task_type]}.pt"


def main():
    args = parse_args()
    class_names = [c.strip() for c in args.classes.split(",") if c.strip()]
    data_root   = Path(args.data_root)
    export_dir  = data_root / "exports" / args.dataset_id
    split_dir   = data_root / "splits"  / args.job_id
    images_dir  = data_root / "raw"     / args.dataset_id

    # ── 1. Label Studio export ─────────────────────────────────────────────
    if args.ls_project_id and args.ls_api_key:
        export_from_label_studio(
            args.ls_host, args.ls_api_key,
            args.ls_project_id, args.task_type, export_dir,
        )
    else:
        print(f"[train] Skipping LS export (no project_id or api_key). Using existing {export_dir}")

    # ── 2. Ultralytics 내장 MLflow 콜백 비활성화 ──────────────────────────
    # YOLO's built-in callback calls mlflow.set_tracking_uri() internally,
    # which overrides our server URI with a local path and breaks our run.
    try:
        from ultralytics.utils import SETTINGS
        SETTINGS.update({"mlflow": False})
    except Exception:
        pass
    # Belt-and-suspenders: also set the env var ultralytics reads at import time
    os.environ["MLFLOW_TRACKING_URI"] = args.mlflow_uri

    # ── 3. MLflow 설정 ─────────────────────────────────────────────────────
    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment(f"yolo_{args.task_type}")

    with mlflow.start_run(run_name=f"job_{args.job_id}") as run:
        mlflow.log_params({
            "job_id":      args.job_id,
            "dataset_id":  args.dataset_id,
            "task_type":   args.task_type,
            "model_size":  args.model_size,
            "epochs":      args.epochs,
            "device":      args.device,
            "class_names": ",".join(class_names),
        })

        # ── 4. 데이터셋 빌드 ───────────────────────────────────────────────
        print(f"[train] Building dataset: export={export_dir}, images={images_dir}")
        split_dir.mkdir(parents=True, exist_ok=True)

        if args.task_type == "classify":
            yaml_path = build_classification_dataset(
                export_dir, split_dir, class_names, images_dir=images_dir
            )
        else:
            yaml_path = build_yolo_dataset(
                export_dir, split_dir, class_names, images_dir=images_dir
            )
        print(f"[train] Dataset yaml: {yaml_path}")

        # ── 5. YOLO 학습 ──────────────────────────────────────────────────
        model_name = get_model_name(args.task_type, args.model_size)
        model_path = data_root.parent / "models" / "pretrained" / model_name
        if not model_path.exists():
            model_path = model_name  # ultralytics auto-download

        print(f"[train] Starting YOLO: model={model_name}, device={args.device}, epochs={args.epochs}")
        model = YOLO(str(model_path))

        results = model.train(
            data=str(yaml_path),
            epochs=args.epochs,
            device=args.device,
            project=str(data_root / "runs"),
            name=args.job_id,
            exist_ok=True,
            verbose=True,
        )

        # ── 6. 메트릭 로깅 ────────────────────────────────────────────────
        metrics = results.results_dict if hasattr(results, "results_dict") else {}
        for k, v in metrics.items():
            try:
                mlflow.log_metric(
                    k.replace("(", "").replace(")", "").replace("/", "_"),
                    float(v),
                )
            except (TypeError, ValueError):
                pass

        # ── 7. 모델 등록 ──────────────────────────────────────────────────
        best_weights = data_root / "runs" / args.job_id / "weights" / "best.pt"
        if best_weights.exists():
            mlflow.log_artifact(str(best_weights), artifact_path="weights")
            reg_name = f"yolo_{args.task_type}_{args.model_size}"
            # Use MlflowClient directly to avoid newer-client API calls
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            try:
                client.create_registered_model(reg_name)
            except Exception:
                pass  # already exists
            client.create_model_version(
                name=reg_name,
                source=f"{run.info.artifact_uri}/weights",
                run_id=run.info.run_id,
            )
            print(f"[train] Model registered: {reg_name}")

        print(f"[train] Done. run_id={run.info.run_id}")
        print(f"MLFLOW_RUN_ID={run.info.run_id}")


if __name__ == "__main__":
    main()
