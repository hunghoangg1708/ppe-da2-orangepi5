# Đồ án 2 — giám sát PPE trên Orange Pi 5

Repo độc lập cho Đồ án 2. Mục tiêu cuối: camera OV13855 → phát hiện PPE trên RK3588S NPU → gán PPE theo từng người → lưu sự kiện vi phạm → xem camera và sự kiện trên web. Hiện bản thử nghiệm giám sát chạy trên laptop; xem trạng thái bên dưới.

**Hướng hiện tại:** dùng bộ Huang–Cheng với bốn trạng thái `Helmet`, `NoHelmet`, `NoVest`, `Vest` cho nhận diện PPE; ứng dụng laptop dùng YOLOv8n COCO để phát hiện người, ByteTrack để gán ID, rồi gán PPE theo vùng đầu/thân. Ba baseline SFCHD, Construction Site Safety và CHV vẫn được giữ để đối chiếu. Xem [kế hoạch triển khai](plan/DA2_PPE_Implementation_Plan.md) để biết các mốc của hệ thống.

**Thành viên mới:** đọc [Hướng dẫn cài đặt và kiểm thử nhóm](guides/TEAM_SETUP_AND_TEST.md) trước khi chạy. File `.pt`, video và ảnh dataset hiện không được đưa lên Git; cần nhận riêng từ người phụ trách.

## Trạng thái hiện tại

- Camera đã thu 1920×1080 NV12 gần 30 FPS; model 3 lớp đã chạy ảnh tĩnh trên NPU theo [nhật ký board](logs/OrangePi5_Work_Log_2026-09-20.md).
- Đã mang sang mã chuẩn bị SFCHD 5 lớp, cấu hình YOLOv8n/s, train, export RKNN và benchmark từ [repo nền tảng](docs/ORIGIN.md).
- Đã train các baseline trên laptop và lưu checkpoint trong `ai/automation/runs/`. Có bản thử nghiệm theo dõi người và ghi ảnh vi phạm trên laptop (`app/monitor.py`); chưa đo trên camera demo thật, chưa port pipeline hai model sang NPU, chưa có database hoặc web.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| `ai/` | Train, đánh giá, export RKNN và cấu hình các baseline |
| `app/` | Bản thử nghiệm laptop: phát hiện người, tracking, gán PPE, ảnh và sự kiện |
| `scripts/data/` | Kiểm và chuẩn bị dữ liệu cho các baseline, gồm Huang–Cheng |
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

### Train thử Construction Site Safety cho áo phản quang

Bản Roboflow v30 gốc nằm ở `data/construction_site_safety/raw/Construction Site Safety.v30-raw-images_latestversion.yolov8/`. Bộ gốc có 25 lớp; lệnh chuẩn bị dưới đây chỉ giữ `Person`, `Hardhat`, `NO-Hardhat`, `Safety Vest`, `NO-Safety Vest` và tạo bản 5 lớp tại `data/construction_site_safety_5class/processed/`. Ảnh và nhãn gốc không bị thay đổi.

```bash
.venv/bin/python scripts/data/prepare_construction_site_safety_5class.py
make train CONFIG=ai/automation/configs/construction_site_safety_5class_yolov8n.yaml
```

Cấu hình train tối đa 80 epoch, dừng sớm nếu kết quả validation không cải thiện sau 15 epoch, ảnh 640 px và batch 16. Kết quả ở `ai/automation/runs/<run_id>/`: `weights/best.pt`, `metrics.csv`, các biểu đồ trong `plots/` và đánh giá test; bảng tổng hợp ở `ai/automation/leaderboards/construction_site_safety_5class.csv`.

Các video trong `data/Test/` được giữ làm nguồn kiểm thử video độc lập. Không dùng chúng để fine-tune khi còn lấy chúng làm bộ kiểm thử. Hiện tại nhóm xem lại các sự kiện và trường hợp sai; chưa tạo bộ nhãn thủ công cho 27 khung hình.

### Chuẩn bị Huang–Cheng

