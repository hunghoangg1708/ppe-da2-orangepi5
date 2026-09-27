# Đồ án 2 — giám sát PPE trên Orange Pi 5

Repo độc lập cho hệ thống camera OV13855 → phát hiện PPE trên RK3588S NPU → gán PPE theo từng người → lưu sự kiện vi phạm → xem camera và sự kiện trên web.

**Phạm vi dữ liệu:** SFCHD với 5 lớp `person`, `helmet`, `safety_clothes`, `self_clothes`, `head`. Không phát hiện mũ/áo được xử lý là **không xác định**; `head` và `self_clothes` là tín hiệu vi phạm theo nhãn SFCHD. Xem [kế hoạch triển khai](plan/DA2_PPE_Implementation_Plan.md) để biết điều kiện hoàn thành từng giai đoạn.

## Trạng thái hiện tại

- Camera đã thu 1920×1080 NV12 gần 30 FPS; model 3 lớp đã chạy ảnh tĩnh trên NPU theo [nhật ký board](logs/OrangePi5_Work_Log_2026-09-20.md).
- Đã mang sang mã chuẩn bị SFCHD 5 lớp, cấu hình YOLOv8n/s, train, export RKNN và benchmark từ [repo nền tảng](docs/ORIGIN.md).
- Chưa có dữ liệu raw trong repo, checkpoint 5 lớp, pipeline camera + AI, gán PPE theo người, database hoặc web. Các kết quả 3/7 lớp trước đây không phải kết quả đánh giá ĐA2 5 lớp.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| `ai/` | Train, đánh giá, export RKNN và cấu hình hai baseline 5 lớp |
| `scripts/data/` | Tạo bộ SFCHD 5 lớp với split cố định |
| `data/` | Data card; ảnh và nhãn raw/processed được lưu cục bộ và không đưa lên Git |
| `tests/` | Kiểm tra mapping lớp và split |
| `plan/`, `guides/`, `logs/` | Kế hoạch, hướng dẫn board và nhật ký đã ghi |
| `references/` | Hai tài liệu nguồn trực tiếp cần cho ĐA2 |
| `docs/` | Nguồn gốc mã và quyết định tách repo |

## Bắt đầu

Yêu cầu: Linux x86_64, Python 3.12 và máy có GPU NVIDIA để train theo config mặc định. RKNN-Toolkit2 2.3.2 dùng trên máy phát triển; board Orange Pi 5 dùng RKNNLite2/runtime tương ứng. Cài môi trường mới bằng `python3.12 -m venv .venv`, sau đó `.venv/bin/python -m pip install -e .`. Dữ liệu SFCHD raw đặt tại `data/sfchd/raw/` với `classes.txt`, `images/` và `labels/`.

```bash
make test
make prepare-data
make train CONFIG=ai/automation/configs/sfchd_5class_yolov8n_baseline.yaml
```

Sau khi có checkpoint trong `ai/automation/runs/<run_id>/weights/best.pt`:

```bash
make export-npu RUN=<run_id>
make benchmark-npu RUN=<run_id> DEVICE=<board-ip:port>
```

Lệnh benchmark cần board đang chạy RKNN server. Chất lượng của file RKNN phải được kiểm trên cùng tập test trước khi dùng cho camera; `npu_benchmark.json` cũ chỉ là bản ghi export, chưa có số đo board.

## Quy tắc làm việc

Giữ nguyên test split và class order trong [data card 5 lớp](data/sfchd_5class/DATA_CARD.md). Ghi config, seed, commit, phiên bản runtime và điều kiện đo cho mỗi kết quả. Đánh giá detector trên SFCHD test và đánh giá gán/cảnh báo trên video có đáp án riêng.
