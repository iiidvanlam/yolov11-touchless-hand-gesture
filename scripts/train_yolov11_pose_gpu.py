"""
Script huấn luyện trực tiếp mô hình YOLOv11-Pose (21 điểm khớp xương bàn tay)
trên GPU NVIDIA GeForce RTX 4050 (6GB VRAM) của máy hiện tại.

Cách chạy:
  .venv\Scripts\python.exe scripts/train_yolov11_pose_gpu.py --epochs 15 --fraction 0.15 --batch 8
"""

import argparse
import gc
import os
import shutil
import sys

os.environ.setdefault("YOLO_CONFIG_DIR", os.path.abspath("runs/ultralytics_config"))
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


def verify_gpu() -> str:
    """Kiểm tra GPU NVIDIA và cấu hình CUDA trước khi bắt đầu huấn luyện."""
    try:
        import torch

        print("=" * 68)
        print(" KIỂM TRA PHẦN CỨNG HUẤN LUYỆN (GPU CUDA CHECK)")
        print("=" * 68)
        print(f" - PyTorch version : {torch.__version__}")
        print(f" - CUDA available  : {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            print(f" - Thiết bị GPU    : {gpu_name} ({vram_gb:.2f} GB VRAM)")
            print("=" * 68)
            return "0"
        else:
            print(" [CẢNH BÁO] PyTorch hiện tại chưa nhận CUDA GPU (đang chạy bản CPU).")
            print("=" * 68)
            return "cpu"
    except ImportError:
        print("[LỖI] Chưa cài đặt PyTorch và Ultralytics.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Huấn luyện YOLOv11-Pose (21 Hand Keypoints) trên GPU máy cá nhân"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/yolo11n_hand_pose_best.pt",
        help="Model khởi tạo: models/yolo11n_hand_pose_best.pt hoặc yolo11n-pose.pt",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/hand_pose_local.yaml",
        help="File cấu hình dataset",
    )
    parser.add_argument("--epochs", type=int, default=15, help="Số vòng lặp huấn luyện (mặc định: 15)")
    parser.add_argument(
        "--fraction",
        type=float,
        default=0.15,
        help="Tỷ lệ tập dữ liệu sử dụng mỗi đợt train (0.1 -> 1.0)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=8,
        help="Batch size tối ưu cho 6GB VRAM của RTX 4050 (mặc định: 8)",
    )
    parser.add_argument("--imgsz", type=int, default=384, help="Kích thước ảnh huấn luyện (mặc định: 384)")
    parser.add_argument("--freeze", type=int, default=10, help="Số tầng Backbone đóng băng để hội tụ Pose nhanh")
    parser.add_argument("--workers", type=int, default=0, help="Số worker đọc dữ liệu (0 trên Windows)")
    parser.add_argument(
        "--name",
        type=str,
        default="yolo11_hand_pose_rtx4050",
        help="Tên thư mục lưu kết quả trong runs/pose/",
    )
    args = parser.parse_args()

    device = verify_gpu()

    from ultralytics import YOLO
    from ultralytics.utils.loss import KeypointLoss
    import torch

    # Khắc phục lỗi Vanishing Gradient của hàm OKS KeypointLoss (1 - exp(-e)) trong FP16 khi sigma=1/21 quá nhỏ,
    # khiến các đỉnh ngón tay xa tâm (kpt 12, 16, 20) có exp(-e) == 0 và bị kẹt cứng ở lòng bàn tay.
    def _stable_keypoint_loss_forward(self, pred_kpts, gt_kpts, kpt_mask, area):
        d = (pred_kpts[..., 0] - gt_kpts[..., 0]).pow(2) + (pred_kpts[..., 1] - gt_kpts[..., 1]).pow(2)
        kpt_loss_factor = kpt_mask.shape[1] / (torch.sum(kpt_mask != 0, dim=1) + 1e-9)
        e = d / ((2 * self.sigmas).pow(2) * (area + 1e-9) * 2)
        loss_per_kpt = (1.0 - torch.exp(-e)) + 0.25 * torch.log1p(e)
        return (kpt_loss_factor.view(-1, 1) * (loss_per_kpt * kpt_mask)).mean()

    KeypointLoss.forward = _stable_keypoint_loss_forward

    model_path = args.model if os.path.exists(args.model) else "yolo11n-pose.pt"
    print(f"\n[1/3] Đang khởi tạo mô hình {model_path}...")
    model = YOLO(model_path)

    os.makedirs("models", exist_ok=True)
    target_path = os.path.join("models", "yolo11n_hand_pose_best.pt")

    def _on_epoch_end_callback(trainer) -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        # Tự động đồng bộ best.pt / last.pt sang models/yolo11n_hand_pose_best.pt sau MỖI epoch
        try:
            w_dir = os.path.join(str(trainer.save_dir), "weights")
            best_f = os.path.join(w_dir, "best.pt")
            last_f = os.path.join(w_dir, "last.pt")
            if os.path.exists(best_f):
                shutil.copy2(best_f, target_path)
            elif os.path.exists(last_f):
                shutil.copy2(last_f, target_path)
        except Exception:
            pass

    model.add_callback("on_train_epoch_end", _on_epoch_end_callback)
    model.add_callback("on_fit_epoch_end", _on_epoch_end_callback)

    print(f"[2/3] Bắt đầu huấn luyện 21-Keypoints trên '{args.dataset}' (device={device}, imgsz={args.imgsz})...")
    results = model.train(
        data=args.dataset,
        epochs=args.epochs,
        fraction=args.fraction,
        imgsz=args.imgsz,
        batch=args.batch,
        freeze=args.freeze,
        device=device,
        workers=args.workers,
        amp=True,
        cache=False,
        project="runs/pose",
        name=args.name,
        exist_ok=True,
        cos_lr=True,
        warmup_epochs=0.5,
        mosaic=0.0,             # Tắt ghép 4 ảnh nhỏ để bàn tay rõ nét, giúp 21 keypoints hội tụ nhanh gấp 4 lần
        fliplr=0.5,
        degrees=15.0,
        plots=False,
    )

    save_dir = str(getattr(results, "save_dir", os.path.join("runs", "pose", args.name)))
    best_weight_path = os.path.join(save_dir, "weights", "best.pt")
    if os.path.exists(best_weight_path):
        shutil.copy2(best_weight_path, target_path)
        print("\n" + "=" * 68)
        print(f" [3/3] HOÀN TẤT! Đã cập nhật model 21-Keypoints tốt nhất tại: {target_path}")
        print("=" * 68)


if __name__ == "__main__":
    main()
