# Hướng dẫn step-by-step cho Thành viên 2

## Edge Deployment and System Lead

**Đề tài:** PPE Non-compliance Detection trên Orange Pi 5  
**Phần cứng đích:** Orange Pi 5, RK3588S NPU, camera OV13855 13 MP MIPI CSI  
**Phạm vi phụ trách:** board, camera, RKNN, NPU profiling, Person–PPE Association, runtime, benchmark và ứng dụng demo.

---

## 1. Mục tiêu cuối cùng

Thành viên 2 phải hoàn thành pipeline:

```text
OV13855
  -> MIPI CSI / RKISP / V4L2
  -> Lấy frame
  -> Resize + Letterbox + Chuẩn hóa
  -> RK3588S NPU inference
  -> Decode + NMS
  -> Person–PPE Association
  -> Xác định vi phạm
  -> Hiển thị + Snapshot + Log sự kiện
```

Kết quả không chỉ là “model chạy được”. Cần chứng minh bằng số liệu:

- Camera hoạt động ổn định.
- Model chạy thật trên NPU.
- Đo được latency, FPS, RAM và tỷ lệ rớt frame.
- Xác định được bottleneck nằm ở capture, preprocess, NPU hay postprocess.
- Ứng dụng nhận camera thật và sinh sự kiện vi phạm PPE.

---

## 2. Nguyên tắc thực hiện

1. Làm từng tầng và kiểm tra từng tầng độc lập.
2. Không tích hợp toàn bộ hệ thống ngay từ đầu.
3. Không làm INT8 trước khi model FP16 chạy đúng.
4. Không đo hiệu năng khi kết quả model còn sai.
5. Không dùng độ phân giải 13 MP trực tiếp làm input model nếu không có mục đích cụ thể.
6. Mỗi bước phải giữ lại cấu hình, lệnh chạy, log và kết quả.
7. Cùng một model phải dùng cùng input, preprocessing và postprocessing khi so sánh PC với NPU.

---

## 3. Công cụ và thiết bị cần chuẩn bị

### 3.1. Phần cứng

- Orange Pi 5.
- Nguồn đúng chuẩn và đủ công suất cho board.
- Thẻ nhớ hoặc eMMC chứa hệ điều hành.
- Camera OV13855.
- Adapter camera đúng loại dành cho Orange Pi 5.
- Cáp FPC đúng loại và đúng chiều tiếp xúc.
- Màn hình hoặc kết nối SSH từ máy tính.
- Tản nhiệt/quạt cho board khi benchmark dài.

### 3.2. Máy tính phát triển

- Máy tính Ubuntu x86_64.
- Git và Python virtual environment.
- RKNN-Toolkit2 để chuyển ONNX sang RKNN.
- ONNX Runtime để kiểm tra model trước khi chuyển đổi.
- Một tập ảnh kiểm tra cố định.
- Calibration dataset khi bắt đầu INT8.

### 3.3. Phần mềm trên Orange Pi 5

- OS image có hỗ trợ Orange Pi 5, camera OV13855, RKISP và NPU.
- V4L2 utilities.
- Media Controller utilities.
- GStreamer hoặc FFmpeg/OpenCV.
- RKNN Runtime hoặc RKNN-Toolkit-Lite2.
- Công cụ theo dõi CPU, RAM và nhiệt độ.

> RKNN-Toolkit2 chạy trên máy tính để chuyển model. Orange Pi 5 dùng RKNN Runtime C/C++ hoặc RKNN-Toolkit-Lite2 Python để inference. Không nên dùng board để train model.

---

## 4. Cấu trúc thư mục đề xuất

```text
project/
  docs/
    board_info.md
    camera_bringup.md
    rknn_environment.md
    issue_log.md
  deployment/
    onnx/
    rknn/
    convert/
    python_runtime/
    cpp_runtime/
  app/
    camera/
    preprocess/
    inference/
    postprocess/
    association/
    event/
  benchmark/
    configs/
    scripts/
    results/
  samples/
    images/
    videos/
```

**Ý nghĩa:** Tách model, runtime, application và kết quả benchmark để dễ truy vết lỗi.  
**Đầu ra:** Repository có cấu trúc thống nhất trước khi viết code.

---

# PHẦN A — BRING-UP ORANGE PI 5 VÀ CAMERA

## Bước 1. Kiểm kê và ghi nhận cấu hình phần cứng

### Mục đích

Biết chính xác phiên bản board, RAM, thiết bị lưu trữ, adapter và camera đang sử dụng. Thông tin này cần cho báo cáo và xử lý lỗi tương thích.

### Thực hiện

