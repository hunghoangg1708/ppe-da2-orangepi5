"""Geometry and temporal rules for person-level PPE events.

The rules deliberately leave uncertain cases undecided. A missing PPE box is
not evidence that a worker lacks that item.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


Box = tuple[float, float, float, float]
PPE_CLASSES = {"Helmet", "NoHelmet", "Vest", "NoVest"}


@dataclass(frozen=True)
class Detection:
    box: Box
    label: str
    confidence: float


@dataclass(frozen=True)
class Person:
    track_id: int
    box: Box
    confidence: float


def _area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _overlap_fraction(inner: Box, region: Box) -> float:
    intersection = (
        max(inner[0], region[0]),
        max(inner[1], region[1]),
        min(inner[2], region[2]),
        min(inner[3], region[3]),
    )
    return _area(intersection) / max(_area(inner), 1.0)


def box_iou(a: Box, b: Box) -> float:
    intersection = (
        max(a[0], b[0]), max(a[1], b[1]),
        min(a[2], b[2]), min(a[3], b[3]),
    )
    shared = _area(intersection)
    return shared / max(_area(a) + _area(b) - shared, 1.0)


def _ppe_region(person_box: Box, label: str) -> Box:
    x1, y1, x2, y2 = person_box
    width, height = x2 - x1, y2 - y1
    # Headwear can extend slightly above a person's detected box.
    if label in {"Helmet", "NoHelmet"}:
        return (x1 - 0.08 * width, y1 - 0.08 * height,
                x2 + 0.08 * width, y1 + 0.38 * height)
    return (x1 - 0.06 * width, y1 + 0.17 * height,
            x2 + 0.06 * width, y1 + 0.82 * height)


def associate(
    people: list[Person], detections: list[Detection]
) -> dict[int, dict[str, str]]:
    """Assign each PPE box to at most one person; leave ambiguous boxes unused."""
    candidates: dict[int, dict[str, list[str]]] = {
        person.track_id: {"helmet": [], "vest": []} for person in people
    }
    for detection in detections:
        if detection.label not in PPE_CLASSES:
            continue
        matches = sorted(
            ((
                _overlap_fraction(detection.box, _ppe_region(person.box, detection.label)),
                person.track_id,
            ) for person in people),
            reverse=True,
        )
        if not matches or matches[0][0] < 0.55:
            continue
        # Similar overlap with two people usually means the PPE box cannot be
        # attributed reliably, especially when people occlude one another.
        if len(matches) > 1 and matches[0][0] - matches[1][0] < 0.15:
            continue
        part = "helmet" if detection.label in {"Helmet", "NoHelmet"} else "vest"
        candidates[matches[0][1]][part].append(detection.label)

    state: dict[int, dict[str, str]] = {}
    for person in people:
        parts: dict[str, str] = {}
        for part, labels in candidates[person.track_id].items():
            if len(set(labels)) == 1:
                parts[part] = "violation" if labels[0].startswith("No") else "compliant"
            else:
                parts[part] = "unknown"
        state[person.track_id] = parts
    return state


@dataclass
class EventGate:
    """Require repeated negative evidence and emit one event per ID and part."""

    window: int = 5
    confirm_frames: int = 3
    history: dict[tuple[int, str], deque[str]] = field(default_factory=dict)
    emitted: set[tuple[int, str]] = field(default_factory=set)
    recent: list[tuple[str, Box, int]] = field(default_factory=list)

    def update(
        self, track_id: int, part: str, observation: str,
        person_box: Box | None = None, frame_index: int = 0,
        dedup_frames: int = 0,
    ) -> bool:
        key = (track_id, part)
        values = self.history.setdefault(key, deque(maxlen=self.window))
        values.append(observation)
        if key in self.emitted:
            return False
        # A positive and a negative observation in the recent window are
        # conflicting evidence; wait until the conflict ages out.
        if values.count("violation") >= self.confirm_frames and "compliant" not in values:
            self.emitted.add(key)
            if person_box is not None and dedup_frames > 0:
                self.recent = [
                    item for item in self.recent
                    if frame_index - item[2] <= dedup_frames
                ]
                if any(
                    old_part == part and box_iou(person_box, old_box) >= 0.6
                    for old_part, old_box, _ in self.recent
                ):
                    return False
                self.recent.append((part, person_box, frame_index))
            return True
        return False
