"""
Label Studio export → YOLO-format dataset 변환 + train/val/test split
"""
import json
import os
import random
import shutil
from pathlib import Path
from typing import List, Optional, Tuple


def build_yolo_dataset(
    export_dir: Path,
    output_dir: Path,
    class_names: List[str],
    images_dir: Optional[Path] = None,
    splits: Tuple[float, float, float] = (0.7, 0.2, 0.1),
    seed: int = 42,
) -> Path:
    """
    export_dir   : Label Studio YOLO export 압축 해제 경로 (labels/*.txt)
    output_dir   : 최종 데이터셋 저장 경로
    images_dir   : 원본 이미지 경로 (없으면 export_dir에서 탐색)
    반환          : dataset.yaml 경로
    """
    random.seed(seed)

    # ── 이미지 수집 ────────────────────────────────────────────────────────────
    exts = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")
    images: List[Path] = []
    search_root = images_dir if (images_dir and images_dir.exists()) else export_dir
    for ext in exts:
        images.extend(search_root.rglob(ext))
    images = sorted(set(images))
    random.shuffle(images)

    if not images:
        raise ValueError(f"No images found in {search_root}")

    # ── 라벨 파일 인덱스 (stem → Path) ────────────────────────────────────────
    # Label Studio YOLO export names files as "{hash}__{original_stem}.txt".
    # Index both the full stem and the original stem so lookups by image filename work.
    label_index: dict[str, Path] = {}
    for txt in export_dir.rglob("*.txt"):
        if txt.name == "classes.txt":
            continue
        label_index[txt.stem] = txt
        if "__" in txt.stem:
            original = txt.stem.split("__", 1)[1]
            label_index[original] = txt

    # ── split 계산 (val 최소 1장 보장) ────────────────────────────────────────
    n = len(images)
    if n == 1:
        assignments = ["train", "val", "val"][:n] + ["train"] * max(0, n - 3)
        # re-use the single image for train and val
        split_map = [("train", images[0]), ("val", images[0])]
    elif n == 2:
        split_map = [("train", images[0]), ("val", images[1])]
    else:
        n_val   = max(1, round(n * splits[1]))
        n_test  = max(0, round(n * splits[2])) if n >= 4 else 0
        n_train = n - n_val - n_test
        names   = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
        split_map = list(zip(names, images))

    # ── 파일 복사 ──────────────────────────────────────────────────────────────
    for split, img_path in split_map:
        img_dest = output_dir / "images" / split / img_path.name
        lbl_src  = label_index.get(img_path.stem)
        lbl_dest = output_dir / "labels" / split / (img_path.stem + ".txt")

        img_dest.parent.mkdir(parents=True, exist_ok=True)
        lbl_dest.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(img_path, img_dest)
        if lbl_src and lbl_src.exists():
            shutil.copy2(lbl_src, lbl_dest)
        else:
            lbl_dest.touch()  # 어노테이션 없는 이미지 → 빈 label 파일

    # YOLO는 val 디렉터리가 항상 존재해야 함
    for split in ("train", "val", "test"):
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    # ── dataset.yaml 생성 ──────────────────────────────────────────────────────
    import yaml
    yaml_path = output_dir / "dataset.yaml"
    yaml_path.write_text(yaml.dump({
        "path":  str(output_dir),
        "train": "images/train",
        "val":   "images/val",
        "test":  "images/test",
        "nc":    len(class_names),
        "names": class_names,
    }, allow_unicode=True))

    return yaml_path


def build_classification_dataset(
    export_dir: Path,
    output_dir: Path,
    class_names: List[str],
    images_dir: Optional[Path] = None,
    splits: Tuple[float, float, float] = (0.7, 0.2, 0.1),
    seed: int = 42,
) -> Path:
    random.seed(seed)

    annotations_file = export_dir / "annotations.json"
    if not annotations_file.exists():
        raise FileNotFoundError(f"annotations.json not found in {export_dir}")

    data = json.loads(annotations_file.read_text())
    items = [(d["image"], d["choice"]) for d in data if "choice" in d]
    random.shuffle(items)

    n = len(items)
    if n == 0:
        raise ValueError("No annotated classification items found")

    if n == 1:
        split_map = [("train", *items[0]), ("val", *items[0])]
    elif n == 2:
        split_map = [("train", *items[0]), ("val", *items[1])]
    else:
        n_val   = max(1, round(n * splits[1]))
        n_test  = max(0, round(n * splits[2])) if n >= 4 else 0
        n_train = n - n_val - n_test
        names   = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
        split_map = [(s, img, lbl) for s, (img, lbl) in zip(names, items)]

    img_root = images_dir if (images_dir and images_dir.exists()) else export_dir

    for split, img_path, label in split_map:
        src  = img_root / img_path if not Path(img_path).is_absolute() else Path(img_path)
        dest = output_dir / split / label / Path(img_path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dest)

    import yaml
    yaml_path = output_dir / "dataset.yaml"
    yaml_path.write_text(yaml.dump({
        "path":  str(output_dir),
        "names": class_names,
    }, allow_unicode=True))
    return yaml_path
