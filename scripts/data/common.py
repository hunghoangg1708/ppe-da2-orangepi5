"""Shared helpers for scripts/data/prepare_*.py.

Every prepare_<name>.py turns data/<name>/raw/ into data/<name>/processed/
by symlinking images/labels into a YOLO-style split layout. raw/ is never
modified.
"""
from pathlib import Path


def symlink_pair(image_src: Path, label_src: Path, images_dst_dir: Path, labels_dst_dir: Path) -> None:
    images_dst_dir.mkdir(parents=True, exist_ok=True)
    labels_dst_dir.mkdir(parents=True, exist_ok=True)
    image_link = images_dst_dir / image_src.name
    label_link = labels_dst_dir / label_src.name
    if not image_link.exists():
        image_link.symlink_to(image_src.resolve())
    if not label_link.exists():
        label_link.symlink_to(label_src.resolve())


def write_classes(classes: list[str], dst: Path) -> None:
    dst.write_text("\n".join(classes) + "\n")


def write_dataset_yaml(dst: Path, root: Path, classes: list[str], splits: dict[str, str]) -> None:
    lines = [f"path: {root.resolve()}"]
    for split, rel in splits.items():
        lines.append(f"{split}: {rel}")
    lines.append(f"nc: {len(classes)}")
    names = ", ".join(f'"{c}"' for c in classes)
    lines.append(f"names: [{names}]")
    dst.write_text("\n".join(lines) + "\n")
