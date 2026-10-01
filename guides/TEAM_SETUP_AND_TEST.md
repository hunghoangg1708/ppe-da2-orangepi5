# Hướng dẫn cài đặt và kiểm thử Đồ án 2

Cập nhật: 2026-10-02. Tài liệu dành cho thành viên nhận repo `ppe-da2-orangepi5` để chạy thử hệ thống giám sát mũ bảo hộ và áo phản quang. Các lệnh dưới đây chạy từ **gốc repo** trên laptop Linux. Nếu chỉ muốn thử model đã train, hãy làm mục 1–4; không cần train lại.

## 1. Trạng thái và luồng hiện tại

```text
Video/camera → YOLOv8n COCO phát hiện người + ByteTrack gán ID
             → YOLOv8n Huang–Cheng phát hiện Helmet/NoHelmet/Vest/NoVest
             → ghép nhãn PPE vào từng người → xác nhận qua nhiều frame
             → lưu video có khung, ảnh người/ảnh toàn cảnh và events.jsonl
```

Hai model là hai file `.pt` riêng. Ứng dụng xử lý chúng **lần lượt trên từng frame**, không phải hai tiến trình GPU chạy đồng thời. ByteTrack giữ ID người qua các frame; luật xác nhận giảm cảnh báo lặp/nhiễu. Nếu không thấy mũ hoặc áo trong một frame, trạng thái có thể là **chưa rõ**, không tự động kết luận vi phạm.

| Thành phần | Hiện có | Giới hạn |
|---|---|---|
| Train và dự đoán 4 baseline | Huang–Cheng, Construction Site Safety 5 lớp, SFCHD 5 lớp, CHV | Mỗi bộ có cách đặt nhãn khác nhau; video dự đoán trực tiếp chưa có ID hay cảnh báo |
| Ứng dụng `app.monitor` trên laptop | Theo dõi người, gán PPE, chụp sự kiện vi phạm | **Chỉ hỗ trợ checkpoint Huang–Cheng 4 lớp**; chưa đánh giá định lượng đầy đủ cảnh báo trên góc demo |
| Orange Pi 5 | Đã thử camera OV13855 và NPU cho model cũ trên ảnh tĩnh | Pipeline **hai model + tracking + cảnh báo** hiện chưa chạy trên board |
| Web/database | Chưa triển khai | Kết quả hiện lưu trong thư mục và JSONL cục bộ |

`Helmet` nghĩa là **mũ bảo hộ** theo nhãn huấn luyện; chưa bảo đảm phân biệt ổn định mọi kiểu mũ thông thường. `Vest` là áo bảo hộ/áo phản quang theo nhãn của bộ Huang–Cheng. Hãy kiểm tra trực quan trên video cùng loại với góc camera dự định demo.

## 2. Clone và cài môi trường

Repo GitHub là private, người tham gia cần được cấp quyền trước khi clone. Môi trường đã dùng để phát triển: Ubuntu/Linux x86_64, Python 3.12, GPU NVIDIA RTX 3050 4 GB; mã dự đoán cũng có thể chạy CPU nếu chọn `device=cpu` (chậm hơn). Cần đủ dung lượng cho các gói PyTorch/CUDA, checkpoint và video.

```bash
git clone https://github.com/hunghoangg1708/ppe-da2-orangepi5.git
cd ppe-da2-orangepi5
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
make test
```

`make test` kiểm tra logic và chuẩn bị dữ liệu bằng Python trong `.venv`; không cần GPU, dataset hay video. Kiểm tra GPU nếu muốn chạy CUDA:

```bash
.venv/bin/python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'không có')"
```

Nếu `CUDA: False`, dùng `device=cpu` trong lệnh YOLO, hoặc `--device cpu` với `app.monitor`. Cấu hình train mặc định dùng GPU `device: 0`; CPU cần sửa cấu hình train tương ứng. Gói `rknn-toolkit2` trong `pyproject.toml` phục vụ bước export NPU trên Linux x86_64; đây không phải môi trường Python chạy trực tiếp trên Orange Pi.

## 3. File cần nhận riêng sau khi clone