1. Chụp ảnh board, camera, adapter và hai đầu cáp FPC.
2. Ghi lại:
   - Model board và dung lượng RAM.
   - Loại lưu trữ: microSD hay eMMC.
   - Model camera: OV13855.
   - Cổng MIPI CSI được sử dụng.
   - Loại adapter và cáp FPC.
   - Loại nguồn và hệ thống tản nhiệt.
3. Tạo `docs/board_info.md`.

### Đầu vào

Orange Pi 5 và toàn bộ phụ kiện thực tế.

### Đầu ra

Một bảng cấu hình phần cứng và ảnh kết nối.

### Điều kiện hoàn thành

Có thể nhìn tài liệu và xác định chính xác mọi thành phần đang dùng.

---

## Bước 2. Cài hệ điều hành và tạo baseline môi trường

### Mục đích

Tạo môi trường Linux ổn định trước khi xử lý camera và NPU. Nếu OS, kernel hoặc driver thay đổi giữa các lần đo thì kết quả benchmark không còn công bằng.

### Thực hiện

1. Cài OS image phù hợp với Orange Pi 5.
2. Khởi động board và thiết lập mạng/SSH.
3. Ghi lại thông tin hệ thống:

```bash
cat /etc/os-release
uname -a
lscpu
free -h
df -h
```

4. Ghi lại kernel, OS image và ngày cài đặt trong `docs/board_info.md`.
5. Không tự nâng kernel sau khi camera và NPU đã hoạt động, trừ khi có lý do và có backup.

### Đầu vào

Orange Pi 5 và OS image.

### Đầu ra

Board khởi động được, truy cập SSH được và có thông tin phiên bản hệ thống.

### Điều kiện hoàn thành

- Boot ổn định ít nhất ba lần.
- SSH hoạt động.
- Không có lỗi nguồn hoặc reboot bất thường.

---

## Bước 3. Kết nối OV13855 đúng cách

### Mục đích

Tránh trường hợp camera không được nhận do sai adapter, sai cổng hoặc ngược chiều cáp.

### Thực hiện

1. Tắt nguồn Orange Pi 5 hoàn toàn.
2. Đối chiếu tài liệu adapter để xác định đúng cổng dành cho OV13855.
3. Kiểm tra chiều mặt tiếp xúc của hai đầu cáp FPC.
4. Gắn cáp chắc chắn vào khóa connector.
5. Kiểm tra lại bằng mắt trước khi cấp nguồn.
6. Chụp ảnh kết nối và thêm vào `docs/camera_bringup.md`.

### Đầu vào

OV13855, adapter camera và cáp FPC.

### Đầu ra

Camera được kết nối vật lý đúng và có ảnh đối chứng.

### Điều kiện hoàn thành

Đúng camera, đúng adapter, đúng cổng và đúng chiều cáp.

---

## Bước 4. Kiểm tra kernel, Device Tree, CSI và RKISP

### Mục đích

Xác nhận Linux đã nhận đủ chuỗi phần cứng: sensor → CSI receiver → ISP. Có `/dev/video*` không đồng nghĩa node đó chắc chắn là camera OV13855.

### Thực hiện

1. Khởi động board sau khi kết nối camera.
2. Kiểm tra log liên quan:

```bash
dmesg | grep -Ei "ov13855|camera|csi|mipi|rkisp|isp"
```

3. Liệt kê thiết bị media và video:

```bash
ls -l /dev/media* /dev/video* 2>/dev/null
v4l2-ctl --list-devices
```

4. Kiểm tra media graph. Thử lần lượt `/dev/media0`, `/dev/media1`, ...:

```bash
media-ctl -p -d /dev/media0
```

5. Xác định trong graph có sensor OV13855, CSI và RKISP hay không.
6. Nếu không thấy sensor:
   - Kiểm tra lại cáp và adapter.
   - Kiểm tra OS image có driver OV13855 hay không.
   - Kiểm tra Device Tree/overlay đã bật đúng camera chưa.
   - Lưu toàn bộ `dmesg` trước khi thay đổi cấu hình.

### Đầu vào

Board đã boot và camera đã kết nối.

### Đầu ra

- Log phát hiện sensor.
- Media graph.
- Danh sách video node.

### Điều kiện hoàn thành

Media graph thể hiện được đường đi từ OV13855 đến RKISP và có capture node phù hợp.

---

## Bước 5. Xác định đúng video node và cấu hình camera

### Mục đích

Rockchip ISP có thể tạo nhiều `/dev/videoX`. Bước này xác định node nào dùng để lấy frame chính và node đó hỗ trợ format, độ phân giải, FPS nào.

### Thực hiện

1. Với từng node nghi ngờ, chạy:

```bash
v4l2-ctl -d /dev/videoX --all
v4l2-ctl -d /dev/videoX --list-formats-ext
```

