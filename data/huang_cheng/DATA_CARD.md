# Huang–Cheng PPE, bản người dùng tải về

- Bài báo: https://doi.org/10.1016/j.dib.2025.111988
- Bản tải hiện có: https://universe.roboflow.com/ying2001/20250731-ppe2286-m0ega
- Thư mục nguồn: `data/Huang-Cheng/` (không đưa ảnh và nhãn lên Git).

Bản tải có 2.286 ảnh: 1.829 train và 457 validation. Bốn lớp theo đúng thứ tự file nhãn là `Helmet`, `NoHelmet`, `NoVest`, `Vest`. Không có tập test ảnh riêng. Bài báo Huang–Cheng mô tả cùng số ảnh, phân chia và bốn lớp này, nhưng nguồn tải hiện có là một bản đăng trên Roboflow bởi Ying2001; chưa xác minh nó giống hệt bản lưu trên Mendeley Data của tác giả.

`data/Huang-Cheng/data.yaml` chứa đường dẫn tuyệt đối của máy Windows. Chạy `scripts/data/prepare_huang_cheng.py` để kiểm số lượng, thứ tự lớp, nhãn YOLO và ảnh trùng chính xác, rồi tạo `data/huang_cheng/processed/dataset.yaml` dùng trên máy hiện tại. Script chỉ tạo YAML; không sửa hoặc nhân đôi ảnh.

```bash
.venv/bin/python scripts/data/prepare_huang_cheng.py
make train CONFIG=ai/automation/configs/huang_cheng_yolov8n.yaml
```

Đánh giá tự động sau train dùng **validation**; mọi chỉ số trong `huang_cheng.csv` là `val_*`, không phải kết quả test độc lập. Các video trong `data/Test/` vẫn để riêng cho đánh giá ứng dụng về sau, không dùng để train.

Dataset không có lớp `person` và cũng không đánh dấu cùng một người qua nhiều khung hình. Ứng dụng video cần bộ phát hiện người riêng, bước gán PPE theo người, theo dõi ID và xác nhận qua nhiều khung hình trước khi tạo sự kiện.