Git hiện **không chứa** `.venv`, các checkpoint `*.pt`, ảnh/nhãn dataset raw/processed, video `data/Test/*.mp4`, hoặc kết quả trong `runs/`. Clone thành công chưa đủ để chạy các ví dụ dưới đây. Nhận file từ người phụ trách bằng kênh chia sẻ riêng và đặt **đúng đường dẫn** sau; không đổi tên checkpoint khi chép:

| Mục đích | Đường dẫn tính từ gốc repo |
|---|---|
| Phát hiện người cho `app.monitor` | `yolov8n.pt` |
| PPE Huang–Cheng cho `app.monitor` và so sánh | `ai/automation/runs/2026-09-30_huang_cheng_yolov8n_baseline_80ep/weights/best.pt` |
| Construction Site Safety | `ai/automation/runs/2026-09-27_construction_site_safety_5class_yolov8n_baseline_80ep/weights/best.pt` |
| SFCHD | `ai/automation/runs/2026-09-27_sfchd_5class_yolov8n_baseline_100ep/weights/best.pt` |
| CHV | `ai/automation/runs/2026-09-27_chv_yolov8n_baseline_80ep/weights/best.pt` |
| Video kiểm thử | `data/Test/001.mp4`, `002.mp4`, ... (chỉ chép video cần thử) |

Chỉ chạy `app.monitor` cần **hai checkpoint đầu** và một video hoặc camera. So sánh đủ bốn baseline cần cả bốn `best.pt`. Dự đoán bằng checkpoint đã có **không cần dataset gốc**; chỉ cần dataset nếu muốn train lại. Kiểm tra file trước khi chạy:

```bash
test -f yolov8n.pt && test -f ai/automation/runs/2026-09-30_huang_cheng_yolov8n_baseline_80ep/weights/best.pt && test -f data/Test/009.mp4 && echo 'Đủ file để thử app trên 009.mp4'
```

Nếu cần xác minh file chép đúng phiên bản, hai máy có thể chạy `sha256sum <đường-dẫn-file>` và đối chiếu chuỗi băm; riêng tên `best.pt` không đủ phân biệt các lần train. Không đưa các file nặng lên Git bằng `git add -f` khi chưa thống nhất cách lưu trữ với nhóm.

## 4. Thử ứng dụng chụp vi phạm

Đổi `009.mp4` thành video cần thử. Lệnh dùng mặc định `yolov8n.pt` và checkpoint Huang–Cheng ở mục 3. Dùng `--max-frames 100` để kiểm tra nhanh trước khi chạy hết video:

```bash
.venv/bin/python -m app.monitor --source data/Test/009.mp4 --max-frames 100
.venv/bin/python -m app.monitor --source data/Test/009.mp4
```

Mặc định ứng dụng tự chọn GPU NVIDIA nếu PyTorch thấy CUDA, nếu không sẽ chọn CPU. Có thể đặt rõ `--device 0` hoặc `--device cpu`. Thử webcam với `--source 0`. Tùy chọn `--show` cần màn hình và bản OpenCV có hỗ trợ cửa sổ đồ họa; cài đặt mặc định dùng `opencv-python-headless`, nên nếu cửa sổ không mở được thì hãy xem file `annotated.mp4` đã ghi thay thế.

Mỗi lần chạy tạo thư mục mới theo **tên video và thời điểm**, ví dụ `runs/ppe_monitor/009_20261002_153000/`:

| File | Ý nghĩa |
|---|---|
| `annotated.mp4` | Video có box người, ID, trạng thái `H` (mũ) và `V` (áo); không tạo khi dùng `--no-video` |
| `events.jsonl` | Mỗi dòng JSON là một sự kiện `no_helmet` hoặc `no_vest` |
| `events/*_person.jpg` | Ảnh người bị cảnh báo |
| `events/*_scene.jpg` | Cả frame với box đỏ quanh người bị cảnh báo |

Để xem số sự kiện và thư mục kết quả mới nhất:

```bash
ls -td runs/ppe_monitor/009_* | head -1
wc -l runs/ppe_monitor/009_*/events.jsonl
```

