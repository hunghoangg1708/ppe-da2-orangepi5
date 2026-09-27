# Kế hoạch triển khai Đồ án 2 — giám sát PPE trên Orange Pi 5

**Mục tiêu DA2:** Camera OV13855 → phát hiện `person`, `helmet`, `safety_clothes`, `self_clothes`, `head` → gán PPE cho từng người → ghi nhận vi phạm → xem camera và sự kiện trên web. Sản phẩm nộp gồm hệ thống demo trực tiếp, báo cáo, số liệu đánh giá và video demo.

**Phạm vi dữ liệu:** Chỉ dùng SFCHD, lọc về 5 lớp trên.

**Nguyên tắc quyết định vi phạm:** `head` là bằng chứng không đội mũ; `self_clothes` là bằng chứng không mặc đồ bảo hộ theo định nghĩa SFCHD. Nếu không phát hiện được mũ/áo thì đánh dấu **không xác định**, không tự kết luận vi phạm. Một người đứng liên tục trước camera chỉ tạo một sự kiện cho mỗi đợt vi phạm; quy tắc ổn định qua nhiều frame và ngưỡng tin cậy được chốt trước khi đo.

| Phase | Cần làm | Đầu ra bắt buộc / điều kiện qua phase | Tham chiếu |
|---|---|---|---|
| **0. Khóa đặc tả và môi trường** | Đồng bộ repo với bản 5 lớp/board mới nhất; kiểm camera, RKNN và luồng đọc ảnh. Chốt định nghĩa hai lớp quần áo, trạng thái **đạt / vi phạm / không xác định**, chức năng web và chỉ số cần đo. | Tài liệu đặc tả ngắn, sơ đồ hệ thống, danh sách kịch bản demo, commit và phiên bản môi trường; camera đọc được ảnh trên board. | [Hướng dẫn board][board-guide], [Data Card SFCHD][data-card] |
| **1. Khóa dữ liệu và bộ kiểm thử** | Kiểm số lượng ảnh/box từng lớp, chất lượng nhãn và danh sách train/val/test; giữ nguyên tập test khi so model. Thu các video camera riêng, gán đáp án **PPE theo từng người** để kiểm phần ứng dụng. | Dataset 5 lớp và bảng phân bố nhãn; danh sách split cố định; bộ video test kèm đáp án, không đưa vào train. Ghi rõ khác biệt giữa split của nhóm và paper. | [Paper SFCHD][sfchd-paper] §IV–V, [Data Card 5 lớp][data-card] |
| **2. Baseline phát hiện 5 lớp** | Train YOLOv8n trước, sau đó YOLOv8s với cùng dữ liệu và cách đánh giá. Chọn model cho demo theo AP từng lớp và tốc độ dự kiến; lưu các trường hợp nhầm `safety_clothes`/`self_clothes`. | Checkpoint, config, log; bảng Precision, Recall, mAP50, mAP50–95 và AP của cả 5 lớp trên **cùng test set**; ảnh ví dụ đúng/sai. Một seed/model đủ để hoàn thành luồng DA2; chạy thêm seed nếu có thời gian để củng cố kết luận cho DATN. | [Data Card 5 lớp][data-card], [Paper SFCHD][sfchd-paper] Table IV–V |
| **3. Triển khai NPU** | Export ONNX → RKNN FP16/INT8; kiểm đầu ra sau chuyển đổi và đo trên Orange Pi 5. Dùng bản có chất lượng đủ cho demo; giữ kết quả INT8 kể cả khi nó kém FP16. | File `.rknn` chạy được trên board; bảng AP trước/sau export, latency NPU, thời gian tiền/hậu xử lý, FPS và thông tin board/runtime. | [Hướng dẫn board][board-guide], [RKNN API Reference][rknn-api] |
| **4. Camera và gán PPE theo người** | Xây luồng OV13855 → NV12/RGB → LetterBox → RKNN → NMS; gán box đầu/mũ vào vùng đầu và box áo vào vùng thân của từng `person`. Theo dõi người qua frame, xử lý nhiều người, che khuất và trường hợp hai nhãn mâu thuẫn. | Video trực tiếp có khung, ID tạm thời và trạng thái PPE cho từng người; bộ ca kiểm thử một người, nhiều người, ra/vào khung, che khuất, không xác định. | [Hướng dẫn board][board-guide]; quy tắc gán và xử lý mâu thuẫn do **nhóm thiết kế**, phải mô tả rõ trong báo cáo |
| **5. Ghi sự kiện và web** | Khi vi phạm ổn định qua nhiều frame, lưu `event_id`, thời gian, loại vi phạm, ID theo dõi, độ tin cậy, phiên bản model và ảnh minh chứng vào database. Web hiển thị camera, danh sách sự kiện, bộ lọc và ảnh; tránh ghi lặp, kiểm dung lượng lưu trữ. | Web truy cập được trong mạng khi board đang chạy; sự kiện và ảnh còn sau khi khởi động lại; mỗi đợt vi phạm chỉ có một bản ghi phù hợp. | Yêu cầu sản phẩm DA2 đã được nhóm xác nhận; đặc tả ở Phase 0 |
| **6. Đánh giá tích hợp và nộp** | Đánh giá riêng **detector** trên SFCHD test và **gán/cảnh báo** trên video có đáp án. Đo FPS thực, latency P95, CPU/RAM/nhiệt độ khi chạy camera liên tục; ghi ca báo nhầm/bỏ sót. Viết báo cáo, quay video demo, lưu cách chạy lại. | Bảng chất lượng 5 lớp; bảng cảnh báo đúng/báo nhầm/bỏ sót và sự kiện trùng; kết quả chạy liên tục; báo cáo, video demo, mã nguồn và hướng dẫn tái lập. | [Kế hoạch ĐA2](../README.md) và đặc tả được khóa ở Phase 0 |

## Thứ tự ưu tiên và mốc sản phẩm

1. **Mốc demo tối thiểu:** một model FP16 chạy camera trực tiếp, gán PPE theo người, ghi sự kiện kèm ảnh và xem được trên web.
2. **Mốc hoàn chỉnh DA2:** đủ hai baseline YOLOv8n/s, phép đo detector và cảnh báo, đánh giá RKNN FP16/INT8, kiểm thử chạy liên tục, báo cáo và video demo.
3. **Dữ liệu giữ cho DATN:** split/test cố định, cấu hình và seed, checkpoint, log, bảng AP từng lớp, số đo latency/tài nguyên trên board và bộ video lỗi. DATN dùng chúng để tìm nút thắt, đề xuất tối ưu và làm ablation.

**Lưu ý khi viết báo cáo:** mAP trên SFCHD chỉ đánh giá box và lớp, không đo đúng/sai của bước gán PPE cho từng người. Bộ video có đáp án ở Phase 1 là nguồn cho chỉ số cảnh báo hệ thống. Split SFCHD hiện tại khác split tác giả, nên không so trực tiếp số mAP của nhóm với số trong paper.

[board-guide]: ../guides/Huong_dan_Thanh_vien_2_OrangePi5_RKNN.md
[data-card]: ../data/sfchd_5class/DATA_CARD.md
[sfchd-paper]: ../references/papers/sfchd_scale_2023yu.pdf
[rknn-api]: ../references/papers/Rockchip_RKNPU_API_Reference_Toolkit2_V2.3.2.pdf
