"""
Script xuất mô hình YOLOv11-Pose (.pt) sang định dạng ONNX (.onnx)
để tăng tốc độ suy luận thời gian thực.
"""

import argparse
import importlib.util
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _resolve_path(path: str) -> str:
    if os.path.isabs(path) or os.path.exists(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Xuất model YOLOv11-Pose sang ONNX")
    parser.add_argument(
        "--weights",
        type=str,
        default=os.path.join(PROJECT_ROOT, "models", "yolo11n_hand_pose_best.pt"),
        help="Đường dẫn file trọng số .pt",
    )
    parser.add_argument("--imgsz", type=int, default=384, help="Kích thước ảnh đầu vào (mặc định: 384)")
    args = parser.parse_args()

    weights_path = _resolve_path(args.weights)
    if not os.path.exists(weights_path):
        print(f"[LỖI] Không tìm thấy file trọng số: {weights_path}")
        sys.exit(1)

    missing = [pkg for pkg in ("onnx", "onnxruntime", "onnxslim") if importlib.util.find_spec(pkg) is None]
    if missing:
        print(
            f"[LỖI] Thiếu thư viện ONNX cần thiết để xuất mô hình: {', '.join(missing)}.\n"
            "Vui lòng cài đặt: uv pip install onnx onnxruntime onnxslim"
        )
        sys.exit(1)

    from ultralytics import YOLO

    model = YOLO(weights_path)
    export_path = model.export(format="onnx", imgsz=args.imgsz, dynamic=False, simplify=True)
    print(f"[THÀNH CÔNG] Đã xuất mô hình ONNX tại: {export_path}")


if __name__ == "__main__":
    main()