Nếu có nhiều lần chạy, lệnh `wc` liệt kê từng lần; mở đúng thư mục theo thời điểm. Không có ảnh sự kiện **không chứng minh** video không có vi phạm: model có thể bỏ sót hoặc chưa đủ 5/8 frame xác nhận. Khung xanh là đủ bằng chứng đạt; đỏ là có bằng chứng vi phạm; vàng là chưa rõ. Số ID có thể thay đổi khi người bị che/khuất hoặc ra khỏi khung hình. Quy tắc của bài demo: người trong vùng giám sát phải **đội mũ bảo hộ và mặc áo phản quang**.

## 5. So sánh trực tiếp bốn model trên cùng video

Đây là lệnh **dự đoán từng model độc lập** để xem box trên video; nó không chạy tracking, gán PPE theo người hay chụp sự kiện. Thay `DA2_VIDEO=009` một lần cho `001`–`014` (nếu đã nhận video tương ứng). Giữ cùng video, kích thước ảnh và ngưỡng cho một lượt xem đối chiếu. GPU dùng `device=0`; máy không có CUDA đổi cả bốn thành `device=cpu`.

```bash
DA2_VIDEO=009

.venv/bin/yolo detect predict model=ai/automation/runs/2026-09-30_huang_cheng_yolov8n_baseline_80ep/weights/best.pt source=data/Test/${DA2_VIDEO}.mp4 imgsz=640 conf=0.35 device=0 save=True project=runs/model_compare name=${DA2_VIDEO}_huang_cheng

.venv/bin/yolo detect predict model=ai/automation/runs/2026-09-27_construction_site_safety_5class_yolov8n_baseline_80ep/weights/best.pt source=data/Test/${DA2_VIDEO}.mp4 imgsz=640 conf=0.35 device=0 save=True project=runs/model_compare name=${DA2_VIDEO}_construction

.venv/bin/yolo detect predict model=ai/automation/runs/2026-09-27_sfchd_5class_yolov8n_baseline_100ep/weights/best.pt source=data/Test/${DA2_VIDEO}.mp4 imgsz=640 conf=0.35 device=0 save=True project=runs/model_compare name=${DA2_VIDEO}_sfchd

.venv/bin/yolo detect predict model=ai/automation/runs/2026-09-27_chv_yolov8n_baseline_80ep/weights/best.pt source=data/Test/${DA2_VIDEO}.mp4 imgsz=640 conf=0.35 device=0 save=True project=runs/model_compare name=${DA2_VIDEO}_chv
```

Kết quả nằm trong `runs/model_compare/009_huang_cheng/`, `009_construction/`, `009_sfchd/`, `009_chv/`. Nếu chạy lại cùng tên, Ultralytics có thể tạo thư mục thêm hậu tố (`...2`, `...3`); xem dòng `Results saved to ...` trong terminal để biết chính xác. Có thể thêm `exist_ok=True` nếu muốn ghi lại vào thư mục cùng tên.

`conf=0.35` là ngưỡng giữ box có điểm tin cậy từ 0,35 trở lên; giảm xuống `0.25` thường tăng box yếu và cả báo nhầm. Bốn model có **tập lớp khác nhau**: Huang–Cheng không có lớp người, CHV không có lớp rõ ràng cho *không mũ/không áo*, SFCHD dùng lớp quần áo không đồng nghĩa trực tiếp với áo phản quang. Vì vậy không lấy số box hoặc chỉ số mAP trên các dataset khác nhau để kết luận model nào tốt nhất cho demo; hãy xem các tình huống sai trên cùng video/góc camera.

## 6. Chuẩn bị dữ liệu và train lại (tùy chọn)

Chỉ làm khi cần tái tạo hoặc cải thiện model. Dataset gốc cần chuyển riêng vì không nằm trên Git. Các script tạo bản `processed` theo class order/split của từng nguồn; không trộn class ID giữa các bộ. Kiểm tra [data card Huang–Cheng](../data/huang_cheng/DATA_CARD.md), [CHV](../data/chv/DATA_CARD.md) và [SFCHD](../data/sfchd_5class/DATA_CARD.md) trước khi đổi nhãn.

