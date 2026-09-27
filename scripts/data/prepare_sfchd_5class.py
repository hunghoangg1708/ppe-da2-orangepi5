"""Prepare the five-class SFCHD dataset with the existing seed-42 split.

The original SFCHD files are read-only. The generated image files are links,
while YOLO labels are rewritten because the two clothing classes change order.
"""

import argparse
import hashlib
import json
import math
import os
import random
from collections import Counter
from pathlib import Path

from common import write_classes, write_dataset_yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = REPO_ROOT / "data" / "sfchd" / "raw"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "sfchd_5class" / "processed"
RAW_CLASSES = (
    "person",
    "helmet",
    "self_clothes",
    "safety_clothes",
    "head",
    "blur_head",
    "blur_clothes",
)
TARGET_CLASSES = (
    "person",
    "helmet",
    "safety_clothes",
    "self_clothes",
    "head",
)
CLASS_MAP = {0: 0, 1: 1, 2: 3, 3: 2, 4: 4}
SEED = 42
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def discover_images(raw: Path) -> dict[str, Path]:
    image_dir = raw / "images"
    if not image_dir.is_dir():
        raise FileNotFoundError(f"Missing image directory: {image_dir}")
    images: dict[str, Path] = {}
    for image in sorted(image_dir.iterdir()):
        if not image.is_file() or image.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if image.stem in images:
            raise ValueError(f"Two images have the same stem: {image.stem}")
        images[image.stem] = image
    if not images:
        raise ValueError(f"No images found in {image_dir}")
    return images


def validate_and_convert_label(label: Path) -> tuple[str, Counter[int], Counter[int]]:
    if not label.is_file():
        raise FileNotFoundError(f"Missing label: {label}")
    converted: list[str] = []
    original_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    for line_number, line in enumerate(label.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) != 5:
            raise ValueError(f"{label}:{line_number}: expected YOLO class x y w h")
        try:
            class_id = int(fields[0])
            x, y, width, height = (float(v) for v in fields[1:])
        except ValueError as exc:
            raise ValueError(f"{label}:{line_number}: invalid class or box") from exc
        if class_id not in range(len(RAW_CLASSES)):
            raise ValueError(f"{label}:{line_number}: class {class_id} outside 0..6")
        if not all(math.isfinite(v) for v in (x, y, width, height)):
            raise ValueError(f"{label}:{line_number}: non-finite box coordinate")
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < width <= 1 and 0 < height <= 1):
            raise ValueError(f"{label}:{line_number}: box outside normalized YOLO range")
        original_counts[class_id] += 1
        if class_id in CLASS_MAP:
            new_id = CLASS_MAP[class_id]
            converted.append(" ".join((str(new_id), *fields[1:])))
            target_counts[new_id] += 1
    return ("\n".join(converted) + "\n" if converted else "", original_counts, target_counts)


def link_image(source: Path, destination: Path, mode: str) -> None:
    if mode in {"auto", "symlink"}:
        try:
            destination.symlink_to(source.resolve())
            return
        except OSError:
            if mode == "symlink":
                raise
    try:
        os.link(source, destination)
    except OSError as exc:
        raise OSError(
            f"Cannot link {source}. Run on the same drive or enable symlinks; "
            "raw images were not copied."
        ) from exc


def prepare(raw: Path, output: Path, image_mode: str = "auto") -> dict:
    raw = raw.resolve()
    output = output.resolve()
    if image_mode not in {"auto", "symlink", "hardlink"}:
        raise ValueError(f"Unsupported image mode: {image_mode}")
    if output.exists():
        raise FileExistsError(f"Output already exists; refusing to overwrite: {output}")
    classes_file = raw / "classes.txt"
    if not classes_file.is_file():
        raise FileNotFoundError(f"Missing class list: {classes_file}")
    actual_classes = tuple(line.strip() for line in classes_file.read_text(encoding="utf-8").splitlines())
    if actual_classes != RAW_CLASSES:
        raise ValueError(f"Unexpected raw class order: {actual_classes!r}; expected {RAW_CLASSES!r}")

    images = discover_images(raw)
    labels: dict[str, str] = {}
    per_image_counts: dict[str, Counter[int]] = {}
    raw_counts: Counter[int] = Counter()
    new_counts: Counter[int] = Counter()
    for stem in sorted(images):
        converted, old, new = validate_and_convert_label(raw / "labels" / f"{stem}.txt")
        labels[stem] = converted
        per_image_counts[stem] = new
        raw_counts.update(old)
        new_counts.update(new)

    stems = sorted(images)
    random.Random(SEED).shuffle(stems)
    n_train = int(len(stems) * 0.8)
    n_val = int(len(stems) * 0.1)
    splits = {
        "train": stems[:n_train],
        "val": stems[n_train : n_train + n_val],
        "test": stems[n_train + n_val :],
    }
    split_instance_counts = {
        split: {
            name: sum(per_image_counts[stem][i] for stem in split_stems)
            for i, name in enumerate(TARGET_CLASSES)
        }
        for split, split_stems in splits.items()
    }

    output.mkdir(parents=True)
    split_hashes = {}
    for split, split_stems in splits.items():
        image_dir = output / "images" / split
        label_dir = output / "labels" / split
        image_dir.mkdir(parents=True)
        label_dir.mkdir(parents=True)
        (output / f"{split}_files.txt").write_text("\n".join(split_stems) + "\n", encoding="utf-8")
        split_hashes[split] = hashlib.sha256("\n".join(split_stems).encode("utf-8")).hexdigest()
        for stem in split_stems:
            image = images[stem]
            link_image(image, image_dir / image.name, image_mode)
            (label_dir / f"{stem}.txt").write_text(labels[stem], encoding="utf-8")

    write_classes(list(TARGET_CLASSES), output / "classes.txt")
    write_dataset_yaml(
        output / "dataset.yaml",
        output,
        list(TARGET_CLASSES),
        {"train": "images/train", "val": "images/val", "test": "images/test"},
    )
    label_digest = hashlib.sha256()
    for stem in sorted(labels):
        label_digest.update(stem.encode("utf-8") + b"\0" + labels[stem].encode("utf-8"))
    manifest = {
        "source": str(raw),
        "output": str(output),
        "seed": SEED,
        "split_ratio": {"train": 0.8, "val": 0.1, "test": 0.1},
        "raw_classes": list(RAW_CLASSES),
        "classes": list(TARGET_CLASSES),
        "class_id_map": {str(old): new for old, new in CLASS_MAP.items()},
        "dropped_class_ids": [5, 6],
        "images": len(images),
        "split_images": {split: len(value) for split, value in splits.items()},
        "raw_instances": {name: raw_counts[i] for i, name in enumerate(RAW_CLASSES)},
        "instances": {name: new_counts[i] for i, name in enumerate(TARGET_CLASSES)},
        "split_instances": split_instance_counts,
        "split_list_sha256": split_hashes,
        "converted_labels_sha256": label_digest.hexdigest(),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-mode", choices=("auto", "symlink", "hardlink"), default="auto")
    args = parser.parse_args()
    manifest = prepare(args.raw, args.output, args.image_mode)
    print(json.dumps({key: manifest[key] for key in ("images", "split_images", "split_instances")}, indent=2))


if __name__ == "__main__":
    main()
