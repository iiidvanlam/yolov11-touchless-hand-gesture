from concurrent.futures import ThreadPoolExecutor
import importlib.util
import math
import os
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

from src.core.paths import (
    DEFAULT_GESTURE_TASK_PATH,
    DEFAULT_YOLO_MODEL_PATH,
    PROJECT_ROOT,
    resolve_project_path,
)
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
        model_path: str = DEFAULT_YOLO_MODEL_PATH,
        conf_threshold: float = 0.55,
        iou_threshold: float = 0.45,
        use_gpu: bool = True,
        gesture_task_path: str = DEFAULT_GESTURE_TASK_PATH,
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
        self.last_raw_kpts: Optional[np.ndarray] = None
        self._prev_bbox: Optional[Tuple[int, int, int, int]] = None
        self._pool = ThreadPoolExecutor(max_workers=2)
        self._last_yolo_warn_t: float = 0.0
        self._last_mp_warn_t: float = 0.0

        self._init_mediapipe_refiner()
        self.load_model(model_path)

    def close(self) -> None:
        self._pool.shutdown(wait=False)

    def _init_mediapipe_refiner(self) -> None:
        """Khởi tạo bộ tinh chỉnh 21 khớp 3D & GestureRecognizer sub-pixel."""
        task_path = self.gesture_task_path
        if not os.path.exists(task_path) and task_path and not os.path.isabs(task_path):
            candidate = resolve_project_path(task_path)
            if os.path.exists(candidate):
                task_path = candidate
        if not task_path or not os.path.exists(task_path):
            return
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            base_opts = mp_python.BaseOptions(model_asset_path=task_path)
            opts = mp_vision.GestureRecognizerOptions(
                base_options=base_opts,
                num_hands=1,
                min_hand_detection_confidence=0.62,
                min_hand_presence_confidence=0.62,
                min_tracking_confidence=0.58,
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

        resolved_requested = self.model_path
        if resolved_requested and not os.path.exists(resolved_requested) and not os.path.isabs(resolved_requested):
            candidate_rel = resolve_project_path(resolved_requested)
            if os.path.exists(candidate_rel):
                resolved_requested = candidate_rel

        if resolved_requested and resolved_requested.lower().endswith(".onnx"):
            if importlib.util.find_spec("onnxruntime") is None:
                print(
                    f"[Cảnh báo] Thiếu thư viện 'onnxruntime' để nạp model ONNX ({resolved_requested}). "
                    "Vui lòng cài đặt 'onnxruntime' hoặc chọn file trọng số '.pt'."
                )
                self.model = None
                self.model_loaded_name = "Thiếu onnxruntime (.onnx)"
                return False

        try:
            from ultralytics import YOLO

            candidates = [
                resolved_requested,
                DEFAULT_YOLO_MODEL_PATH,
                os.path.join(PROJECT_ROOT, "runs", "pose", "runs", "pose", "yolo11_hand_pose_rtx4050", "weights", "best.pt"),
                os.path.join(PROJECT_ROOT, "runs", "pose", "yolo11n_hand_pose_refine", "weights", "best.pt"),
                os.path.join(PROJECT_ROOT, "yolo11n-pose.pt"),
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
            kpt_shape = getattr(getattr(self.model, "model", None), "kpt_shape", None)
            if kpt_shape is not None and len(kpt_shape) >= 1 and int(kpt_shape[0]) < 21:
                print(
                    f"[Cảnh báo] Model '{os.path.basename(selected)}' chỉ có {int(kpt_shape[0])} keypoints "
                    "(COCO person), không đủ 21 keypoints bàn tay! Vui lòng dùng 'models/yolo11n_hand_pose_best.pt'."
                )
                self.model_loaded_name = (
                    f"{os.path.basename(selected)} [CẢNH BÁO {int(kpt_shape[0])}-kpt!] ({self.device.upper()}{tag_mp})"
                )
            else:
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

    def _mp_recognize_roi(
        self, rgb_full: np.ndarray, bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]], Optional[str], float]:
        """Chạy MediaPipe 3D trên vùng ROI (hoặc toàn ảnh RGB) đã chuyển đổi sẵn."""
        if self.mp_recognizer is None:
            return None, None, None, 0.0

        try:
            import mediapipe as mp

            h_full, w_full = rgb_full.shape[:2]
            if bbox is not None:
                x1, y1, x2, y2 = bbox
                bw, bh = x2 - x1, y2 - y1
                pad = int(max(bw, bh) * 0.50)
                cx1 = max(0, x1 - pad)
                cy1 = max(0, y1 - pad)
                cx2 = min(w_full, x2 + pad)
                cy2 = min(h_full, y2 + pad)
                if (cx2 - cx1) >= 64 and (cy2 - cy1) >= 64:
                    roi_rgb = np.ascontiguousarray(rgb_full[cy1:cy2, cx1:cx2])
                    res = self.mp_recognizer.recognize(mp.Image(image_format=mp.ImageFormat.SRGB, data=roi_rgb))
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
                return None, None, None, 0.0

            res_full = self.mp_recognizer.recognize(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_full))
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
        except Exception as exc:
            now = time.monotonic()
            if now - self._last_mp_warn_t >= 5.0:
                self._last_mp_warn_t = now
                print(f"[Cảnh báo] Lỗi MediaPipe 3D Refiner: {exc}")
        return None, None, None, 0.0

    def _run_yolo(
        self, frame: np.ndarray
    ) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[np.ndarray], float]:
        if self.model is None:
            return None, None, 0.0
        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
                imgsz=384,
            )
            if results and results[0].boxes is not None and len(results[0].boxes) > 0:
                res = results[0]
                boxes_xyxy = res.boxes.xyxy.cpu().numpy()
                boxes_conf = res.boxes.conf.cpu().numpy()
                best_idx = int(np.argmax(boxes_conf))
                x1, y1, x2, y2 = [int(v) for v in boxes_xyxy[best_idx]]
                yolo_bbox = (x1, y1, x2, y2)
                yolo_conf = float(boxes_conf[best_idx])
                yolo_kpts = None
                if res.keypoints is not None and res.keypoints.data is not None:
                    kpts_all = res.keypoints.data.cpu().numpy()
                    if best_idx < len(kpts_all) and kpts_all[best_idx].shape[0] >= 21:
                        yolo_kpts = self._anatomical_correct_keypoints(kpts_all[best_idx][:21])
                return yolo_bbox, yolo_kpts, yolo_conf
        except Exception as exc:
            now = time.monotonic()
            if now - self._last_yolo_warn_t >= 5.0:
                self._last_yolo_warn_t = now
                print(f"[Cảnh báo] Lỗi suy luận YOLO: {exc}")
        return None, None, 0.0

    def detect(
        self, frame: np.ndarray, pinch_mode_enabled: bool = False
    ) -> Tuple[np.ndarray, List[HandPoseAnalysis]]:
        """Chạy song song Hybrid YOLOv11-Pose (GPU) + MediaPipe 3D (CPU) + 1€ Filter để đạt FPS tối đa."""
        annotated = frame.copy()
        analyses: List[HandPoseAnalysis] = []

        rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        prev_box = self._prev_bbox

        # Chạy song song Stage 1 (YOLO trên GPU) và Stage 2 (MediaPipe trên CPU) cùng lúc (~10ms tổng)
        f_yolo = self._pool.submit(self._run_yolo, frame)
        f_mp = self._pool.submit(self._mp_recognize_roi, rgb_full, prev_box)

        yolo_bbox, yolo_kpts, yolo_conf = f_yolo.result()
        mp_kpts, mp_bbox, neural_gesture, neural_score = f_mp.result()

        # Nếu prev_box bị trượt (tay mới vào hoặc di chuyển nhanh) thì thử lại đúng vùng YOLO/toàn ảnh
        if mp_kpts is None and self.mp_recognizer is not None:
            if yolo_bbox is not None:
                mp_kpts, mp_bbox, neural_gesture, neural_score = self._mp_recognize_roi(rgb_full, yolo_bbox)
            elif prev_box is not None:
                mp_kpts, mp_bbox, neural_gesture, neural_score = self._mp_recognize_roi(rgb_full, None)

        final_kpts: Optional[np.ndarray] = None
        final_bbox: Optional[Tuple[int, int, int, int]] = None
        final_conf: float = yolo_conf

        if self.mp_recognizer is not None:
            # Khi có MediaPipe 3D Refiner, BẮT BUỘC phải được MediaPipe xác nhận là bàn tay thật
            # để loại bỏ 100% hiện tượng YOLO nhận nhầm khuôn mặt / quần áo / phông nền làm bàn tay.
            if mp_kpts is not None and mp_bbox is not None:
                final_kpts = mp_kpts
                final_bbox = mp_bbox
                final_conf = max(yolo_conf, 0.92)
        elif yolo_kpts is not None and yolo_bbox is not None and yolo_conf >= 0.65:
            final_kpts = yolo_kpts
            final_bbox = yolo_bbox

        if final_kpts is None or final_bbox is None:
            self._prev_bbox = None
            self.kpt_smoother.reset()
            self.last_raw_kpts = None
            return annotated, analyses

        # Kiểm tra giải phẫu bàn tay chặt chẽ trước khi lọc & phân tích
        if not self.analyzer.is_valid_hand_skeleton(final_bbox, final_kpts):
            self._prev_bbox = None
            self.kpt_smoother.reset()
            self.last_raw_kpts = None
            return annotated, analyses

        self._prev_bbox = final_bbox

        # Lưu tọa độ thô (trước lọc) để vẽ biểu đồ Telemetry so sánh Raw vs 1€
        self.last_raw_kpts = final_kpts.copy()

        # Stage 3: Bộ lọc thích ứng One-Euro Filter (1€ Filter) chống rung tuyệt đối
        smoothed_kpts = self.kpt_smoother.update(final_kpts)

        # Kiểm tra lại khung xương sau làm mượt (tránh trường hợp trộn tọa độ tạo ra khung xương lỗi)
        if not self.analyzer.is_valid_hand_skeleton(final_bbox, smoothed_kpts):
            self._prev_bbox = None
            self.kpt_smoother.reset()
            self.last_raw_kpts = None
            return annotated, analyses

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
