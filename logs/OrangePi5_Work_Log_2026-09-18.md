# Orange Pi 5 – Work Log 2026-09-18

## 1. Mục đích của ngày làm việc

Tiếp tục baseline cho hệ thống **Industrial Worker Safety Monitoring** trên Orange Pi 5, tập trung vào hai phần chính:

1. Hoàn thiện kết nối **Ubuntu laptop ↔ Orange Pi 5** để có thể phát triển và deploy model thuận tiện.
2. Thiết lập pipeline **ONNX → RKNN → RK3588S NPU** và xác nhận model YOLOv8n 3-class có thể chạy inference thật trên NPU.

Target cuối ngày:

```text
YOLOv8n best.onnx
        ↓
RKNN-Toolkit2 2.3.2 trên Ubuntu x86_64
        ↓
best_fp16.rknn
        ↓
Orange Pi 5
        ↓
RKNNLite2 2.3.2
        ↓
RK3588S NPU
        ↓
output (1, 7, 8400)
```

---

## 2. Baseline hệ thống sử dụng trong ngày

| Item | Current baseline |
|---|---|
| Board | Orange Pi 5 |
| SoC | RK3588S |
| RAM | 4 GB |
| Board OS | Orange Pi Ubuntu Jammy |
| Board Kernel | Linux 6.1.99-rockchip-rk3588 |
| Camera | OV13855 13MP MIPI CSI |
| Camera node | `/dev/video11` |
| Host OS | Ubuntu 24.04.3 LTS |
| Host architecture | x86_64 |
| Host Python | 3.12.3 |
| RKNN-Toolkit2 | 2.3.2 |
| RKNNLite2 | 2.3.2 |
| librknnrt | 2.3.2 |
| RKNPU driver | 0.9.8 |
| Local Orange Pi IP | `192.168.137.49` |
| Tailscale Orange Pi IP | `100.67.251.37` |

---

## 3. Step 1 – Hoàn thiện kết nối Ubuntu laptop ↔ Orange Pi 5

### Công việc thực hiện

Ubuntu laptop được cấu hình để chia sẻ Internet qua Ethernet cho Orange Pi.

Orange Pi giữ IP local cố định:

```text
Orange Pi: 192.168.137.49
Ubuntu host: 192.168.137.1
```

Kiểm tra SSH local:

```bash
ssh orangepi@192.168.137.49
```

Kiểm tra Internet từ Orange Pi:

```bash
ping -c 3 8.8.8.8
```

Kiểm tra Tailscale:

```bash
tailscale status
```

### Ý nghĩa

Bước này thiết lập một đường kết nối local ổn định giữa máy phát triển và board. Không cần phụ thuộc vào Tailscale khi laptop và Orange Pi đang nối trực tiếp bằng Ethernet.

### Mục đích

- Copy model và source nhanh bằng `scp`.
- SSH vào board từ Ubuntu laptop.
- Cho Orange Pi có Internet để cài package và sử dụng Tailscale.
- Giữ khả năng remote từ các thành viên khác thông qua Tailscale.

### Kết quả

```text
Local SSH      : PASS
Internet       : PASS
Tailscale      : PASS
```

---

## 4. Step 2 – Thiết lập RKNN-Toolkit2 trên Ubuntu x86_64

### Công việc thực hiện

Kiểm tra host:

```bash
uname -m
python3 --version
lsb_release -a
```

Kết quả:

```text
Architecture : x86_64
Python       : 3.12.3
Ubuntu       : 24.04.3 LTS
```

Tạo virtual environment:

```bash
python3 -m venv ~/rknn_toolkit2_env
source ~/rknn_toolkit2_env/bin/activate
```

Cài:

```bash
pip install rknn-toolkit2==2.3.2
```

Test import:

```python
from rknn.api import RKNN
print("RKNN-Toolkit2 import: PASS")
```

### Ý nghĩa

`RKNN-Toolkit2` là tool phía **host PC** dùng để chuyển model AI từ ONNX sang định dạng `.rknn` mà Rockchip NPU có thể sử dụng.

### Mục đích

Tách rõ hai môi trường:

```text
Ubuntu x86_64 host
    → convert / compile model

Orange Pi 5 ARM64
    → load model / inference
```

