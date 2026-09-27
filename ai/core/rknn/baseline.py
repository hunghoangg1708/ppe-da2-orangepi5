"""Baseline RKNN export using Ultralytics native RKNN backend."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ultralytics import YOLO

from ai.core.dataset import dataset_yaml_path


@dataclass
class ExportConfig:
    weights: str
    dataset: str
    platform: str = "rk3588"
    imgsz: int = 640
    quantize: int = 8  # 8 for INT8 quantization, 16 for FP16
    calib_split: str = "train"


def export_baseline(cfg: ExportConfig) -> str:
    """Export model weights to RKNN using Ultralytics native backend."""
    model = YOLO(cfg.weights)
    data_yaml = dataset_yaml_path(cfg.dataset)

    stash = None
    if cfg.quantize == 8:
        # export_rknn() deletes this file when quantize=8; keep a copy and restore it after.
        # opset=19 matches the clamp export_rknn() applies internally.
        onnx_path = Path(model.export(format="onnx", imgsz=cfg.imgsz, opset=19))
        stash = onnx_path.with_suffix(".onnx.stash")
        shutil.copy2(onnx_path, stash)

    result = model.export(
        format="rknn",
        name=cfg.platform,
        quantize=cfg.quantize,
        data=str(data_yaml),
        split=cfg.calib_split,
        imgsz=cfg.imgsz,
    )

    if stash is not None:
        stash.rename(onnx_path)

    return result