Bộ ảnh đã tải nằm tại `data/Huang-Cheng/`. Chạy bước kiểm tra để tạo YAML phù hợp với máy hiện tại, sau đó train baseline:

```bash
.venv/bin/python scripts/data/prepare_huang_cheng.py
make train CONFIG=ai/automation/configs/huang_cheng_yolov8n.yaml
```

Bộ này có 1.829 ảnh train, 457 ảnh validation và **không có ảnh test riêng**. Bảng kết quả sau train ghi `val_*`; không so trực tiếp với chỉ số test của các bộ khác. Nguồn dữ liệu và giới hạn được ghi trong [data card Huang–Cheng](data/huang_cheng/DATA_CARD.md).

Sau khi có checkpoint trong `ai/automation/runs/<run_id>/weights/best.pt`:

```bash
make export-npu RUN=<run_id>
make benchmark-npu RUN=<run_id> DEVICE=<board-ip:port>
```

Lệnh benchmark cần board đang chạy RKNN server. Chất lượng của file RKNN phải được kiểm trên cùng tập test trước khi dùng cho camera; `npu_benchmark.json` cũ chỉ là bản ghi export, chưa có số đo board.

### Thử luồng phát hiện vi phạm trên laptop

Cần hai checkpoint: `yolov8n.pt` (COCO, lớp người) tại gốc repo và `best.pt` Huang–Cheng tại đường dẫn mặc định trong `app/monitor.py`. Cài môi trường từ `pyproject.toml`; ByteTrack cần gói `lap`. Chạy thử trên video độc lập:

```bash
.venv/bin/python -m app.monitor --source data/Test/007.mp4
```

Thử nhanh 100 frame hoặc đổi nguồn sang camera laptop:

```bash
.venv/bin/python -m app.monitor --source data/Test/007.mp4 --max-frames 100
.venv/bin/python -m app.monitor --source 0 --show --no-video
```

Mỗi lần chạy tự tạo thư mục mới theo tên nguồn và thời gian, ví dụ `runs/ppe_monitor/007_20261001_003703/` cho video `007.mp4` hoặc `camera_0_.../` cho camera 0. Bên trong có `annotated.mp4` (nếu bật ghi video), `events.jsonl`, ảnh người và ảnh toàn cảnh trong `events/`. Dùng `--output runs/ppe_monitor/ten-lan-chay` nếu muốn đặt tên riêng; thư mục đó phải mới hoặc rỗng. Nhấn `q` khi xem camera bằng `--show`, hoặc `Ctrl+C` để dừng.

Màu khung: xanh = có bằng chứng mũ và áo đạt; đỏ = có bằng chứng vi phạm; vàng = chưa đủ bằng chứng. `H` là mũ, `V` là áo; `OK`, `NO`, `?` lần lượt là đạt, vi phạm, chưa rõ. **Không thấy box mũ/áo không được suy thành vi phạm.** Mặc định cần 5 trong 8 frame gần nhất có nhãn vi phạm và không có nhãn đạt; có thể chỉnh `--confirm-frames`/`--window`. Một ID chỉ sinh một sự kiện mỗi loại; các ID mới có khung người trùng mạnh trong 10 giây được gộp để giảm ảnh lặp (`--dedup-seconds`). Đây là quy tắc thử nghiệm, chưa có số đo báo nhầm/bỏ sót trên góc camera demo.

Ảnh trong `events/` và bản ghi JSONL là đầu vào cho bước database/web sau này. Khi chạy hai model cùng lúc trên Orange Pi, cần export và benchmark **cả model người và model PPE**; checkpoint `.pt` và ByteTrack trên laptop chưa chứng minh tốc độ NPU của hệ thống hoàn chỉnh.

## Quy tắc làm việc

Giữ nguyên split và class order của từng bộ dữ liệu, ghi config, seed, commit, phiên bản runtime và điều kiện đo. Chỉ số validation của Huang–Cheng phản ánh bài toán phát hiện box trên ảnh; kết quả cảnh báo theo người cần được xem xét riêng trên video và góc camera demo.