Việc này giúp không phải compile model trực tiếp trên Orange Pi.

### Kết quả

```text
RKNN-Toolkit2 2.3.2 import: PASS
```

---

## 5. Step 3 – Fix dependency compatibility của RKNN-Toolkit2

### Vấn đề gặp phải

Khi tạo object:

```python
rknn = RKNN(verbose=True)
```

xuất hiện lỗi:

```text
ModuleNotFoundError: No module named 'pkg_resources'
```

### Cách xử lý

Pin lại `setuptools` về version tương thích:

```bash
python -m pip install "setuptools<82"
```

Đồng thời sử dụng ONNX version phù hợp hơn với RKNN-Toolkit2 2.3.2:

```bash
python -m pip install "onnx==1.18.0"
```

### Ý nghĩa

RKNN-Toolkit2 2.3.2 phụ thuộc vào một số API Python package cũ hơn. Nếu host dùng package quá mới, tool có thể import được nhưng fail khi thực sự khởi tạo compiler.

### Mục đích

Đảm bảo môi trường conversion có version dependency ổn định trước khi đánh giá lỗi model.

Điều này giúp phân biệt:

```text
dependency/toolchain issue
        ≠
model conversion issue
```

### Kết quả

```text
pkg_resources : PASS
RKNN object    : PASS
```

---

## 6. Step 4 – Chuẩn bị workspace và kiểm tra model YOLOv8

### Model input

Workspace:

```text
~/DA/rknn_yolov8/
```

Các file chính:

```text
best.onnx
best.pt
classes.txt
data.yaml
model_info.txt
results.png
confusion_matrix.png
```

Model:

```text
YOLOv8n
Input: 640 × 640
Classes:
0 - person
1 - helmet
2 - safety_clothes
```

### Inspect ONNX

Kết quả:

```text
INPUT
images [1, 3, 640, 640]

OUTPUT
output0 [1, 7, 8400]

OPSET
ai.onnx 12
```

### Ý nghĩa

Bước inspect xác định interface thực tế của model trước khi convert.

`[1, 7, 8400]` có ý nghĩa:

```text
1     = batch
7     = 4 bbox values + 3 class scores
8400  = tổng số prediction candidates
```

### Mục đích

Không giả định post-processing giống các model YOLOv8 khác.

Việc biết chính xác input/output giúp chuẩn bị đúng:

- preprocessing
- input layout
- post-processing
- bbox decoding
- class score extraction
- NMS

### Kết quả

```text
ONNX structure verified: PASS
```

---

## 7. Step 5 – Convert ONNX → RKNN FP16

### Công việc thực hiện

Tạo script:

```text
convert_onnx_to_rknn.py
```

Cấu hình chính:

```python
rknn.config(
    mean_values=[[0, 0, 0]],
    std_values=[[255, 255, 255]],
    target_platform="rk3588"
)
```

Build lần đầu theo non-INT8 path:

```python
rknn.build(
    do_quantization=False
)
```

Export:

```python
rknn.export_rknn("best_fp16.rknn")
```

### Ý nghĩa

Đây là bước compiler chuyển graph ONNX sang representation phù hợp với **RKNPU v2 / RK3588**.

Tool thực hiện:

```text
ONNX graph
    ↓
graph optimization
    ↓
operator fusion
    ↓
layout optimization
    ↓
RK3588 NPU compilation
    ↓
RKNN model
```

### Mục đích

Ưu tiên FP16/non-quantized trước để tạo một baseline dễ kiểm chứng.

Chưa dùng INT8 ngay để tránh trộn hai loại vấn đề:

```text
conversion / post-processing problem
vs
quantization accuracy problem
```

### Kết quả

```text
RKNN conversion PASS
Output: best_fp16.rknn
```

Model RKNN khoảng:

```text
7.6 MB
```

Compiler report:

```text
Internal memory ≈ 16.8 MB
Weight memory   ≈ 6.67 MB
```

---

## 8. Step 6 – Deploy model RKNN sang Orange Pi 5

### Công việc thực hiện

Tạo thư mục:

```bash
mkdir -p ~/models/yolov8_ppe
```