| Dataset | Chỗ đặt dữ liệu gốc | Chuẩn bị / train |
|---|---|---|
| Huang–Cheng | `data/Huang-Cheng/` | `.venv/bin/python scripts/data/prepare_huang_cheng.py` rồi `make train CONFIG=ai/automation/configs/huang_cheng_yolov8n.yaml` |
| Construction Site Safety v30 | `data/construction_site_safety/raw/Construction Site Safety.v30-raw-images_latestversion.yolov8/` | `.venv/bin/python scripts/data/prepare_construction_site_safety_5class.py` rồi `make train CONFIG=ai/automation/configs/construction_site_safety_5class_yolov8n.yaml` |
| CHV | `data/chv/raw/CHV_dataset/CHV_dataset/` | `.venv/bin/python scripts/data/prepare_chv.py` rồi `make train CONFIG=ai/automation/configs/chv_yolov8n.yaml` |
| SFCHD | `data/sfchd/raw/` (`classes.txt`, ảnh, nhãn) | `make prepare-data` rồi `make train CONFIG=ai/automation/configs/sfchd_5class_yolov8n_baseline.yaml` |

Các config train hiện thiết lập GPU `device: 0`, YOLOv8n và giới hạn epoch riêng; early stopping có thể kết thúc trước giới hạn. Kết quả nằm dưới `ai/automation/runs/<run_id>/`, đặc biệt `weights/best.pt`, `metrics.csv`, `config.yaml`, và đánh giá validation/test nếu dataset có split phù hợp. Huang–Cheng chỉ có train/validation, **không có test riêng**; không so trực tiếp mAP của nó với test của dataset khác. Video `data/Test/` giữ làm **kiểm thử độc lập**, không đưa vào train nếu còn dùng chúng để nhận xét chất lượng trên video.

## 7. Cách làm việc chung và lỗi thường gặp

1. Trước khi push, chạy `git status --short`; bảo đảm mã `app/`, `scripts/`, cấu hình, test và tài liệu cần chia sẻ đã được stage/commit. **Hiện có nhiều file mã mới chưa được Git theo dõi**, đặc biệt `app/`, cấu hình ba bộ dữ liệu và tài liệu này; chỉ `git push` mà chưa `git add`/`git commit` thì bạn cùng nhóm sẽ không nhận được chúng. Sau khi xem danh sách, có thể dùng `git add -A`, kiểm tra lại bằng `git diff --cached --stat` và `git diff --cached --check`, rồi mới commit/push. `git status` không hiện file bị `.gitignore` bỏ qua; kiểm tra thêm danh sách checkpoint/video ở mục 3.
2. Ghi lại video, checkpoint, `imgsz`, `conf`, device và thư mục output cho mỗi lần thử. Chỉ đổi một biến khi muốn tìm nguyên nhân khác biệt. Chia sẻ ảnh/video kết quả và các ca báo nhầm/bỏ sót bằng kênh lưu trữ của nhóm, vì `runs/` không lên Git.
3. `FileNotFoundError`: đối chiếu tên video và đường dẫn `.pt` ở mục 3; từ terminal phải đứng ở gốc repo.
4. CUDA unavailable hoặc hết VRAM 4 GB: dùng CPU cho kiểm tra ngắn, giảm `imgsz`, hoặc đóng ứng dụng GPU khác. Tăng `imgsz` giúp người xa có thêm pixel nhưng tốn thời gian và bộ nhớ hơn.
5. `app.monitor` báo checkpoint PPE không đúng lớp: kiểm tra đã dùng Huang–Cheng 4 lớp. Thay đường dẫn sang Construction/SFCHD/CHV **chưa đủ** để ứng dụng chụp vi phạm hiểu nhãn của chúng.
6. MP4 không mở được bằng trình quản lý file: cài/trỏ tới trình phát như VLC; nếu `cv2.VideoCapture` không mở được, kiểm tra codec/file đầu vào. File `.pt` là nhị phân, không mở bằng trình soạn thảo văn bản.

Định hướng tiếp: kiểm tra riêng độ đúng của **sự kiện theo người** trên góc demo gần; sau đó mới chuyển pipeline hai model/tracking sang Orange Pi và làm phần lưu trữ/web. Chỉ số phát hiện box trên ảnh không thay thế cho kiểm tra báo nhầm và bỏ sót trong video.
