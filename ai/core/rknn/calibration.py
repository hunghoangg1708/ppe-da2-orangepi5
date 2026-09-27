"""Calibration image selection utilities for RKNN INT8 quantization."""
from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path


def sample_calibration_images(
    labels_dir: Path,
    n: int = 100,
    min_per_class: int = 10,
    seed: int = 42,
) -> list[str]:
    """Select representative calibration images with guaranteed coverage of minority classes.

    Prioritizes minority classes to ensure at least min_per_class images per class
    before filling the remainder uniformly.

    Args:
        labels_dir: Path to directory containing YOLO .txt label files.
        n: Total number of calibration image stems to return.
        min_per_class: Minimum guaranteed images per class.
        seed: Random seed for deterministic selection.

    Returns:
        List of image stems (without extension), with length <= n.
    """
    rng = random.Random(seed)
    class_to_images: dict[int, set[str]] = defaultdict(set)
    all_images: list[str] = []

    for label_file in sorted(labels_dir.glob("*.txt")):
        classes = {int(line.split()[0]) for line in label_file.read_text().splitlines() if line.strip()}
        all_images.append(label_file.stem)
        for c in classes:
            class_to_images[c].add(label_file.stem)

    selected: set[str] = set()
    for c in sorted(class_to_images, key=lambda c: len(class_to_images[c])):
        candidates = list(class_to_images[c] - selected)
        rng.shuffle(candidates)
        selected.update(candidates[:min_per_class])

    remaining = [img for img in all_images if img not in selected]
    rng.shuffle(remaining)
    selected.update(remaining[: max(0, n - len(selected))])

    return list(selected)[:n]


def write_calib_list(image_stems: list[str], images_dir: Path, out_path: Path) -> Path:
    """Write absolute image paths to a newline-delimited dataset list for RKNN build."""
    paths = [str(images_dir / f"{stem}.jpg") for stem in image_stems]
    out_path.write_text("\n".join(paths) + "\n")
    return out_path
