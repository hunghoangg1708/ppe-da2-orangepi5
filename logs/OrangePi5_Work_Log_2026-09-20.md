# Work Log - 2026-09-20

## 1. AI Deployment Knowledge
- Review basic concepts:
  - Loss
  - `.pt`, `.onnx`, `.rknn`
  - PyTorch execution flow
  - RKNN-Toolkit2
  - AI operators: Conv, Add, Sigmoid, Concat, Resize
  - NV12 vs RGB
  - Model optimization levels
- Understand model input/output:
  - Input: `[1, 3, 640, 640]`
  - Output: `[1, 7, 8400]`
  - 8400 candidate predictions → confidence filter → NMS → final detections

## 2. Dataset / Test Image
- Reviewed two PPE datasets:
  - SFCHD
  - SH17
- Selected one real SFCHD image containing:
  - person
  - helmet
  - safety clothes

## 3. PyTorch Baseline
- Created separate `yolo_env`
- Installed Ultralytics
- Ran `best.pt` with `test.jpg`
- Forced inference input to `640x640`
- Result:

| Class | Confidence |
|---|---:|
| person | ~0.915 |
| helmet | ~0.916 |
| safety_clothes | ~0.889 |

- PyTorch baseline: **PASS**

## 4. RKNN Static Image Inference
- Copied `test.jpg` to Orange Pi 5
- Installed `opencv-python-headless`
- Created `infer_image_rknn.py`
- Implemented:
  - Letterbox 640x640
  - BGR → RGB
  - RKNN NPU inference
  - Parse `[1,7,8400]`
  - Confidence filtering
  - NMS
  - Bounding-box mapping
  - Save result image

RKNN result:

| Class | Confidence |
|---|---:|
| person | 0.9175 |
| helmet | 0.9155 |
| safety_clothes | 0.8921 |

- Final detections: `3`
- Output: `result_rknn.jpg`
- RKNN result is very close to PyTorch baseline.

## 5. Current Status

```text
best.pt
   ↓
best.onnx
   ↓
best_fp16.rknn
   ↓
RKNNLite2
   ↓
RK3588S NPU
   ↓
Real image inference
   ↓
person / helmet / safety_clothes