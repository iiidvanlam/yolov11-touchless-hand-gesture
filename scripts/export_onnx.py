"""
Script xuất mô hình YOLOv11-Pose (.pt) sang định dạng ONNX (.onnx)
để tăng tốc độ suy luận thời gian thực.
"""

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Xuất model YOLOv11-Pose sang ONNX")
    parser.add_argument(
        "--weights",
        type=str,
        default="models/yolo11n_hand_pose_best.pt",
        help="Đường dẫn file trọng số .pt",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước ảnh đầu vào")
    args = parser.parse_args()

    if not os.path.exists(args.weights):
        print(f"[LỖI] Không tìm thấy file trọng số: {args.weights}")
        return

    from ultralytics import YOLO

    model = YOLO(args.weights)
    export_path = model.export(format="onnx", imgsz=args.imgsz, dynamic=False, simplify=True)
    print(f"[THÀNH CÔNG] Đã xuất mô hình ONNX tại: {export_path}")


if __name__ == "__main__":
    main()