2. Ghi lại:
   - Tên node.
   - Pixel format.
   - Resolution.
   - FPS hỗ trợ.
3. Không mặc định `/dev/video0` là node đúng.
4. Chọn trước một cấu hình thử nghiệm, ưu tiên 1920×1080 hoặc 1280×720 ở FPS ổn định.

### Đầu vào

Danh sách `/dev/videoX` từ bước 4.

### Đầu ra

Bảng ánh xạ video node → chức năng → format → resolution → FPS.

### Điều kiện hoàn thành

Xác định được một node có thể stream hình ảnh ổn định.

---

## Bước 6. Capture ảnh/video và kiểm tra độ ổn định

### Mục đích

Chứng minh camera không chỉ được kernel nhận mà thực sự truyền được frame đúng màu, đúng hướng và không rớt frame nghiêm trọng.

### Thực hiện

1. Dùng cấu hình thực tế lấy từ `--list-formats-ext`.
2. Kiểm tra stream bằng V4L2 hoặc GStreamer.
3. Ví dụ kiểm tra 300 frame bằng V4L2:

```bash
v4l2-ctl -d /dev/videoX \
  --set-fmt-video=width=1920,height=1080,pixelformat=NV12 \
  --stream-mmap=3 --stream-count=300 --stream-to=capture.nv12
```

4. Nếu node không hỗ trợ `NV12`, thay bằng format được liệt kê thực tế.
5. Kiểm tra thêm:
   - Màu sắc có đúng không.
   - Hình có bị lật hoặc xoay không.
   - Exposure có ổn định không.
   - FPS thực tế.
   - Có timeout hoặc dropped frame không.
6. Chạy stability test tối thiểu 10 phút ở cấu hình dự kiến dùng cho demo.

### Đầu vào

Video node và cấu hình được chốt ở bước 5.

### Đầu ra

- Ảnh hoặc video mẫu.
- Log FPS.
- Báo cáo stability test.

### Điều kiện hoàn thành

- Stream liên tục ít nhất 10 phút.
- Hình ảnh quan sát được và màu hợp lý.
- Ghi được FPS và số lỗi/rớt frame.

---

## Bước 7. Chốt camera profile cho toàn bộ project

### Mục đích

Giữ input camera nhất quán giữa các lần benchmark. Độ phân giải camera thay đổi sẽ làm preprocess time, memory bandwidth và end-to-end FPS thay đổi.

### Thực hiện

Tạo một file cấu hình, ví dụ:

```yaml
camera: OV13855
device: /dev/videoX
capture_width: 1920
capture_height: 1080
capture_fps: 30
pixel_format: NV12
model_width: 640
model_height: 640
```

Chỉ thay các giá trị trên bằng thông số đã kiểm chứng trên board.

### Đầu vào

Kết quả ổn định từ bước 6.

### Đầu ra

`benchmark/configs/camera_ov13855.yaml`.

### Điều kiện hoàn thành

Mọi lần benchmark sau đó đọc cùng một camera profile.

---

# PHẦN B — BRING-UP NPU VÀ RKNN

## Bước 8. Kiểm tra NPU driver trên Orange Pi 5

### Mục đích

Xác nhận kernel đã có RKNPU driver trước khi cài runtime và chạy model.

### Thực hiện

```bash
dmesg | grep -Ei "rknpu|npu"
lsmod | grep -Ei "rknpu|npu"
```

Ghi lại phiên bản driver nếu log hoặc API cung cấp. Việc có tên module trong `lsmod` chỉ là kiểm tra ban đầu; bằng chứng cuối cùng là model mẫu inference thành công trên NPU.

### Đầu vào

Orange Pi 5 đã cài OS.

### Đầu ra

Log trạng thái NPU driver.

### Điều kiện hoàn thành

Không có lỗi khởi tạo NPU và có thể chuyển sang chạy RKNN sample.

---

## Bước 9. Thiết lập môi trường RKNN trên máy tính

### Mục đích

Chuẩn bị môi trường chuyển model từ ONNX sang `.rknn` cho RK3588S.

### Thực hiện

1. Dùng Ubuntu x86_64 trên máy tính.
2. Tạo Python virtual environment riêng.
3. Clone repository chính thức `airockchip/rknn-toolkit2`.
4. Đọc Quick Start tương ứng với phiên bản đang dùng.
5. Cài đúng wheel RKNN-Toolkit2 phù hợp với Python và Ubuntu.
6. Ghi lại:
   - Python version.
   - RKNN-Toolkit2 version.
   - ONNX version.
   - Commit/tag của repository.

### Đầu vào

Máy tính Ubuntu và repository RKNN chính thức.

### Đầu ra

Môi trường Python import được RKNN Toolkit.

