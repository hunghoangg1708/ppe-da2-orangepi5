"""Run person tracking, PPE association and event capture on video or camera."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

from app.logic import Detection, EventGate, Person, associate


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PPE = ROOT / "ai/automation/runs/2026-09-30_huang_cheng_yolov8n_baseline_80ep/weights/best.pt"
DEFAULT_PERSON = ROOT / "yolov8n.pt"


def _default_output_name(source: int | str) -> str:
    label = f"camera_{source}" if isinstance(source, int) else Path(source).stem
    label = re.sub(r"[^A-Za-z0-9_-]+", "_", label).strip("_") or "video"
    return f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _detections(result, names: dict[int, str]) -> list[Detection]:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []
    return [
        Detection(tuple(map(float, box)), names[int(class_id)], float(confidence))
        for box, class_id, confidence in zip(
            boxes.xyxy.cpu().numpy(), boxes.cls.cpu().numpy(), boxes.conf.cpu().numpy()
        )
    ]


def _people(result) -> list[Person]:
    boxes = result.boxes
    if boxes is None or boxes.id is None:
        return []
    return [
        Person(int(track_id), tuple(map(float, box)), float(confidence))
        for box, track_id, confidence in zip(
            boxes.xyxy.cpu().numpy(), boxes.id.cpu().numpy(), boxes.conf.cpu().numpy()
        )
    ]


def _crop(frame, box, padding: float = 0.12):
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = box
    dx, dy = (x2 - x1) * padding, (y2 - y1) * padding
    left, top = max(0, int(x1 - dx)), max(0, int(y1 - dy))
    right, bottom = min(width, int(x2 + dx)), min(height, int(y2 + dy))
    return frame[top:bottom, left:right]


def _draw(frame, people: list[Person], states: dict[int, dict[str, str]]) -> None:
    colors = {"violation": (0, 0, 255), "compliant": (0, 180, 0), "unknown": (0, 190, 220)}
    for person in people:
        parts = states[person.track_id]
        worst = "violation" if "violation" in parts.values() else (
            "unknown" if "unknown" in parts.values() else "compliant"
        )
        color = colors[worst]
        x1, y1, x2, y2 = map(int, person.box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        short = {"violation": "NO", "compliant": "OK", "unknown": "?"}
        label = f"ID {person.track_id} H:{short[parts['helmet']]} V:{short[parts['vest']]}"
        cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, color, 2, cv2.LINE_AA)


def run(args: argparse.Namespace) -> Path:
    if args.confirm_frames < 1 or args.window < args.confirm_frames:
        raise ValueError("Cần 1 <= --confirm-frames <= --window")
    if args.imgsz < 32 or args.dedup_seconds < 0 or args.max_frames < 0:
        raise ValueError("--imgsz phải >= 32; --dedup-seconds và --max-frames phải >= 0")
    if not 0 < args.person_conf < 1 or not 0 < args.ppe_conf < 1:
        raise ValueError("--person-conf và --ppe-conf phải nằm giữa 0 và 1")
    if not args.ppe_weights.is_file() or not args.person_weights.is_file():
        raise FileNotFoundError("Không tìm thấy checkpoint PPE hoặc person; kiểm tra --ppe-weights/--person-weights")
    source = int(args.source) if args.source.isdigit() else args.source
    if isinstance(source, str) and not Path(source).is_file():
        raise FileNotFoundError(f"Không tìm thấy video: {source}")
    output = (args.output or ROOT / "runs/ppe_monitor" /
              _default_output_name(source)).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Thư mục kết quả đã có dữ liệu: {output}; chọn --output khác")
    person_model = YOLO(str(args.person_weights))
    ppe_model = YOLO(str(args.ppe_weights))
    if {ppe_model.names[i] for i in ppe_model.names} != {"Helmet", "NoHelmet", "Vest", "NoVest"}:
        raise ValueError("Checkpoint PPE phải có bốn lớp Helmet, NoHelmet, Vest, NoVest")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được nguồn video/camera: {source}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "events").mkdir(exist_ok=True)
    device = args.device or ("0" if torch.cuda.is_available() else "cpu")
    gate = EventGate(window=args.window, confirm_frames=args.confirm_frames)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = None
    if not args.no_video:
        writer = cv2.VideoWriter(str(output / "annotated.mp4"),
                                 cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        if not writer.isOpened():
            cap.release()
            raise RuntimeError("Không tạo được video đầu ra; thử --no-video")

    frame_index = 0
    event_count = 0
    try:
        with (output / "events.jsonl").open("w", encoding="utf-8") as events:
            while True:
                ok, frame = cap.read()
                if not ok or (args.max_frames and frame_index >= args.max_frames):
                    break
                tracked = person_model.track(
                    frame, persist=True, tracker="bytetrack.yaml", classes=[0],
                    imgsz=args.imgsz, conf=args.person_conf, device=device,
                    verbose=False,
                )[0]
                predicted = ppe_model.predict(
                    frame, imgsz=args.imgsz, conf=args.ppe_conf,
                    device=device, verbose=False,
                )[0]
                people = _people(tracked)
                states = associate(people, _detections(predicted, ppe_model.names))
                for person in people:
                    for part in ("helmet", "vest"):
                        if not gate.update(
                            person.track_id, part, states[person.track_id][part],
                            person_box=person.box, frame_index=frame_index,
                            dedup_frames=int(args.dedup_seconds * fps),
                        ):
                            continue
                        event_count += 1
                        stem = f"frame_{frame_index:06d}_id_{person.track_id}_{part}"
                        crop_path = output / "events" / f"{stem}_person.jpg"
                        frame_path = output / "events" / f"{stem}_scene.jpg"
                        crop = _crop(frame, person.box)
                        if crop.size == 0 or not cv2.imwrite(str(crop_path), crop):
                            raise RuntimeError(f"Không lưu được ảnh người: {crop_path}")
                        scene = frame.copy()
                        x1, y1, x2, y2 = map(int, person.box)
                        cv2.rectangle(scene, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        if not cv2.imwrite(str(frame_path), scene):
                            raise RuntimeError(f"Không lưu được ảnh toàn cảnh: {frame_path}")
                        record = {
                            "event_id": stem,
                            "source": str(source),
                            "frame": frame_index,
                            "video_second": round(frame_index / fps, 3),
                            "recorded_at": datetime.now(timezone.utc).isoformat(),
                            "track_id": person.track_id,
                            "violation": "no_helmet" if part == "helmet" else "no_vest",
                            "person_box": list(person.box),
                            "person_confidence": round(person.confidence, 4),
                            "person_image": str(crop_path.relative_to(output)),
                            "scene_image": str(frame_path.relative_to(output)),
                            "person_model": str(args.person_weights.resolve()),
                            "ppe_model": str(args.ppe_weights.resolve()),
                            "imgsz": args.imgsz,
                            "confirmation": f"{args.confirm_frames}/{args.window}",
                        }
                        events.write(json.dumps(record, ensure_ascii=False) + "\n")
                        events.flush()
                if writer is not None or args.show:
                    annotated = frame.copy()
                    _draw(annotated, people, states)
                    if writer is not None:
                        writer.write(annotated)
                    if args.show:
                        cv2.imshow("DA2 PPE monitor (q to quit)", annotated)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            break
                frame_index += 1
                if frame_index % 50 == 0:
                    print(f"{frame_index} frames, {event_count} events", flush=True)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if args.show:
            cv2.destroyAllWindows()
    print(f"Done: {frame_index} frames, {event_count} events -> {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="PPE monitor trên laptop")
    parser.add_argument("--source", required=True, help="Đường dẫn video hoặc camera index (0, 1, ...)")
    parser.add_argument("--ppe-weights", type=Path, default=DEFAULT_PPE)
    parser.add_argument("--person-weights", type=Path, default=DEFAULT_PERSON)
    parser.add_argument("--output", type=Path,
                        help="Thư mục mới để lưu kết quả; mặc định tên nguồn và thời gian")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--person-conf", type=float, default=0.35)
    parser.add_argument("--ppe-conf", type=float, default=0.35)
    parser.add_argument("--window", type=int, default=8)
    parser.add_argument("--confirm-frames", type=int, default=5)
    parser.add_argument("--dedup-seconds", type=float, default=10.0,
                        help="Gộp sự kiện cùng loại ở cùng vị trí khi tracker đổi ID")
    parser.add_argument("--max-frames", type=int, default=0, help="Giới hạn frame để thử nhanh; 0 = toàn bộ")
    parser.add_argument("--no-video", action="store_true", help="Chỉ lưu ảnh và sự kiện")
    parser.add_argument("--show", action="store_true", help="Hiển thị cửa sổ trực tiếp")
    parser.add_argument("--device", help="Thiết bị inference, mặc định tự chọn CUDA/CPU")
    try:
        run(parser.parse_args())
    except KeyboardInterrupt:
        print("Stopped by user")


if __name__ == "__main__":
    main()
