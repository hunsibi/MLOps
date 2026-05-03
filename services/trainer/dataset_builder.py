"""
Label Studio export → YOLO-format dataset 변환 + train/val/test split
"""
import os
import json
import shutil
import random
from pathlib import Path
from typing import List, Tuple


def build_yolo_dataset(
    export_dir: Path,
    output_dir: Path,
    class_names: List[str],
    splits: Tuple[float, float, float] = (0.7, 0.2, 0.1),
    seed: int = 42,
) -> Path:
    """
    export_dir: Label Studio YOLO export 압축 해제 경로
    output_dir: 최종 데이터셋 저장 경로
    반환: dataset.yaml 경로
    """
    random.seed(seed)

    images = sorted(export_dir.rglob("*.jpg")) + sorted(export_dir.rglob("*.png"))
    random.shuffle(images)

    n = len(images)
    n_train = int(n * splits[0])
    n_val = int(n * splits[1])

    split_map = (
        [("train", img) for img in images[:n_train]]
        + [("val", img) for img in images[n_train : n_train + n_val]]
        + [("test", img) for img in images[n_train + n_val :]]
    )

    for split, img_path in split_map:
        img_dest = output_dir / "images" / split / img_path.name
        lbl_src = (export_dir / "labels" / img_path.stem).with_suffix(".txt")
        lbl_dest = output_dir / "labels" / split / img_path.stem + ".txt"

        img_dest.parent.mkdir(parents=True, exist_ok=True)
        lbl_dest.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(img_path, img_dest)
        if lbl_src.exists():
            shutil.copy2(lbl_src, lbl_dest)
        else:
            lbl_dest.touch()

    yaml_path = output_dir / "dataset.yaml"
    yaml_content = {
        "path": str(output_dir),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": len(class_names),
        "names": class_names,
    }
    import yaml
    yaml_path.write_text(yaml.dump(yaml_content, allow_unicode=True))

    return yaml_path


def build_classification_dataset(
    export_dir: Path,
    output_dir: Path,
    class_names: List[str],
    splits: Tuple[float, float, float] = (0.7, 0.2, 0.1),
    seed: int = 42,
) -> Path:
    random.seed(seed)
    annotations_file = export_dir / "annotations.json"
    if not annotations_file.exists():
        raise FileNotFoundError("annotations.json not found in export")

    data = json.loads(annotations_file.read_text())
    items = [(d["image"], d["choice"]) for d in data if "choice" in d]
    random.shuffle(items)

    n = len(items)
    n_train = int(n * splits[0])
    n_val = int(n * splits[1])

    split_map = (
        [("train", *item) for item in items[:n_train]]
        + [("val", *item) for item in items[n_train : n_train + n_val]]
        + [("test", *item) for item in items[n_train + n_val :]]
    )

    for split, img_path, label in split_map:
        src = export_dir / img_path
        dest = output_dir / split / label / Path(img_path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dest)

    yaml_path = output_dir / "dataset.yaml"
    import yaml
    yaml_path.write_text(yaml.dump({"path": str(output_dir), "names": class_names}, allow_unicode=True))
    return yaml_path
