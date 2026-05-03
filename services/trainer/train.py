"""
YOLO v11 학습 스크립트 + MLflow 자동 로깅
FastAPI training_runner.py가 subprocess로 실행함
"""
import argparse
import os
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path

import mlflow
import mlflow.pytorch
from ultralytics import YOLO

from dataset_builder import build_yolo_dataset, build_classification_dataset


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--job-id", required=True)
    p.add_argument("--dataset-id", required=True)
    p.add_argument("--task-type", required=True, choices=["detect", "segment", "classify"])
    p.add_argument("--model-size", default="yolo11n")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--device", default="cpu")
    p.add_argument("--data-root", default="/data")
    p.add_argument("--mlflow-uri", default="http://localhost:5000")
    p.add_argument("--classes", default="")
    return p.parse_args()


def get_model_name(task_type: str, model_size: str) -> str:
    suffix_map = {"detect": "", "segment": "-seg", "classify": "-cls"}
    return f"{model_size}{suffix_map[task_type]}.pt"


def main():
    args = parse_args()
    class_names = [c.strip() for c in args.classes.split(",") if c.strip()]
    data_root = Path(args.data_root)
    export_dir = data_root / "exports" / args.dataset_id
    split_dir = data_root / "splits" / args.job_id

    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment(f"yolo_{args.task_type}")

    with mlflow.start_run(run_name=f"job_{args.job_id}") as run:
        mlflow.log_params({
            "job_id": args.job_id,
            "dataset_id": args.dataset_id,
            "task_type": args.task_type,
            "model_size": args.model_size,
            "epochs": args.epochs,
            "device": args.device,
            "class_names": ",".join(class_names),
        })

        # 1. 데이터셋 빌드
        print(f"[train] Building dataset from {export_dir}")
        split_dir.mkdir(parents=True, exist_ok=True)

        if args.task_type == "classify":
            yaml_path = build_classification_dataset(export_dir, split_dir, class_names)
        else:
            yaml_path = build_yolo_dataset(export_dir, split_dir, class_names)

        # 2. YOLO 학습
        model_name = get_model_name(args.task_type, args.model_size)
        model_path = data_root.parent / "models" / "pretrained" / model_name
        if not model_path.exists():
            model_path = model_name  # ultralytics auto-download

        print(f"[train] Starting YOLO training: model={model_name}, device={args.device}")
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

        # 3. 메트릭 로깅
        metrics = results.results_dict if hasattr(results, "results_dict") else {}
        for k, v in metrics.items():
            try:
                mlflow.log_metric(k.replace("(", "").replace(")", "").replace("/", "_"), float(v))
            except (TypeError, ValueError):
                pass

        # 4. 모델 아티팩트 등록
        best_weights = Path(str(data_root / "runs" / args.job_id)) / "weights" / "best.pt"
        if best_weights.exists():
            mlflow.log_artifact(str(best_weights), artifact_path="weights")
            model_uri = f"runs:/{run.info.run_id}/weights"
            mlflow.register_model(model_uri, f"yolo_{args.task_type}_{args.model_size}")
            print(f"[train] Model registered: yolo_{args.task_type}_{args.model_size}")

        print(f"[train] Done. run_id={run.info.run_id}")
        print(f"MLFLOW_RUN_ID={run.info.run_id}")


if __name__ == "__main__":
    main()
