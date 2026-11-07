# Nhận diện Ngôn ngữ Ký hiệu (ASL A-Z) & Điều khiển Thiết bị Không chạm với YOLOv11-Pose

Ứng dụng Desktop Python thời gian thực sử dụng **YOLOv11-Pose (21 điểm khớp xương bàn tay)** chạy trực tiếp trên **GPU NVIDIA GeForce RTX 4050 (CUDA)** với 2 chế độ:
1. **Ngôn ngữ Ký hiệu (ASL A-Z):** Nhận diện chữ cái từ 21 điểm khớp xương bàn tay, chống nhảy chữ bằng `VotingBuffer`, gợi ý từ thông minh (Autocomplete) và đọc to câu bằng giọng nói (`Text-to-Speech`).
2. **Điều khiển Thiết bị Không chạm (Touchless Control):** Điều khiển hệ thống Windows không cần chạm tay (Tăng/giảm âm lượng mượt từ 0-100% bằng khoảng cách chụm ngón cái - ngón trỏ **Pinch Volume**, Tạm dừng/Phát tiếp video YouTube/Spotify, Bật/Tắt tiếng, Chuyển bài, Chụp màn hình).

---

## 1. Cài đặt Môi trường (Tối ưu cho GPU RTX 4050)

> **Lưu ý về phiên bản Python cho GPU CUDA:**
> Để PyTorch nhận diện đầy đủ nhân CUDA của card rời **RTX 4050**, bạn nên tạo môi trường ảo với **Python 3.11 hoặc 3.12**:

```powershell
# 1. Cài đặt PyTorch hỗ trợ GPU NVIDIA CUDA 12.6
pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu126

# 2. Cài đặt Ultralytics YOLOv11 và các thư viện điều khiển hệ thống
pip install -r requirements.txt
```

---

## 2. Huấn luyện YOLOv11-Pose trực tiếp trên GPU của máy

Dự án đã tích hợp sẵn script [scripts/train_yolov11_pose_gpu.py](file:///d:/NhanDienCuChiTay/scripts/train_yolov11_pose_gpu.py) tối ưu riêng cho **6GB VRAM của RTX 4050** (bật Mixed Precision FP16 `amp=True`, `batch=16`, `imgsz=640`).

### Cách 1: Huấn luyện tự động với bộ dữ liệu chuẩn `hand-keypoints.yaml` (Khuyên dùng)
Ultralytics hỗ trợ tự động tải bộ dữ liệu **26,000+ ảnh bàn tay chuẩn 21 điểm khớp xương (`kpt_shape: [21, 3]`)** và huấn luyện ngay bằng 1 lệnh:

```powershell
python scripts/train_yolov11_pose_gpu.py --model yolo11n-pose.pt --dataset hand-keypoints.yaml --epochs 50 --batch 16
```
Sau khi huấn luyện xong, trọng số tốt nhất sẽ tự động được chép vào `models/yolo11n_hand_pose_best.pt`.

### Cách 2: Cá nhân hóa nhanh 21-Keypoints cho bảng chữ cái ASL (A-Z) bằng Webcam
Bạn có thể dạy thêm hoặc tinh chỉnh bất kỳ chữ cái nào theo đúng góc tay của bạn chỉ trong vài giây bằng:
```powershell
python scripts/collect_pose_data.py
```
Hoặc dùng ngay khung **"Cá nhân hóa nhanh 21-Keypoints"** tích hợp sẵn ở góc dưới bên phải giao diện ứng dụng chính.

---

## 3. Khởi chạy Ứng dụng Desktop

```powershell
python main.py
```

