"""Validate the Huang–Cheng export and create a local Ultralytics data YAML."""

from collections import Counter
import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "Huang-Cheng"
TARGET = ROOT / "data" / "huang_cheng" / "processed"
NAMES = ["Helmet", "NoHelmet", "NoVest", "Vest"]
SPLITS = {"train": 1829, "valid": 457}


def check_split(split: str, seen_hashes: dict[str, str]) -> Counter[int]:
    images_dir = SOURCE / split / "images"
    labels_dir = SOURCE / split / "labels"
    if not images_dir.is_dir() or not labels_dir.is_dir():
        raise FileNotFoundError(f"Missing images or labels for {split}: {SOURCE / split}")

    images = sorted(p for p in images_dir.iterdir() if p.is_file())
    labels = {p.stem: p for p in labels_dir.glob("*.txt")}
    if len(images) != SPLITS[split] or len(labels) != len(images):
        raise ValueError(f"Unexpected {split} size: {len(images)} images, {len(labels)} labels")
    if {p.stem for p in images} != set(labels):
        raise ValueError(f"Image/label filenames do not match in {split}")

    counts: Counter[int] = Counter()
    for image in images:
        if image.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValueError(f"Unsupported image: {image}")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest in seen_hashes:
            raise ValueError(f"Exact image duplicate: {seen_hashes[digest]} and {image}")
        seen_hashes[digest] = str(image)

        label = labels[image.stem]
        lines = label.read_text().splitlines()
        if not lines:
            raise ValueError(f"Empty label: {label}")
        for line_number, line in enumerate(lines, 1):
            fields = line.split()
            try:
                class_id = int(fields[0])
                box = [float(value) for value in fields[1:]]
                valid = (
                    len(fields) == 5
                    and class_id in range(len(NAMES))
                    and all(0 <= value <= 1 for value in box)
                    and box[2] > 0
                    and box[3] > 0
                )
            except (ValueError, IndexError):
                valid = False
            if not valid:
                raise ValueError(f"Invalid YOLO label: {label}:{line_number}")
            counts[class_id] += 1
    return counts


def main() -> None:
    source_yaml = SOURCE / "data.yaml"
    if not source_yaml.is_file():
        raise FileNotFoundError(source_yaml)
    source_config = yaml.safe_load(source_yaml.read_text())
    if source_config.get("names") != NAMES or source_config.get("nc") != len(NAMES):
        raise ValueError(f"Unexpected class order in {source_yaml}")

    seen_hashes: dict[str, str] = {}
    for split in SPLITS:
        counts = check_split(split, seen_hashes)
        print(
            f"{split}: {SPLITS[split]} images; "
            + ", ".join(f"{NAMES[i]}={counts[i]}" for i in range(len(NAMES)))
        )

    TARGET.mkdir(parents=True, exist_ok=True)
    config = {
        "path": str(SOURCE.resolve()),
        "train": "train/images",
        "val": "valid/images",
        "nc": len(NAMES),
        "names": NAMES,
    }
    output = TARGET / "dataset.yaml"
    output.write_text(yaml.safe_dump(config, sort_keys=False))
    print(f"Ready: {output} (validation only; no test split)")


if __name__ == "__main__":
    main()