### Điều kiện hoàn thành

Một script Python tối thiểu có thể import RKNN API mà không báo lỗi.

> Không cài wheel ngẫu nhiên từ nguồn không rõ ràng. Phiên bản Toolkit, Runtime và driver cần được ghi lại để xử lý lỗi tương thích.

---

## Bước 10. Cài RKNN Runtime trên Orange Pi 5

### Mục đích

Cho phép ứng dụng trên board nạp model `.rknn` và gửi inference xuống NPU.

### Thực hiện

Chọn một trong hai hướng:

| Hướng | Khi dùng | Ý nghĩa |
|---|---|---|
| RKNN-Toolkit-Lite2 Python | Prototype nhanh | Dễ debug và tích hợp ban đầu |
| RKNN Runtime C/C++ | Demo hoàn chỉnh | Kiểm soát tốt hơn latency, memory và pipeline |

Trình tự đề xuất:

1. Bắt đầu với Python để chứng minh model chạy đúng.
2. Chuyển sang C/C++ khi pipeline đã ổn định và cần tối ưu.
3. Ghi phiên bản runtime vào `docs/rknn_environment.md`.

### Đầu vào

Orange Pi 5 có NPU driver.

### Đầu ra

Runtime được cài và import/link thành công.

### Điều kiện hoàn thành

Board có thể khởi tạo RKNN runtime mà không báo lỗi phiên bản.

---

## Bước 11. Chạy một model mẫu chính thức trên NPU

### Mục đích

Tách lỗi môi trường khỏi lỗi model của nhóm. Nếu model mẫu chính thức chưa chạy được thì chưa nên xử lý model PPE.

### Thực hiện

1. Dùng một ví dụ từ RKNN Model Zoo có hỗ trợ RK3588, chẳng hạn MobileNet hoặc YOLO nhỏ.
2. Chuyển model theo hướng dẫn chính thức hoặc dùng artifact mẫu phù hợp.
3. Copy `.rknn`, ảnh test và chương trình runtime sang Orange Pi 5.
4. Chạy inference.
5. Lưu:
   - Console log.
   - Output detection/classification.
   - Thời gian inference nếu sample cung cấp.
   - Phiên bản Toolkit/Runtime/driver.

### Đầu vào

Model mẫu chính thức và ảnh test.

### Đầu ra

Kết quả inference mẫu trên NPU.

### Điều kiện hoàn thành

- Runtime nạp được model.
- Inference thành công.
- Kết quả đầu ra hợp lý.
- Có log chứng minh model chạy trên target RK3588.

---

# PHẦN C — DEPLOY BASELINE PPE

## Bước 12. Chốt interface với Thành viên 1

### Mục đích

Tránh tình trạng Thành viên 1 thay đổi model hoặc preprocessing làm code deployment bị sai.

### Cần chốt

| Mục | Ví dụ thông tin cần cung cấp |
|---|---|
| Model input | NCHW/NHWC, kích thước, dtype |
| Color format | RGB hay BGR |
| Preprocessing | Resize/letterbox, scale, mean/std |
| Output tensor | Số tensor, shape và ý nghĩa |
| Classes | person, helmet, vest hoặc mapping khác |
| Postprocessing | Decode, confidence threshold, NMS |
| Model artifact | ONNX opset và commit tương ứng |
| Test data | 20–100 ảnh cố định và expected outputs |

### Đầu vào

ONNX baseline và thông tin từ Thành viên 1.

### Đầu ra

`docs/model_interface.md`.

### Điều kiện hoàn thành

Hai thành viên dùng cùng một định nghĩa input/output và bộ ảnh test.

---

## Bước 13. Kiểm tra ONNX trên máy tính

### Mục đích

Đảm bảo model ONNX đúng trước khi quy lỗi cho RKNN.

### Thực hiện

1. Chạy model bằng ONNX Runtime.
2. Chạy trên tập ảnh test cố định.
3. Lưu raw tensor output và detection sau NMS.
4. So sánh với kết quả framework gốc của Thành viên 1.
5. Nếu kết quả sai, sửa export hoặc preprocessing trước khi convert RKNN.

### Đầu vào

Model ONNX, ảnh test và expected outputs.

### Đầu ra

ONNX validation report.

### Điều kiện hoàn thành

Kết quả ONNX gần tương đương model gốc trên cùng input.

---

## Bước 14. Convert ONNX sang RKNN FP16

### Mục đích

Tạo baseline NPU chưa lượng tử hóa. Đây là mốc để tách lỗi conversion khỏi sai số INT8.

### Thực hiện

Trong script conversion, thực hiện tuần tự:

