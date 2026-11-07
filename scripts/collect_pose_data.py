"""
Công cụ thu thập mẫu 21 điểm khớp xương bàn tay (21 Keypoints) trực tiếp từ Webcam
bằng mô hình YOLOv11-Pose để dạy thêm/cá nhân hóa bảng chữ cái ASL (A-Z) trong vài giây.

Cách sử dụng:
  python scripts/collect_pose_data.py
  - Nhấn phím chữ cái (A - Z) trên bàn phím để lưu mẫu 21-keypoints hiện tại cho chữ cái đó.
  - Nhấn phím SPACE để lưu mẫu cho cử chỉ cách từ (SPACE).
  - Nhấn phím ESC để lưu toàn bộ vào `models/asl_keypoints_db.npz` và thoát.
"""

import os
import sys
from typing import List
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.detector import YoloPoseHandDetector
from src.core.pose_analyzer import HandPoseAnalyzer


def main() -> None:
    os.makedirs("models", exist_ok=True)
    db_path = os.path.join("models", "asl_keypoints_db.npz")

    detector = YoloPoseHandDetector()
    analyzer = HandPoseAnalyzer(custom_keypoints_db_path=db_path)

    features_list: List[np.ndarray] = []
    labels_list: List[str] = []

    if analyzer.sample_features is not None and analyzer.sample_labels is not None:
        features_list = list(analyzer.sample_features)
        labels_list = [str(x) for x in analyzer.sample_labels]
        print(f"[INFO] Đã nạp {len(labels_list)} mẫu keypoints có sẵn từ {db_path}")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)

    print("=" * 65)
    print(" THU THẬP MẪU 21-KEYPOINTS CHO BẢNG CHỮ CÁI ASL (A-Z)")
    print(" - Đưa tay vào khung hình, bấm phím A..Z để ghi mẫu cho chữ đó.")
    print(" - Bấm ESC để lưu vào models/asl_keypoints_db.npz và thoát.")
    print("=" * 65)

    last_saved_msg = "Bấm phím chữ cái (A-Z) để lưu mẫu 21-keypoints"

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        frame = cv2.flip(frame, 1)
        annotated, analyses = detector.detect(frame)

        cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 75), (20, 25, 35), -1)
        cv2.putText(
            annotated,
            f"Tong so mau da luu: {len(labels_list)} | Nhan [A-Z] de luu, [ESC] de thoat",
            (15, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (0, 255, 200),
            2,
        )
        cv2.putText(
            annotated,
            last_saved_msg,
            (15, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 220, 100),
            1,
        )

        cv2.imshow("Thu thap 21-Keypoints YOLOv11-Pose (ASL A-Z)", annotated)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            break

        if analyses and (65 <= key <= 90 or 97 <= key <= 122 or key == 32):
            kpts = analyses[0].keypoints
            norm_feat = HandPoseAnalyzer.extract_normalized_features(kpts)
            label = "SPACE" if key == 32 else chr(key).upper()
            features_list.append(norm_feat)
            labels_list.append(label)
            count_for_label = sum(1 for x in labels_list if x == label)
            last_saved_msg = f"Da luu mau cho '{label}' (Tong '{label}': {count_for_label} mau)"

    cap.release()
    cv2.destroyAllWindows()

    if features_list:
        np.savez_compressed(
            db_path,
            features=np.array(features_list, dtype=np.float32),
            labels=np.array(labels_list),
        )
        print(f"[HOÀN TẤT] Đã lưu {len(labels_list)} mẫu vào {db_path}")


if __name__ == "__main__":
    main()

