"""Evaluation metrics computation for object detection.

Computes mAP@0.5, mAP@0.5:0.95, precision, recall, and per-class AP
using Ultralytics metric definitions.
"""
from dataclasses import dataclass

import numpy as np
import torch
from ultralytics.utils.metrics import ap_per_class, box_iou

# 10 IoU thresholds from 0.50 to 0.95 with step 0.05
IOU_THRESHOLDS = torch.linspace(0.5, 0.95, 10)


@dataclass
class Detection:
    boxes: np.ndarray  # (N, 4) xyxy, pixel coords
    scores: np.ndarray  # (N,)
    classes: np.ndarray  # (N,) int


@dataclass
class GroundTruth:
    boxes: np.ndarray  # (M, 4) xyxy, pixel coords
    classes: np.ndarray  # (M,) int


def match_predictions(
    pred_boxes: torch.Tensor,
    pred_classes: torch.Tensor,
    target_boxes: torch.Tensor,
    target_classes: torch.Tensor,
    iou_thresholds: torch.Tensor = IOU_THRESHOLDS,
) -> np.ndarray:
    """Return an (N, 10) bool array: is prediction i a true positive at each IoU threshold."""
    iou = box_iou(target_boxes, pred_boxes)
    correct_class = target_classes[:, None] == pred_classes
    iou = (iou * correct_class).cpu().numpy()

    correct = np.zeros((pred_classes.shape[0], len(iou_thresholds)), dtype=bool)
    for i, threshold in enumerate(iou_thresholds.tolist()):
        matches = np.array(np.nonzero(iou >= threshold)).T
        if matches.shape[0] == 0:
            continue
        if matches.shape[0] > 1:
            matches = matches[iou[matches[:, 0], matches[:, 1]].argsort()[::-1]]
            matches = matches[np.unique(matches[:, 1], return_index=True)[1]]  # 1 gt per pred
            matches = matches[np.unique(matches[:, 0], return_index=True)[1]]  # 1 pred per gt
        correct[matches[:, 1].astype(int), i] = True
    return correct


def compute_map(
    predictions: list[Detection],
    targets: list[GroundTruth],
) -> dict:
    """Compute mAP, precision, and recall from aligned prediction and target lists.

    Args:
        predictions: List of Detection objects per image.
        targets: List of GroundTruth objects per image.

    Returns:
        Dictionary containing map50, map50_95, precision, recall, and per_class_ap50.
    """
    tp_list, conf_list, pred_cls_list, target_cls_list = [], [], [], []

    for det, gt in zip(predictions, targets):
        target_cls_list.append(gt.classes)
        if det.boxes.shape[0] == 0:
            continue
        p_boxes = torch.as_tensor(det.boxes, dtype=torch.float32)
        p_cls = torch.as_tensor(det.classes)
        if gt.boxes.shape[0] == 0:
            tp = np.zeros((det.boxes.shape[0], len(IOU_THRESHOLDS)), dtype=bool)
        else:
            t_boxes = torch.as_tensor(gt.boxes, dtype=torch.float32)
            t_cls = torch.as_tensor(gt.classes)
            tp = match_predictions(p_boxes, p_cls, t_boxes, t_cls)
        tp_list.append(tp)
        conf_list.append(det.scores)
        pred_cls_list.append(det.classes)

    tp = np.concatenate(tp_list) if tp_list else np.zeros((0, len(IOU_THRESHOLDS)), dtype=bool)
    conf = np.concatenate(conf_list) if conf_list else np.zeros(0)
    pred_cls = np.concatenate(pred_cls_list) if pred_cls_list else np.zeros(0)
    target_cls = np.concatenate(target_cls_list) if target_cls_list else np.zeros(0)

    _, _, precision, recall, _, ap, unique_classes, *_ = ap_per_class(tp, conf, pred_cls, target_cls)

    return {
        "map50": float(ap[:, 0].mean()) if len(ap) else 0.0,
        "map50_95": float(ap.mean()) if len(ap) else 0.0,
        "precision": float(precision.mean()) if len(precision) else 0.0,
        "recall": float(recall.mean()) if len(recall) else 0.0,
        "per_class_ap50": {int(c): float(ap[i, 0]) for i, c in enumerate(unique_classes)},
    }