1. Khởi tạo RKNN object.
2. Cấu hình target platform là RK3588.
3. Cấu hình input normalization đúng với model.
4. Load ONNX.
5. Build với quantization tắt.
6. Export file `.rknn`.
7. Lưu đầy đủ conversion log.

Pseudo-flow:

```text
rknn.config(target_platform="rk3588", ...)
-> rknn.load_onnx(...)
-> rknn.build(do_quantization=False)
-> rknn.export_rknn(...)
```

### Đầu vào

ONNX đã được xác nhận đúng.

### Đầu ra

- Model RKNN FP16.
- Conversion script.
- Conversion log.

### Điều kiện hoàn thành

Không có lỗi unsupported operator và sinh được `.rknn`.

---

## Bước 15. Kiểm tra tính đúng của RKNN FP16

### Mục đích

Xác nhận model RKNN không chỉ chạy được mà còn cho kết quả đúng.

### Thực hiện

1. Chạy cùng tập ảnh đã dùng ở bước 13.
2. Giữ nguyên resize, letterbox, color conversion và threshold.
3. So sánh ba tầng:
   - Model gốc.
   - ONNX Runtime.
   - RKNN trên Orange Pi 5.
4. So sánh:
   - Raw output tensor nếu có thể.
   - Số detection.
   - Class.
   - Confidence.
   - Bounding box.
5. Lưu các ảnh có kết quả khác biệt để phân tích.

### Đầu vào

ONNX, RKNN FP16 và tập ảnh cố định.

### Đầu ra

`reports/rknn_fp16_correctness.md`.

### Điều kiện hoàn thành

Không có sai lệch bất thường do preprocessing, layout hoặc postprocessing.

---

## Bước 16. Tạo baseline performance trên NPU

### Mục đích

Tạo mốc định lượng để sau này chứng minh INT8, custom model hoặc Hardware-aware NAS có cải thiện thật.

### Quy trình đo

1. Cố định model, input size và precision.
2. Warm-up trước khi đo.
3. Chạy nhiều lần, không lấy kết quả của một lần duy nhất.
4. Báo cáo median và P95 latency nếu có thể.
5. Tách riêng:
   - Preprocess.
   - NPU inference.
   - Decode/NMS.
   - Person–PPE Association.
   - End-to-end.
6. Theo dõi CPU, RAM và nhiệt độ.
7. Chạy stability test dài để kiểm tra thermal throttling.

### Metric tối thiểu

| Metric | Ý nghĩa |
|---|---|
| NPU latency | Thời gian phần model chạy trên NPU |
| End-to-end latency | Camera đến kết quả cuối cùng |
| Throughput/FPS | Số frame xử lý mỗi giây |
| P95 latency | Độ trễ của các frame chậm |
| CPU usage | Mức tải phần ngoài NPU |
| RAM usage | Bộ nhớ ứng dụng sử dụng |
| Dropped frames | Mức ổn định của pipeline camera |
| Temperature | Phát hiện giảm xung do nhiệt |

### Đầu ra

NPU baseline report với bảng số liệu và cấu hình đầy đủ.

### Điều kiện hoàn thành

Người khác có thể dùng config, model và script để chạy lại phép đo.

---

# PHẦN D — INT8 VÀ PHÂN TÍCH OPERATOR

## Bước 17. Chuẩn bị calibration dataset

### Mục đích

INT8 cần dữ liệu đại diện để ước lượng dải giá trị tensor. Calibration kém có thể làm model nhanh hơn nhưng giảm accuracy mạnh.

### Thực hiện

1. Nhận tập calibration từ Thành viên 1.
2. Bảo đảm tập ảnh có:
   - Người ở nhiều kích thước.
   - Có và không có helmet/vest.
   - Ánh sáng và góc nhìn khác nhau.
   - Cảnh nhiều người và che khuất.
3. Không dùng test set để điều chỉnh model.
4. Tạo manifest đường dẫn ảnh.

### Đầu vào

Dataset đã chốt.

### Đầu ra

Calibration manifest có version.

### Điều kiện hoàn thành

Tập calibration đại diện cho dữ liệu thực tế và tách biệt với test set.

---

## Bước 18. Convert và đánh giá RKNN INT8

### Mục đích

Đánh giá trade-off giữa accuracy, model size, latency và memory.

### Thực hiện

1. Giữ nguyên ONNX, input size và preprocessing của FP16 baseline.
2. Build RKNN với quantization bật và dùng calibration manifest.
3. Chạy lại tập test cố định.
4. So sánh FP16 và INT8:
   - Accuracy/mAP.
   - NPU latency.
   - End-to-end FPS.
   - Model size.
   - RAM.
5. Không kết luận INT8 tốt hơn nếu chỉ giảm file size nhưng accuracy giảm không chấp nhận được.

### Đầu vào

ONNX baseline và calibration dataset.

