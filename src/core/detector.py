import math
import os
from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.core.pose_analyzer import (
    HAND_SKELETON_CONNECTIONS,
    HandPoseAnalysis,
    HandPoseAnalyzer,
)
from src.core.smoother import OneEuroKeypointSmoother


class YoloPoseHandDetector:
    """
    Bộ nhận diện & ước lượng 21 điểm khớp xương bàn tay Hybrid thế hệ mới:
      - Stage 1: YOLOv11-Pose chạy trên GPU NVIDIA (CUDA:0) phát hiện nhanh vùng bàn tay (ROI) & khung xương sơ bộ.
      - Stage 2: Google MediaPipe 3D HandLandmarker & GestureRecognizer tinh chỉnh sub-pixel 21 khớp 3D + phân loại cử chỉ sâu.
      - Stage 3: Bộ lọc thích ứng One-Euro Filter (1€ Filter) triệt tiêu rung nhiễu (jitter) với độ trễ bằng 0.
    """

    FINGER_COLORS = [
        (0, 180, 255),    # Ngón cái (Vàng cam)
        (0, 255, 120),    # Ngón trỏ (Xanh lá)
        (255, 200, 0),    # Ngón giữa (Xanh dương sáng)
        (255, 0, 180),    # Ngón áp út (Tím)
        (80, 80, 255),    # Ngón út (Đỏ hồng)
    ]

    def __init__(
        self,
        model_path: str = "models/yolo11n_hand_pose_best.pt",
        conf_threshold: float = 0.32,
        iou_threshold: float = 0.45,
        use_gpu: bool = True,
        gesture_task_path: str = "models/gesture_recognizer.task",
    ):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.use_gpu = use_gpu
        self.gesture_task_path = gesture_task_path

        self.model = None
        self.mp_recognizer = None
        self.device = "cpu"
        self.model_loaded_name = "Chưa nạp model"
        self.analyzer = HandPoseAnalyzer()
        self.kpt_smoother = OneEuroKeypointSmoother(min_cutoff=1.4, beta=0.035)

        self._init_mediapipe_refiner()
        self.load_model(model_path)

    def _init_mediapipe_refiner(self) -> None:
        """Khởi tạo bộ tinh chỉnh 21 khớp 3D & GestureRecognizer sub-pixel."""
        if not os.path.exists(self.gesture_task_path):
            return
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            base_opts = mp_python.BaseOptions(model_asset_path=self.gesture_task_path)
            opts = mp_vision.GestureRecognizerOptions(
                base_options=base_opts,
                num_hands=1,
                min_hand_detection_confidence=0.25,
                min_hand_presence_confidence=0.25,
                min_tracking_confidence=0.25,
            )
            self.mp_recognizer = mp_vision.GestureRecognizer.create_from_options(opts)
        except Exception as exc:
            print(f"[Cảnh báo] Không thể khởi tạo MediaPipe 3D Refiner: {exc}")
            self.mp_recognizer = None

    def _resolve_device(self) -> str:
        """Kiểm tra GPU NVIDIA CUDA trên máy hiện tại."""
        if not self.use_gpu:
            return "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda:0"
        except Exception:
            pass
        return "cpu"

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """Tải mô hình YOLOv11-Pose lên GPU (hoặc CPU nếu chưa có CUDA)."""
        if model_path:
            self.model_path = model_path

        self.device = self._resolve_device()

        try:
            from ultralytics import YOLO

            candidates = [
                self.model_path,
                "models/yolo11n_hand_pose_best.pt",
                "runs/pose/runs/pose/yolo11_hand_pose_rtx4050/weights/best.pt",
                "runs/pose/yolo11n_hand_pose_gpu/weights/best.pt",
                "yolo11n-pose.pt",
            ]
            selected = None
            for path in candidates:
                if path and os.path.exists(path):
                    selected = path
                    break

            if selected is None:
                selected = "yolo11n-pose.pt"

            self.model = YOLO(selected)
            tag_mp = " + MP3D + 1€" if self.mp_recognizer is not None else ""
            self.model_loaded_name = f"{os.path.basename(selected)} ({self.device.upper()}{tag_mp})"
            return True
        except Exception as exc:
            print(f"[Cảnh báo] Không thể tải YOLOv11-Pose ({exc}).")
            self.model = None
            self.model_loaded_name = "Lỗi nạp model"
            return False

    @staticmethod
    def _anatomical_correct_keypoints(kpts: np.ndarray) -> np.ndarray:
        """
        Hiệu chỉnh hình học giải phẫu cho các điểm đầu ngón tay dự phòng từ YOLO thuần.
        """
        corrected = kpts.copy()
        finger_chains = [
            (5, 6, 7, 8, 0.82),
            (9, 10, 11, 12, 0.85),
            (13, 14, 15, 16, 0.82),
            (17, 18, 19, 20, 0.78),
        ]
        for mcp, pip, dip, tip, scale in finger_chains:
            p_mcp = corrected[mcp, :2]
            p_pip = corrected[pip, :2]
            p_dip = corrected[dip, :2]
            p_tip = corrected[tip, :2]

            v_pip_dip = p_dip - p_pip
            v_dip_tip = p_tip - p_dip
            len_pip_dip = float(np.linalg.norm(v_pip_dip))
            len_dip_tip = float(np.linalg.norm(v_dip_tip))

            if len_pip_dip < 2.0:
                continue

            cos_dir = float(np.dot(v_pip_dip, v_dip_tip) / (len_pip_dip * max(len_dip_tip, 1e-4)))
            dist_dip_mcp = float(np.linalg.norm(p_dip - p_mcp))
            dist_tip_mcp = float(np.linalg.norm(p_tip - p_mcp))

            if cos_dir < -0.20 and dist_tip_mcp < dist_dip_mcp:
                corrected[tip, :2] = p_dip + scale * v_pip_dip

        return corrected

    def _refine_with_mediapipe_3d(
        self, frame: np.ndarray, yolo_bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]], Optional[str], float]:
        """
        Sử dụng MediaPipe 3D HandLandmarker & GestureRecognizer trên ROI của YOLO (hoặc toàn khung hình)
        để trích xuất chính xác tuyệt đối 21 khớp xương bàn tay & phân loại cử chỉ sâu.
        """
        if self.mp_recognizer is None:
            return None, None, None, 0.0

        import mediapipe as mp

        h_full, w_full = frame.shape[:2]

        # 1. Nếu YOLO đã phát hiện vùng bàn tay, thử chạy trên vùng ROI mở rộng trước để tăng tốc & độ chính xác
        if yolo_bbox is not None:
            x1, y1, x2, y2 = yolo_bbox
            bw, bh = x2 - x1, y2 - y1
            pad_x = int(max(bw, bh) * 0.45)
            pad_y = int(max(bw, bh) * 0.45)
            cx1 = max(0, x1 - pad_x)
            cy1 = max(0, y1 - pad_y)
            cx2 = min(w_full, x2 + pad_x)
            cy2 = min(h_full, y2 + pad_y)

            if (cx2 - cx1) >= 64 and (cy2 - cy1) >= 64:
                roi_rgb = cv2.cvtColor(frame[cy1:cy2, cx1:cx2], cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=roi_rgb)
                res = self.mp_recognizer.recognize(mp_img)
                if res.hand_landmarks and len(res.hand_landmarks) > 0:
                    lms = res.hand_landmarks[0]
                    rw, rh = cx2 - cx1, cy2 - cy1
                    kpts = np.array(
                        [[cx1 + lm.x * rw, cy1 + lm.y * rh, 0.98] for lm in lms],
                        dtype=np.float32,
                    )
                    neural_name = None
                    neural_score = 0.0
                    if res.gestures and len(res.gestures) > 0 and len(res.gestures[0]) > 0:
                        neural_name = res.gestures[0][0].category_name
                        neural_score = float(res.gestures[0][0].score)
                    tight_box = (
                        max(0, int(np.min(kpts[:, 0]) - 18)),
                        max(0, int(np.min(kpts[:, 1]) - 18)),
                        min(w_full, int(np.max(kpts[:, 0]) + 18)),
                        min(h_full, int(np.max(kpts[:, 1]) + 18)),
                    )
                    return kpts, tight_box, neural_name, neural_score

        # 2. Chạy trên toàn khung hình
        rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img_full = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_full)
        res_full = self.mp_recognizer.recognize(mp_img_full)
        if res_full.hand_landmarks and len(res_full.hand_landmarks) > 0:
            lms = res_full.hand_landmarks[0]
            kpts = np.array(
                [[lm.x * w_full, lm.y * h_full, 0.98] for lm in lms],
                dtype=np.float32,
            )
            neural_name = None
            neural_score = 0.0
            if res_full.gestures and len(res_full.gestures) > 0 and len(res_full.gestures[0]) > 0:
                neural_name = res_full.gestures[0][0].category_name
                neural_score = float(res_full.gestures[0][0].score)
            tight_box = (
                max(0, int(np.min(kpts[:, 0]) - 18)),
                max(0, int(np.min(kpts[:, 1]) - 18)),
                min(w_full, int(np.max(kpts[:, 0]) + 18)),
                min(h_full, int(np.max(kpts[:, 1]) + 18)),
            )
            return kpts, tight_box, neural_name, neural_score

        return None, None, None, 0.0

    def detect(
        self, frame: np.ndarray, pinch_mode_enabled: bool = False
    ) -> Tuple[np.ndarray, List[HandPoseAnalysis]]:
        """Chạy suy luận Hybrid YOLOv11-Pose (GPU) + MediaPipe 3D + 1€ Filter và vẽ 21 khớp xương."""
        annotated = frame.copy()
        analyses: List[HandPoseAnalysis] = []

        yolo_bbox: Optional[Tuple[int, int, int, int]] = None
        yolo_kpts: Optional[np.ndarray] = None
        yolo_conf: float = 0.0

        # Stage 1: YOLOv11-Pose trên GPU (CUDA:0)
        if self.model is not None:
            try:
                results = self.model.predict(
                    source=frame,
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    device=self.device,
                    verbose=False,
                    imgsz=512,
                )
                if results and results[0].boxes is not None and len(results[0].boxes) > 0:
                    res = results[0]
                    boxes_xyxy = res.boxes.xyxy.cpu().numpy()
                    boxes_conf = res.boxes.conf.cpu().numpy()
                    best_idx = int(np.argmax(boxes_conf))
                    x1, y1, x2, y2 = [int(v) for v in boxes_xyxy[best_idx]]
                    yolo_bbox = (x1, y1, x2, y2)
                    yolo_conf = float(boxes_conf[best_idx])
                    if res.keypoints is not None and res.keypoints.data is not None:
                        kpts_all = res.keypoints.data.cpu().numpy()
                        if best_idx < len(kpts_all) and kpts_all[best_idx].shape[0] >= 21:
                            yolo_kpts = self._anatomical_correct_keypoints(kpts_all[best_idx][:21])
            except Exception:
                pass

        # Stage 2: Tinh chỉnh 21 khớp 3D sub-pixel & nhận diện cử chỉ sâu
        mp_kpts, mp_bbox, neural_gesture, neural_score = self._refine_with_mediapipe_3d(
            frame, yolo_bbox=yolo_bbox
        )

        final_kpts: Optional[np.ndarray] = None
        final_bbox: Optional[Tuple[int, int, int, int]] = None
        final_conf: float = yolo_conf

        if mp_kpts is not None and mp_bbox is not None:
            final_kpts = mp_kpts
            final_bbox = yolo_bbox if yolo_bbox is not None else mp_bbox
            final_conf = max(yolo_conf, 0.92)
        elif yolo_kpts is not None and yolo_bbox is not None:
            final_kpts = yolo_kpts
            final_bbox = yolo_bbox

        if final_kpts is None or final_bbox is None:
            self.kpt_smoother.reset()
            return annotated, analyses

        # Stage 3: Bộ lọc thích ứng One-Euro Filter (1€ Filter) chống rung tuyệt đối
        smoothed_kpts = self.kpt_smoother.update(final_kpts)

        analysis = self.analyzer.analyze(
            bbox=final_bbox,
            keypoints=smoothed_kpts,
            det_conf=final_conf,
            pinch_mode_enabled=pinch_mode_enabled,
            neural_gesture=neural_gesture,
            neural_score=neural_score,
        )
        analyses.append(analysis)
        self._draw_hand_skeleton_and_hud(annotated, analysis)

        return annotated, analyses

    def _draw_hand_skeleton_and_hud(self, canvas: np.ndarray, analysis: HandPoseAnalysis) -> None:
        """Vẽ Bounding Box, 21 điểm khớp xương và các thanh nối giải phẫu bàn tay lên frame."""
        x1, y1, x2, y2 = analysis.bbox
        kpts = analysis.keypoints

        # 1. Vẽ Bounding Box bàn tay
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (80, 220, 100), 2)

        # 2. Vẽ các đoạn xương nối (Skeleton Bones) theo màu từng ngón
        for idx, (u, v) in enumerate(HAND_SKELETON_CONNECTIONS):
            pt1 = (int(kpts[u][0]), int(kpts[u][1]))
            pt2 = (int(kpts[v][0]), int(kpts[v][1]))
            conf_u = kpts[u][2] if kpts.shape[1] > 2 else 1.0
            conf_v = kpts[v][2] if kpts.shape[1] > 2 else 1.0
            if conf_u < 0.15 or conf_v < 0.15:
                continue

            if idx < 4:
                color = self.FINGER_COLORS[0]
            elif idx < 8:
                color = self.FINGER_COLORS[1]
            elif idx < 12:
                color = self.FINGER_COLORS[2]
            elif idx < 16:
                color = self.FINGER_COLORS[3]
            elif idx < 20:
                color = self.FINGER_COLORS[4]
            else:
                color = (200, 200, 200)

            cv2.line(canvas, pt1, pt2, color, 2, cv2.LINE_AA)

        # 3. Vẽ 21 nút khớp (Keypoint Joints)
        for i in range(21):
            px, py = int(kpts[i][0]), int(kpts[i][1])
            conf = kpts[i][2] if kpts.shape[1] > 2 else 1.0
            if conf < 0.15:
                continue
            radius = 6 if i in (0, 4, 8, 12, 16, 20) else 4
            fill_color = (0, 255, 255) if i in (0, 4, 8, 12, 16, 20) else (255, 255, 255)
            cv2.circle(canvas, (px, py), radius, fill_color, -1, cv2.LINE_AA)
            cv2.circle(canvas, (px, py), radius + 1, (20, 20, 20), 1, cv2.LINE_AA)

        # 4. Nếu đang ở chế độ Pinch Volume, vẽ thước đo khoảng cách giữa Ngón Cái (4) và Ngón Trỏ (8)
        if analysis.pinch_points is not None and analysis.pinch_ratio is not None:
            p_thumb, p_index = analysis.pinch_points
            mid_x = (p_thumb[0] + p_index[0]) // 2
            mid_y = (p_thumb[1] + p_index[1]) // 2
            pct = int(round(analysis.pinch_ratio * 100))
            cv2.line(canvas, p_thumb, p_index, (0, 255, 255), 3, cv2.LINE_AA)
            cv2.circle(canvas, (mid_x, mid_y), 8, (0, 140, 255), -1, cv2.LINE_AA)
            cv2.putText(
                canvas,
                f"Vol: {pct}%",
                (mid_x + 12, mid_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
