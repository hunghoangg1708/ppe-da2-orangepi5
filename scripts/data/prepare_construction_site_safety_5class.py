"""Prepare the five PPE classes from Roboflow Construction Site Safety v30."""

from collections import Counter
from pathlib import Path
import shutil

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "construction_site_safety_5class"
SOURCE_DIR = (
    REPO_ROOT
    / "data"
    / "construction_site_safety"
    / "raw"
    / "Construction Site Safety.v30-raw-images_latestversion.yolov8"
)
TARGET_DIR = DATA_DIR / "processed"
CLASS_NAMES = ["Person", "Hardhat", "NO-Hardhat", "Safety Vest", "NO-Safety Vest"]
SPLITS = {"train": "train", "valid": "val", "test": "test"}


def main() -> None:
    source_yaml = SOURCE_DIR / "data.yaml"
    if not source_yaml.is_file():
        raise FileNotFoundError(f"Missing Roboflow export: {source_yaml}")

    source_names = yaml.safe_load(source_yaml.read_text())["names"]
    if not isinstance(source_names, list) or len(source_names) != len(set(source_names)):
        raise ValueError("Expected a unique list of class names in data.yaml")
    missing = set(CLASS_NAMES) - set(source_names)
    if missing:
        raise ValueError(f"Missing PPE classes: {sorted(missing)}")
    class_map = {source_names.index(name): i for i, name in enumerate(CLASS_NAMES)}

    counts = Counter()
    for source_split, target_split in SPLITS.items():
        image_dir = SOURCE_DIR / source_split / "images"
        label_dir = SOURCE_DIR / source_split / "labels"
        if not image_dir.is_dir() or not label_dir.is_dir():
            raise FileNotFoundError(f"Missing {source_split} images or labels")

        out_images = TARGET_DIR / target_split / "images"
        out_labels = TARGET_DIR / target_split / "labels"
        out_images.mkdir(parents=True, exist_ok=True)
        out_labels.mkdir(parents=True, exist_ok=True)

        images = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        if not images:
            raise ValueError(f"No images found in {image_dir}")
        for image in images:
            label = label_dir / f"{image.stem}.txt"
            if not label.is_file():
                raise FileNotFoundError(f"Missing label for {image.name}: {label}")
            remapped = []
            for line_number, line in enumerate(label.read_text().splitlines(), 1):
                fields = line.split()
                if not fields:
                    continue
                if len(fields) != 5:
                    raise ValueError(f"Invalid YOLO label at {label}:{line_number}")
                old_id = int(fields[0])
                if old_id < 0 or old_id >= len(source_names):
                    raise ValueError(f"Invalid class ID at {label}:{line_number}")
                if old_id in class_map:
                    remapped.append(" ".join([str(class_map[old_id]), *fields[1:]]))
                    counts[(target_split, CLASS_NAMES[class_map[old_id]])] += 1

            shutil.copy2(image, out_images / image.name)
            (out_labels / label.name).write_text("\n".join(remapped) + ("\n" if remapped else ""))
        print(f"{target_split}: {len(images)} images")

    dataset_yaml = {
        "path": str(TARGET_DIR.resolve()),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "nc": len(CLASS_NAMES),
        "names": CLASS_NAMES,
    }
    (TARGET_DIR / "dataset.yaml").write_text(yaml.safe_dump(dataset_yaml, sort_keys=False))
    for split in ("train", "val", "test"):
        print(f"{split} instances: " + ", ".join(f"{name}={counts[(split, name)]}" for name in CLASS_NAMES))
    print(f"Ready: {TARGET_DIR / 'dataset.yaml'}")


if __name__ == "__main__":
    main()