### Đầu ra

- RKNN INT8.
- INT8 conversion log.
- Bảng FP16 vs INT8.

### Điều kiện hoàn thành

Có số liệu cho cả accuracy và performance, không chỉ có latency.

---

## Bước 19. Lập operator compatibility log

### Mục đích

Tạo dữ liệu thực nghiệm cho Hardware-aware NAS. Search space chỉ nên chứa operator/block convert và chạy ổn định trên RK3588S.

### Thực hiện

Với mỗi model/candidate:

1. Lưu danh sách operator ONNX.
2. Lưu conversion log.
3. Ghi operator nào:
   - Convert thành công.
   - Bị thay đổi/fuse.
   - Gây warning.
   - Không được hỗ trợ.
4. Với các block quan trọng, tạo micro-model để đo latency riêng.
5. Đo ở các shape/resolution đại diện thay vì kết luận operator có một latency cố định.

### Bảng ghi nhận

| Operator/block | Input shape | Precision | Convert | Chạy NPU | Latency | Ghi chú |
|---|---|---|---|---|---:|---|
| Conv 3×3 | TBD | FP16 | TBD | TBD | TBD | |
| Depthwise Conv | TBD | FP16 | TBD | TBD | TBD | |
| Concat | TBD | FP16 | TBD | TBD | TBD | |
| Resize | TBD | FP16 | TBD | TBD | TBD | |

### Đầu ra

Operator whitelist/blacklist và latency lookup table.

### Điều kiện hoàn thành

Thành viên 1 có thể dùng kết quả này để giới hạn NAS search space.

---

# PHẦN E — PERSON–PPE ASSOCIATION

## Bước 20. Xây baseline association

### Mục đích

Detector chỉ cho biết vị trí person, helmet và vest. Association xác định PPE thuộc về người nào, đặc biệt khi có nhiều người trong ảnh.

### Thực hiện

1. Nhận bounding box sau NMS.
2. Với mỗi person box, tạo:
   - Head region ở phần trên.
   - Upper-body region ở phần giữa.
3. Helmet được ghép khi nằm hợp lý trong head region.
4. Vest được ghép khi nằm hợp lý trong upper-body region.
5. Dùng IoA, containment hoặc khoảng cách tâm làm score.
6. Không cho một PPE được gán cho nhiều người.
7. Sinh trạng thái:

```text
COMPLIANT
NO_HELMET
NO_VEST
NO_HELMET_AND_NO_VEST
```

### Đầu vào

Bounding box person, helmet và vest.

### Đầu ra

Association module và trạng thái PPE của từng person.

### Điều kiện hoàn thành

Mỗi người có `person_id`, box và trạng thái PPE riêng.

---

## Bước 21. Đánh giá association

### Mục đích

Chứng minh thuật toán không chỉ hoạt động trên vài ảnh demo.

### Thực hiện

1. Tạo tập kiểm tra association gồm:
   - Một người.
   - Nhiều người đứng gần nhau.
   - Người bị che khuất.
   - PPE nhỏ hoặc nằm sát người khác.
2. Gán expected result.
3. Đo tỷ lệ association đúng và phân tích lỗi.
4. Chỉ thêm tracking nếu cần ổn định trạng thái qua nhiều frame.

### Đầu ra

Association test report và error cases.

### Điều kiện hoàn thành

Có metric và ảnh minh họa cho trường hợp đúng/sai.

---

# PHẦN F — ỨNG DỤNG VÀ BENCHMARK END-TO-END

## Bước 22. Tích hợp pipeline theo từng tầng

### Mục đích

Giảm độ khó debug bằng cách tích hợp tuần tự.

### Thứ tự bắt buộc

1. Video file → preprocess → RKNN → postprocess.
2. Camera → hiển thị frame, chưa chạy AI.
3. Camera → RKNN → detection overlay.
4. Thêm Person–PPE Association.
5. Thêm xác nhận sự kiện qua nhiều frame nếu cần.
6. Thêm snapshot và local log.
7. Cuối cùng mới thêm giao diện hoặc gửi server.

### Đầu ra

Prototype camera-to-event.

### Điều kiện hoàn thành

Lỗi ở từng tầng có thể được tái hiện độc lập.

---

## Bước 23. Thiết kế event và local log

### Mục đích

Biến kết quả model thành chức năng hệ thống có thể trình diễn và kiểm chứng.

