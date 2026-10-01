"""Prepare CHV's original split for three-class YOLO training."""

from collections import Counter
from pathlib import Path
import shutil

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "data" / "chv" / "raw" / "CHV_dataset" / "CHV_dataset"
TARGET_DIR = REPO_ROOT / "data" / "chv" / "processed"
SPLITS = {"train.txt": "train", "valid.txt": "val", "test.txt": "test"}
NAMES = ["person", "vest", "helmet"]


def main() -> None:
    source_images = SOURCE_DIR / "images"
    source_labels = SOURCE_DIR / "annotations"
    split_dir = SOURCE_DIR / "data split"
    for directory in (source_images, source_labels, split_dir):
        if not directory.is_dir():
            raise FileNotFoundError(f"CHV folder is missing: {directory}")

    split_images = {}
    seen = set()
    for split_file, split_name in SPLITS.items():
        paths = [line.strip() for line in (split_dir / split_file).read_text().splitlines() if line.strip()]
        if not paths:
            raise ValueError(f"Empty split: {split_file}")
        names = []
        for source_path in paths:
            if not source_path.startswith("CHV_dataset/images/"):
                raise ValueError(f"Unexpected image path in {split_file}: {source_path}")
            filename = Path(source_path).name
            if filename in seen:
                raise ValueError(f"Image repeated across splits: {filename}")
            seen.add(filename)
            names.append(filename)
        split_images[split_name] = names

    original_images = {p.name for p in source_images.glob("*.jpg")}
    if seen != original_images:
        raise ValueError(f"Split mismatch: {len(original_images - seen)} images omitted; {len(seen - original_images)} missing")

    counts = Counter()
    for split_name, filenames in split_images.items():
        images_out = TARGET_DIR / split_name / "images"
        labels_out = TARGET_DIR / split_name / "labels"
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            image = source_images / filename
            label = source_labels / f"{Path(filename).stem}.txt"
            if not label.is_file():
                raise FileNotFoundError(f"Annotation is missing: {label}")
            remapped = []
            for line_number, line in enumerate(label.read_text().splitlines(), 1):
                fields = line.split()
                if not fields:
                    continue
                if len(fields) != 5:
                    raise ValueError(f"Invalid label at {label}:{line_number}")
                old_class = int(fields[0])
                if old_class not in range(6):
                    raise ValueError(f"Invalid class at {label}:{line_number}")
                values = [float(value) for value in fields[1:]]
                if any(value < 0 or value > 1 for value in values) or values[2] <= 0 or values[3] <= 0:
                    raise ValueError(f"Invalid box at {label}:{line_number}")
                new_class = min(old_class, 2)
                remapped.append(" ".join([str(new_class), *fields[1:]]))
                counts[(split_name, NAMES[new_class])] += 1
            shutil.copy2(image, images_out / filename)
            (labels_out / label.name).write_text("\n".join(remapped) + ("\n" if remapped else ""))
        print(f"{split_name}: {len(filenames)} images")

    dataset_yaml = {
        "path": str(TARGET_DIR.resolve()),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "nc": 3,
        "names": NAMES,
    }
    (TARGET_DIR / "dataset.yaml").write_text(yaml.safe_dump(dataset_yaml, sort_keys=False))
    for split_name in split_images:
        print(f"{split_name} instances: " + ", ".join(f"{name}={counts[(split_name, name)]}" for name in NAMES))
    print(f"Ready: {TARGET_DIR / 'dataset.yaml'}")


if __name__ == "__main__":
    main()