Copy:

```bash
scp best_fp16.rknn orangepi@192.168.137.49:~/models/yolov8_ppe/
scp classes.txt model_info.txt orangepi@192.168.137.49:~/models/yolov8_ppe/
```

Trên board:

```text
~/models/yolov8_ppe/
├── best_fp16.rknn
├── classes.txt
└── model_info.txt
```

### Ý nghĩa

Đây là bước tách rõ:

```text
development / conversion machine
        ↓
deployment target
```

Model `.rknn` là artifact deploy thực tế cho Orange Pi.

### Mục đích

Chuẩn bị đúng môi trường runtime trên RK3588S, thay vì chạy inference trên host Ubuntu.

### Kết quả

```text
best_fp16.rknn deployed to Orange Pi: PASS
```

---

## 9. Step 7 – Load model và khởi tạo RK3588S NPU runtime

### Công việc thực hiện

Activate environment:

```bash
source ~/rknn_env/bin/activate
```

Load model:

```python
rknn.load_rknn("best_fp16.rknn")
```

Init runtime:

```python
rknn.init_runtime(
    core_mask=RKNNLite.NPU_CORE_AUTO
)
```

Runtime xác nhận:

```text
RKNNLite        : 2.3.2
librknnrt       : 2.3.2
RKNPU driver    : 0.9.8
target platform : rk3588
target          : RKNPU v2
model layout    : NCHW
static shape    : yes
```

### Ý nghĩa

Load model thành công chưa đủ để chứng minh model chạy trên NPU.

`init_runtime()` là bước kết nối:

```text
Python RKNNLite
      ↓
librknnrt
      ↓
RKNPU kernel driver
      ↓
RK3588S NPU
```

### Mục đích

Xác nhận toàn bộ runtime stack giữa userspace và NPU driver hoạt động đúng.

### Kết quả

```text
RKNN load model : PASS
NPU init runtime: PASS
```

---

## 10. Step 8 – Fix input shape cho RKNNLite inference

### Vấn đề gặp phải

Ban đầu input được tạo:

```python
img = np.zeros((640, 640, 3), dtype=np.uint8)
```

Runtime báo cần input 4D.

### Cách xử lý

Thêm batch dimension:

```python
img = np.zeros((1, 640, 640, 3), dtype=np.uint8)
```

Input phía application:

```text
NHWC = [1, 640, 640, 3]
```

Trong khi model graph gốc:

```text
NCHW = [1, 3, 640, 640]
```

### Ý nghĩa

Input API và internal graph layout không nhất thiết giống nhau.

Bước này làm rõ sự khác biệt giữa:

```text
application image buffer
        ↓
RKNN Runtime
        ↓
internal model tensor layout
```

### Mục đích

Đảm bảo dữ liệu đầu vào được runtime nhận đúng trước khi đánh giá output model.

### Kết quả

```text
RKNN input accepted: PASS
```

---

## 11. Step 9 – NPU smoke test

### Công việc thực hiện

Dùng dummy image:

```python
np.zeros((1, 640, 640, 3), dtype=np.uint8)
```

Chạy:

```python
outputs = rknn.inference(inputs=[img])
```

Kết quả:

```text
Number of outputs: 1
output[0]:
    shape = (1, 7, 8400)
    dtype = float32

NPU inference: PASS
```

### Ý nghĩa

Đây là checkpoint quan trọng nhất trong ngày.

Nó chứng minh pipeline sau đã hoạt động end-to-end:

```text
ONNX
 ↓
RKNN compiler
 ↓
RKNN model
 ↓
RKNNLite
 ↓
librknnrt
 ↓
RKNPU driver
 ↓
RK3588S NPU
 ↓
YOLO output
```

### Mục đích

Xác nhận model **thực sự có thể inference trên NPU** trước khi tích hợp ảnh thật hoặc camera.

Nếu bước này chưa PASS thì chưa nên debug post-processing hoặc camera integration.

### Kết quả

```text
NPU inference: PASS
Output shape : (1, 7, 8400)
```

---

## 12. NPU profiling quan sát được

Trong verbose profiling:

