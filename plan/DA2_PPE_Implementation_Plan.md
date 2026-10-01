# Kế hoạch Đồ án 2 — giám sát PPE trên Orange Pi 5

## Phạm vi đã chốt

Demo giám sát công nhân ở **góc camera cố định và khoảng cách gần**. Mỗi người phải đội mũ bảo hộ và mặc áo phản quang. Hệ thống cần theo dõi người, cảnh báo thiếu mũ/áo đủ ổn định, lưu ảnh minh chứng và cho xem kết quả. Bài toán nhận người ở rất xa trên video 4K không phải tiêu chí bắt buộc của Đồ án 2.

Model PPE chính là YOLOv8n đã train trên Huang–Cheng, bốn lớp `Helmet`, `NoHelmet`, `NoVest`, `Vest`, `imgsz=640`. Checkpoint: `ai/automation/runs/2026-09-30_huang_cheng_yolov8n_baseline_80ep/weights/best.pt`. Dataset này không có `Person`; ứng dụng laptop dùng checkpoint YOLOv8n COCO riêng để phát hiện người và ByteTrack để giữ ID qua frame. Các baseline SFCHD, CHV và Construction Site Safety được lưu để đối chiếu, không còn là luồng demo chính.

## Quy tắc cảnh báo

- Chỉ kết luận **thiếu mũ** khi có box `NoHelmet` gán được cho vùng đầu của một người; tương tự `NoVest` cho vùng thân. Không thấy `Helmet`/`Vest` là **chưa rõ**, không phải vi phạm.
- Box PPE khớp mơ hồ với nhiều người hoặc xuất hiện nhãn có/không mâu thuẫn được đánh dấu **chưa rõ**.
- Một vi phạm phải lặp lại qua nhiều frame trước khi lưu ảnh. Một ID chỉ tạo một sự kiện cho mỗi loại; gộp thêm các sự kiện cùng loại, cùng vị trí khi tracker đổi ID trong thời gian ngắn. Đây là quy tắc ban đầu, cần thử tại góc demo thật.
- ID chỉ là mã theo dõi tạm thời trong một lần chạy, không xác định danh tính con người.

## Các mốc thực hiện

| Mốc | Công việc | Điều kiện hoàn thành |
|---|---|---|
| 1. Ứng dụng laptop | Chạy hai model trên video/camera; tracking, gán PPE, xác nhận nhiều frame và lưu ảnh/sự kiện. | Có video với khung/ID/trạng thái; sự kiện JSONL và ảnh người vi phạm, không lưu lặp rõ ràng. Bản đầu nằm trong `app/`. |
| 2. Góc camera demo | Chọn vị trí, khoảng cách, ánh sáng; thử người mặc đủ, thiếu mũ, thiếu áo, thiếu cả hai, nhiều người và che khuất. Chốt `imgsz`, ngưỡng tin cậy, thời gian xác nhận. | Các ca demo gần được kiểm tra bằng mắt, ghi lỗi cụ thể và sửa quy tắc. Không dùng chín video `data/Test/` để huấn luyện khi vẫn dùng để thử nghiệm. |
| 3. Orange Pi 5 | Export cả model người và model PPE sang RKNN; kiểm box/lớp trước và sau export. Chạy camera OV13855 qua NPU; đo tổng thời gian capture, tiền xử lý, hai lần inference, hậu xử lý và tracking. | Camera tạo được trạng thái và sự kiện trên board; ghi FPS thực, RAM, nhiệt độ và giới hạn của cấu hình đã chọn. Bắt đầu với FP16, chỉ thử INT8 sau khi có bản đúng. |
| 4. Lưu trữ và web | Chuyển JSONL/ảnh sang lưu trữ bền vững; web hiển thị hình camera, danh sách sự kiện và ảnh. | Sự kiện còn sau khi khởi động lại; truy cập được giao diện demo trong mạng nội bộ. |
| 5. Báo cáo và nộp | Mô tả dữ liệu, kiến trúc hai model, cách gán PPE/tracking, demo và các trường hợp lỗi. Ghi rõ giới hạn về khoảng cách và che khuất. | Có hướng dẫn chạy lại, số đo board, ảnh/video demo và báo cáo. |

Huang–Cheng hiện có train/validation, không có ảnh test riêng; các chỉ số trong bảng train là **validation**, không được gọi là độ chính xác cảnh báo của ứng dụng. Nhóm đã bỏ quy trình gán nhãn thủ công 27 khung hình; nếu không có nhãn video độc lập thì chỉ mô tả đánh giá video dưới dạng kiểm tra định tính, không tính Precision/Recall cảnh báo từ cảm nhận.
