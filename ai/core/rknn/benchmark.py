"""RK3588 on-device benchmarking utilities for RKNN models.

Provides board connection management, latency evaluation, and mAP measurement.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import cv2
import numpy as np
import torch
import yaml
from rknn.api import RKNN
from ultralytics.utils.nms import non_max_suppression

from ai.core.dataset import dataset_yaml_path
from ai.core.metrics import Detection, GroundTruth, compute_map

CORE_MASK = {
    "AUTO": RKNN.NPU_CORE_AUTO,
    "CORE_0": RKNN.NPU_CORE_0,
    "CORE_1": RKNN.NPU_CORE_1,
    "CORE_2": RKNN.NPU_CORE_2,
    "CORE_0_1": RKNN.NPU_CORE_0_1,
    "CORE_0_1_2": RKNN.NPU_CORE_0_1_2,
}


@contextmanager
def connect_board(
    rknn_path: str,
    device_id: str,
    core_mask: str = "AUTO",
    perf_debug: bool = True,
):
    """Context manager to load an RKNN model and initialize runtime on target board."""
    rknn = RKNN(verbose=False)
    ret = rknn.load_rknn(rknn_path)
    if ret != 0:
        raise RuntimeError(f"load_rknn failed: {ret}")
    ret = rknn.init_runtime(
        target="rk3588",
        device_id=device_id,
        core_mask=CORE_MASK[core_mask],
        perf_debug=perf_debug,
    )
    if ret != 0:
        raise RuntimeError(f"init_runtime failed: {ret}")
    try:
        yield rknn
    finally:
        rknn.release()


def measure_latency(rknn: RKNN, fix_freq: bool = True) -> dict:
    """Measure inference latency, throughput, and op execution breakdown via eval_perf."""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rknn.eval_perf(is_print=True, fix_freq=fix_freq)
    text = buf.getvalue()

    total_us = None
    for line in text.splitlines():
        if "Total Operator Elapsed Per Frame Time(us):" in line:
            total_us = float(line.split(":")[-1].strip())
            break
    if total_us is None:
        raise RuntimeError(f"Could not parse latency from eval_perf() output:\n{text}")

    cpu_us = npu_us = None
    fallback_ops = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] == "Total" and cpu_us is None:
            # Parse aggregate execution times from the summary row
            try:
                cpu_us, npu_us = float(parts[1]), float(parts[3])
            except ValueError:
                pass
    # Parse per-layer execution to identify operators falling back to CPU
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit() and parts[3] == "CPU" and parts[1] not in fallback_ops:
            fallback_ops.append(parts[1])

    return {
        "latency_ms": total_us / 1000,
        "fps": round(1000 / (total_us / 1000), 2),
        "npu_time_us": npu_us,
        "cpu_time_us": cpu_us,
        "cpu_fallback_ops": fallback_ops,
    }


def measure_map_drop(rknn: RKNN, dataset: str, split: str = "test", imgsz: int = 640) -> dict:
    """Run inference on dataset split and compute evaluation metrics."""
    data_yaml = yaml.safe_load(dataset_yaml_path(dataset).read_text())
    images_dir = Path(data_yaml["path"]) / data_yaml[split]
    labels_dir = Path(str(images_dir).replace("/images/", "/labels/"))

    predictions, targets = [], []
    for img_path in sorted(images_dir.glob("*.jpg")):
        img = cv2.imread(str(img_path))
        img = cv2.resize(img, (imgsz, imgsz))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        raw = rknn.inference(inputs=[np.expand_dims(img, 0)])[0]
        pred = torch.from_numpy(raw).float()
        # Scale normalized box coordinates [0, 1] to pixel dimensions for NMS
        pred[:, [0, 2]] *= imgsz
        pred[:, [1, 3]] *= imgsz

        nms_out = non_max_suppression(pred, conf_thres=0.001, iou_thres=0.65)[0]
        predictions.append(
            Detection(
                boxes=nms_out[:, :4].numpy(),
                scores=nms_out[:, 4].numpy(),
                classes=nms_out[:, 5].numpy().astype(int),
            )
        )

        label_path = labels_dir / f"{img_path.stem}.txt"
        gt_boxes, gt_classes = [], []
        if label_path.exists():
            for line in label_path.read_text().splitlines():
                if not line.strip():
                    continue
                cls, cx, cy, w, h = (float(v) for v in line.split())
                gt_boxes.append(
                    [
                        (cx - w / 2) * imgsz,
                        (cy - h / 2) * imgsz,
                        (cx + w / 2) * imgsz,
                        (cy + h / 2) * imgsz,
                    ]
                )
                gt_classes.append(int(cls))
        targets.append(
            GroundTruth(
                boxes=np.array(gt_boxes, dtype=np.float32).reshape(-1, 4),
                classes=np.array(gt_classes, dtype=int),
            )
        )

    result = compute_map(predictions, targets)
    return {
        "n_test_images": len(predictions),
        "map50_int8": result["map50"],
        "map50_95_int8": result["map50_95"],
        "precision_int8": result["precision"],
        "recall_int8": result["recall"],
        "per_class_ap50_int8": result["per_class_ap50"],
    }