```text
ConvExSwish : NPU ~44.0 ms
Concat      : NPU ~7.5 ms
exSoftmax13 : NPU ~3.1 ms
Split       : NPU ~3.0 ms
```

Tổng operator report:

```text
CPU time   ≈ 2.37 ms
NPU time   ≈ 65.17 ms
Total      ≈ 67.55 ms
```

Python đo toàn bộ call:

```text
~104.4 ms
```

### Ý nghĩa

Profiling cho thấy phần lớn các operator chính đã chạy trên NPU, không phải toàn bộ model fallback về CPU.

### Mục đích

Dùng làm **reference ban đầu**, chưa phải benchmark chính thức.

Hiện tại đang chạy:

```text
verbose/debug mode
single inference
dummy input
không warm-up
```

Do đó chưa dùng số này để kết luận FPS cuối cùng.

---

## 13. Kết quả tổng hợp cuối ngày

| Item | Status |
|---|---|
| Ubuntu ↔ Orange Pi local SSH | PASS |
| Orange Pi Internet sharing | PASS |
| Tailscale | PASS |
| RKNN-Toolkit2 2.3.2 host setup | PASS |
| RKNN dependency fix | PASS |
| ONNX input/output inspection | PASS |
| ONNX → RKNN FP16 conversion | PASS |
| Deploy RKNN to Orange Pi | PASS |
| RKNNLite load model | PASS |
| RK3588S NPU runtime init | PASS |
| Dummy input accepted | PASS |
| NPU inference | PASS |
| Output `(1, 7, 8400)` | PASS |
| Real image detection | NOT STARTED |
| NMS / bounding box post-process | NOT STARTED |
| OV13855 realtime AI | NOT STARTED |
| INT8 quantization | NOT STARTED |
| Formal performance benchmark | NOT STARTED |

---

## 14. Current project pipeline

Tính đến cuối ngày 2026-09-18:

```text
OV13855 Camera bring-up                    ✅
        ↓
1920×1080 NV12 ~30 FPS                    ✅

YOLOv8n training                           ✅
        ↓
best.pt                                    ✅
        ↓
best.onnx                                  ✅
        ↓
ONNX interface verification                ✅
        ↓
RKNN-Toolkit2 2.3.2                        ✅
        ↓
best_fp16.rknn                             ✅
        ↓
Orange Pi 5                                ✅
        ↓
RKNNLite2 + librknnrt + RKNPU driver       ✅
        ↓
RK3588S NPU inference                      ✅
        ↓
output [1, 7, 8400]                        ✅
        ↓
Real image preprocessing                   ⏳
        ↓
BBox decode + confidence + class           ⏳
        ↓
NMS                                        ⏳
        ↓
PPE detection result                       ⏳
        ↓
OV13855 realtime integration               ⏳
```

---

## 15. Next Work

Bước tiếp theo nên thực hiện theo thứ tự:

1. Chuẩn bị một ảnh PPE thật.
2. Implement preprocessing:
   - resize / letterbox về `640×640`
   - BGR → RGB nếu cần
3. Inference ảnh thật bằng `best_fp16.rknn`.
4. Parse output `[1, 7, 8400]`.
5. Decode:
   - bounding box
   - confidence
   - class ID
6. Implement NMS.
7. Vẽ box:
   - `person`
   - `helmet`
   - `safety_clothes`
8. Xuất `result.jpg`.
9. So sánh kết quả RKNN với ONNX/PyTorch.
10. Sau khi ảnh tĩnh đúng mới tích hợp:
    ```text
    OV13855 → V4L2 → RKNN NPU → realtime detection
    ```
11. Sau baseline FP16 ổn định mới thực hiện:
    - INT8 quantization
    - calibration dataset
    - accuracy comparison
    - latency / FPS / memory benchmark
    - Person–PPE Association

---

## 16. Kết luận ngày 2026-09-18

Mục tiêu quan trọng nhất hôm nay đã hoàn thành:

> **Model YOLOv8n 3-class đã được convert từ ONNX sang RKNN và inference thành công trên RK3588S NPU của Orange Pi 5.**

Baseline hiện tại đủ ổn định để chuyển sang giai đoạn **real-image validation và post-processing** trong buổi làm việc tiếp theo.
