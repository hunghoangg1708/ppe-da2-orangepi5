# CHV (Color Helmet and Vest)

- Nguồn chính thức: https://github.com/ZijianWang-ZW/PPE_detection
- Tải `CHV_dataset.zip`: https://drive.google.com/file/d/1fdGn67W0B7ShpBDbbQpUF0ScPQa4DR0a/view?usp=sharing
- Bài báo: https://doi.org/10.3390/s21103478
- Mục đích: thí nghiệm độc lập với dữ liệu mũ và áo phản quang ở công trường.

Theo bài báo, CHV gồm 1.330 ảnh với 6 lớp: `person`, `vest`, mũ xanh dương, đỏ, trắng và vàng. Các tập gốc có 1.064 ảnh train, 133 ảnh validation và 133 ảnh test. Giữ nguyên phân chia này khi chuẩn bị dữ liệu.

ZIP đã được giải nén tại `data/chv/raw/CHV_dataset/CHV_dataset/`. Nhãn gốc là YOLO TXT với thứ tự: `person`, `vest`, mũ xanh dương, đỏ, trắng, vàng. Chạy `scripts/data/prepare_chv.py` để giữ nguyên split gốc và gộp bốn màu mũ vào một lớp `helmet`. Bản train có ba lớp `person`, `vest`, `helmet` ở `data/chv/processed/`; thư mục `raw/` và `processed/` được Git bỏ qua. Cấu hình train: `ai/automation/configs/chv_yolov8n.yaml`.

CHV có nhãn mũ/áo khi nhìn thấy; dữ liệu không có lớp riêng `NO-Hardhat` hoặc `NO-Safety Vest`. Việc kết luận một người thiếu PPE cần bước gán mũ/áo cho từng người và kiểm tra trên video có đáp án.

Để train sau khi đã chuẩn bị dữ liệu:

```bash
make train CONFIG=ai/automation/configs/chv_yolov8n.yaml
```