### Event record tối thiểu

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SS",
  "event": "NO_HELMET",
  "confidence": 0.91,
  "person_id": 3,
  "snapshot": "path/to/image.jpg"
}
```

### Thực hiện

1. Chỉ tạo event khi vi phạm tồn tại đủ số frame xác nhận.
2. Dùng cooldown để không ghi hàng trăm event giống nhau.
3. Lưu snapshot có bounding box và trạng thái.
4. Lưu JSON/CSV log để kiểm tra lại.

### Đầu ra

Event module, snapshot và local history.

### Điều kiện hoàn thành

Mỗi event có thời gian, loại vi phạm, người tương ứng và bằng chứng hình ảnh.

---

## Bước 24. Benchmark end-to-end

### Mục đích

Đánh giá hiệu năng của hệ thống thật, không chỉ latency của model.

### Phải đo riêng

```text
T_capture
T_preprocess
T_inference
T_decode_NMS
T_association
T_event_render
T_end_to_end
```

Trong đó:

```text
T_end_to_end ≠ chỉ T_inference
```

### Kịch bản đo tối thiểu

| ID | Input | Resolution model | Precision | Mục đích |
|---|---|---:|---|---|
| E2E-01 | Video cố định | 640×640 | FP16 | Kết quả tái lập |
| E2E-02 | Video cố định | 640×640 | INT8 | So sánh FP16/INT8 |
| E2E-03 | OV13855 | 640×640 | FP16 | Camera thực tế |
| E2E-04 | OV13855 | 640×640 | INT8 | Demo tối ưu |
| E2E-05 | OV13855 dài hạn | 640×640 | Best model | Stability/thermal |

### Đầu ra

End-to-end benchmark report.

### Điều kiện hoàn thành

Có FPS ổn định, latency từng stage, CPU/RAM, nhiệt độ và số dropped frame.

---

## Bước 25. Đóng gói demo và tài liệu tái lập

### Mục đích

Đảm bảo giảng viên hoặc thành viên khác có thể chạy lại hệ thống mà không phụ thuộc vào người viết code.

### Cần chuẩn bị

- `setup.md`: cách chuẩn bị board.
- `camera_bringup.md`: camera node và cấu hình.
- `rknn_environment.md`: version matrix.
- `build.md`: cách build runtime/application.
- `run.md`: lệnh chạy demo.
- `benchmark.md`: quy trình đo.
- Model ONNX và RKNN có version.
- Video demo dự phòng nếu camera gặp vấn đề khi bảo vệ.

### Đầu ra

Một release có source, model, config, log, báo cáo và video demo.

### Điều kiện hoàn thành

Một người khác có thể setup và chạy demo theo tài liệu.

---

## 5. Kế hoạch thực hiện theo tuần của Thành viên 2

| Tuần | Công việc chính | Output bắt buộc |
|---:|---|---|
| 1 | Setup repository, Orange Pi 5, OV13855, Device Tree, RKISP/V4L2 | Board report, media graph, camera stream ổn định |
| 2 | Hỗ trợ dataset/license/script; chốt interface sơ bộ | Dataset utility, interface draft |
| 3 | Xây benchmark harness trên PC/board | Script timing, config và result format |
| 4 | Validate ONNX, thử convert RKNN | ONNX report, RKNN conversion log đầu tiên |
| 5 | Xây Person–PPE Association | Association module và test report |
| 6 | Deploy baseline RKNN FP16/INT8 | Correctness report và NPU baseline |
| 7 | Operator/block microbenchmark | Whitelist, blacklist, latency table |
| 8 | Đo candidate từ Hardware-aware NAS | Candidate latency report và Pareto data |
| 9 | Tích hợp camera, event, snapshot, local log | Demo end-to-end v1 |
| 10 | Stability test, đóng gói và viết báo cáo | Release, benchmark report và video demo |

---

## 6. Quy tắc ghi experiment

Mỗi lần đo tạo một ID:

```yaml
experiment_id: EXP_YYYYMMDD_XXX
git_commit: <commit>
os_image: <name/version>
kernel: <version>
rknn_toolkit: <version>
rknn_runtime: <version>
rknpu_driver: <version>
camera_profile: <config>
model: <name>
model_hash: <hash>
input_size: <width>x<height>
precision: FP16_or_INT8
warmup_runs: 50
measure_runs: 500
```

Các con số warm-up và measure ở trên là cấu hình khởi đầu đề xuất; có thể thay đổi nhưng phải ghi lại.

Mỗi experiment cần có:

- Config.
- Console log.
- Model artifact.
- Accuracy hoặc correctness result.
- Latency/FPS result.
- CPU/RAM/nhiệt độ nếu đo trên board.
- Kết luận `PASS`, `FAIL` hoặc `RETEST`.

---

## 7. Version matrix bắt buộc

| Thành phần | Phiên bản đang dùng | Ghi chú |
|---|---|---|
| Orange Pi OS image | TBD | |
| Linux kernel | TBD | |
| OV13855 driver/DTS | TBD | |
| RKNPU driver | TBD | |
| RKNN-Toolkit2 | TBD | Cài trên PC |
| RKNN Runtime/Lite2 | TBD | Cài trên Orange Pi 5 |
| Python | TBD | |
| ONNX/ONNX Runtime | TBD | |
| OpenCV/GStreamer | TBD | |

**Ý nghĩa:** Nhiều lỗi RKNN xuất phát từ lệch phiên bản Toolkit, Runtime và driver. Bảng này giúp tái hiện và xử lý lỗi.

---

## 8. Checklist xử lý lỗi

### Camera không xuất hiện

1. Tắt nguồn và kiểm tra cáp/adapter/cổng.
2. Kiểm tra `dmesg` có nhận OV13855 không.
3. Kiểm tra Device Tree/overlay.
4. Kiểm tra media graph.
5. Kiểm tra OS image có camera support không.
6. Không sửa application khi kernel chưa nhận sensor.

### Có video node nhưng không có hình

1. Xác nhận đúng node bằng media graph.
2. Kiểm tra format/resolution/FPS được hỗ trợ.
3. Thử stream raw với V4L2.
4. Kiểm tra ISP link và pixel format.
5. Lưu log timeout hoặc dropped frame.

### RKNN không convert được

1. Kiểm tra ONNX bằng checker/runtime.
2. Đọc operator gây lỗi trong conversion log.
3. Tạo model tối thiểu chứa operator nghi ngờ.
4. Thử thay operator/block sau khi thống nhất với Thành viên 1.
5. Không tự ý thay kiến trúc mà không tạo experiment mới.

### RKNN chạy nhưng kết quả sai

1. So sánh cùng một ảnh giữa framework, ONNX và RKNN.
2. Kiểm tra RGB/BGR.
3. Kiểm tra NCHW/NHWC.
4. Kiểm tra scale, mean/std và dtype.
5. Kiểm tra letterbox padding.
6. Kiểm tra output tensor và decode/NMS.
7. Với INT8, kiểm tra calibration dataset.

### NPU nhanh nhưng end-to-end chậm

1. Đo riêng từng stage.
2. Kiểm tra resize/color conversion trên CPU.
3. Kiểm tra số lần copy frame.
4. Kiểm tra decode/NMS và association.
5. Kiểm tra queue camera có gây trễ tích lũy không.
6. Giảm capture resolution về 1080p/720p nếu 13 MP không cần thiết.

---

## 9. Việc cần làm ngay hôm nay

Thực hiện đúng thứ tự sau:

1. Tạo cấu trúc repository.
2. Ghi thông tin OS, kernel và phần cứng vào `board_info.md`.
3. Tắt nguồn và kết nối OV13855 đúng adapter/cáp/cổng.
4. Boot board và lưu `dmesg` liên quan OV13855, CSI, RKISP.
5. Lưu danh sách `media-ctl -p` và `v4l2-ctl --list-devices`.
6. Xác định đúng `/dev/videoX`.
7. Capture thử 300 frame.
8. Chạy stream liên tục 10 phút.
9. Chốt camera profile ban đầu.
10. Sau khi camera PASS mới chuyển sang bring-up NPU và RKNN sample.

### Kết quả tối thiểu cuối ngày

- `board_info.md`.
- `camera_bringup.md`.
- Ảnh/video mẫu từ OV13855.
- Media graph.
- Danh sách format/resolution/FPS.
- Kết luận camera `PASS`, `FAIL` hoặc `RETEST`.

---

## 10. Definition of Done cho phần Thành viên 2

Phần việc được xem là hoàn thành khi:

- OV13855 stream ổn định qua MIPI CSI, RKISP và V4L2.
- Có camera profile cố định và log stability test.
- Một model mẫu chính thức chạy được trên RK3588S NPU.
- Baseline PPE ONNX được convert và chạy đúng dưới dạng RKNN.
- Có kết quả so sánh FP16 và INT8.
- Có benchmark latency/FPS/memory theo từng stage.
- Có operator compatibility log phục vụ Hardware-aware NAS.
- Person–PPE Association có metric kiểm tra.
- Ứng dụng camera-to-event lưu được snapshot và local log.
- Có source, config, model, log, báo cáo và hướng dẫn chạy lại.

---

## 11. Tài liệu tham khảo chính

- RKNN-Toolkit2 chính thức: https://github.com/airockchip/rknn-toolkit2
- RKNN Model Zoo chính thức: https://github.com/airockchip/rknn_model_zoo
- Tài liệu Orange Pi 5: http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_5

Luôn ưu tiên Quick Start và example đi kèm đúng phiên bản RKNN đang sử dụng. Không sao chép lệnh từ tài liệu của phiên bản khác mà chưa kiểm tra version matrix.
