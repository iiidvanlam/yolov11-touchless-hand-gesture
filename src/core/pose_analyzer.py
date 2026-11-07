from dataclasses import dataclass
import math
import os
from typing import List, Optional, Tuple
import numpy as np


# Định nghĩa các cặp nối khớp xương bàn tay (21 Keypoints chuẩn)
HAND_SKELETON_CONNECTIONS: List[Tuple[int, int]] = [
    # Ngón cái (Thumb)
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Ngón trỏ (Index)
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Ngón giữa (Middle)
    (0, 9), (9, 10), (10, 11), (11, 12),
    # Ngón áp út (Ring)
    (0, 13), (13, 14), (14, 15), (15, 16),
    # Ngón út (Pinky)
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Lòng bàn tay (Palm)
    (5, 9), (9, 13), (13, 17),
]


@dataclass
class HandPoseAnalysis:
    """Kết quả phân tích từ 21 điểm khớp xương bàn tay (Hybrid YOLOv11-Pose + MediaPipe 3D)."""
    bbox: Tuple[int, int, int, int]          # (x1, y1, x2, y2)
    keypoints: np.ndarray                    # Shape (21, 3): x, y, conf
    det_confidence: float                    # Độ tự tin phát hiện bàn tay
    fingers_up: List[int]                    # [Thumb, Index, Middle, Ring, Pinky] (1: mở, 0: gập)
    asl_label: str                           # Nhãn chữ cái A-Z / SPACE / DEL
    asl_confidence: float                    # Độ tự tin nhận diện ASL
    control_gesture: str                     # Nhãn điều khiển (OPEN_PALM, FIST, THUMBS_UP, PINCH_VOLUME...)
    pinch_ratio: Optional[float]             # Giá trị 0.0 -> 1.0 khi đang dùng chế độ Pinch kéo âm lượng
    pinch_points: Optional[Tuple[Tuple[int, int], Tuple[int, int]]]  # Tọa độ (ngón cái, ngón trỏ)


class HandPoseAnalyzer:
    """
    Bộ phân tích 21 điểm khớp xương bàn tay kết hợp:
      1. Vector hình học bất biến tỷ lệ & góc khớp 3D/2D (21 Keypoints).
      2. Neural Gesture Classifier (Open_Palm, Closed_Fist, Victory, Thumb_Up, Thumb_Down, Pointing_Up, ILoveYou).
      3. Cơ sở dữ liệu mẫu cá nhân hóa k-NN Cosine Similarity (`models/asl_keypoints_db.npz`).
    """

    def __init__(self, custom_keypoints_db_path: str = "models/asl_keypoints_db.npz"):
        self.custom_keypoints_db_path = custom_keypoints_db_path
        self.sample_features: Optional[np.ndarray] = None
        self.sample_labels: Optional[np.ndarray] = None
        self.reload_custom_samples()

    def reload_custom_samples(self) -> None:
        """Tải tập mẫu 21-keypoints cá nhân hóa nếu người dùng đã lưu."""
        if os.path.exists(self.custom_keypoints_db_path):
            try:
                data = np.load(self.custom_keypoints_db_path, allow_pickle=True)
                self.sample_features = data["features"]
                self.sample_labels = data["labels"]
            except Exception:
                self.sample_features = None
                self.sample_labels = None

    @staticmethod
    def _dist(p1: np.ndarray, p2: np.ndarray) -> float:
        return float(math.hypot(float(p1[0] - p2[0]), float(p1[1] - p2[1])))

    @staticmethod
    def _angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        """Tính góc (độ) tại đỉnh b tạo bởi tia ba và bc."""
        ba = a[:2] - b[:2]
        bc = c[:2] - b[:2]
        norm_ba = float(np.linalg.norm(ba))
        norm_bc = float(np.linalg.norm(bc))
        if norm_ba < 1e-5 or norm_bc < 1e-5:
            return 180.0
        cos_angle = float(np.dot(ba, bc) / (norm_ba * norm_bc))
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return math.degrees(math.acos(cos_angle))

    @staticmethod
    def extract_normalized_features(kpts: np.ndarray) -> np.ndarray:
        """
        Chuẩn hóa 21 điểm khớp xương về hệ quy chiếu gốc cổ tay (kpt 0),
        bất biến với vị trí và kích thước bàn tay xa/gần camera.
        Trả về vector đặc trưng 42 chiều (21 x 2).
        """
        coords = kpts[:, :2].astype(np.float32)
        wrist = coords[0].copy()
        rel = coords - wrist
        max_val = float(np.max(np.linalg.norm(rel, axis=1)))
        if max_val < 1e-5:
            max_val = 1.0
        normed = (rel / max_val).flatten()
        return normed

    def is_valid_hand_skeleton(self, bbox: Tuple[int, int, int, int], kpts: np.ndarray) -> bool:
        """
        Kiểm tra xem 21 điểm khớp xương có tạo thành cấu trúc bàn tay hợp lệ hay đang bị nhiễu/chưa hội tụ.
        """
        x1, y1, x2, y2 = bbox
        box_diag = math.hypot(max(1, x2 - x1), max(1, y2 - y1))

        xs = kpts[:, 0]
        ys = kpts[:, 1]
        kpt_span = math.hypot(float(np.max(xs) - np.min(xs)), float(np.max(ys) - np.min(ys)))
        if kpt_span < 0.18 * box_diag:
            return False

        palm_len = self._dist(kpts[0], kpts[9])
        if palm_len < 0.10 * box_diag:
            return False

        d_5_9 = self._dist(kpts[5], kpts[9])
        d_9_13 = self._dist(kpts[9], kpts[13])
        d_13_17 = self._dist(kpts[13], kpts[17])
        d_5_17 = self._dist(kpts[5], kpts[17])
        if d_5_17 < 1e-3 or (d_5_9 + d_9_13 + d_13_17) / d_5_17 > 2.6:
            return False

        return True

    def get_finger_states(self, kpts: np.ndarray) -> List[int]:
        """
        Kiểm tra 5 ngón tay đang mở (1) hay gập (0) dựa trên hình học góc khớp PIP/DIP và khoảng cách tới cổ tay/lòng bàn tay.
        Thứ tự: [Thumb (Cái), Index (Trỏ), Middle (Giữa), Ring (Áp út), Pinky (Út)]
        """
        wrist = kpts[0]
        palm_center = (kpts[0][:2] + kpts[5][:2] + kpts[9][:2] + kpts[13][:2] + kpts[17][:2]) / 5.0
        palm_size = max(self._dist(wrist, kpts[9]), self._dist(kpts[5], kpts[17]), 1.0)

        # 1. Ngón cái (Thumb: 1-2-3-4)
        thumb_angle = self._angle_deg(kpts[1], kpts[2], kpts[4])
        thumb_ip_angle = self._angle_deg(kpts[2], kpts[3], kpts[4])
        dist_thumb_tip_pinky = self._dist(kpts[4], kpts[17])
        dist_thumb_mcp_pinky = self._dist(kpts[2], kpts[17])
        dist_thumb_tip_index_mcp = self._dist(kpts[4], kpts[5])
        dist_thumb_tip_middle_mcp = self._dist(kpts[4], kpts[9])

        thumb_open = int(
            thumb_angle > 130.0
            and thumb_ip_angle > 135.0
            and (
                (dist_thumb_tip_pinky > dist_thumb_mcp_pinky + 0.08 * palm_size and dist_thumb_tip_index_mcp > 0.30 * palm_size)
                or dist_thumb_tip_middle_mcp > 0.52 * palm_size
            )
        )

        states = [thumb_open]

        # 2. 4 ngón còn lại: Index (5-6-7-8), Middle (9-10-11-12), Ring (13-14-15-16), Pinky (17-18-19-20)
        finger_joints = [
            (5, 6, 7, 8),
            (9, 10, 11, 12),
            (13, 14, 15, 16),
            (17, 18, 19, 20),
        ]
        for mcp, pip, dip, tip in finger_joints:
            pip_angle = self._angle_deg(kpts[mcp], kpts[pip], kpts[dip])
            dip_angle = self._angle_deg(kpts[pip], kpts[dip], kpts[tip])
            dist_tip_wrist = self._dist(kpts[tip], wrist)
            dist_pip_wrist = self._dist(kpts[pip], wrist)
            dist_mcp_wrist = self._dist(kpts[mcp], wrist)
            dist_tip_palm = self._dist(kpts[tip], palm_center)
            dist_pip_palm = self._dist(kpts[pip], palm_center)

            is_extended = (
                pip_angle > 130.0
                and dip_angle > 125.0
                and dist_tip_wrist > dist_pip_wrist + 0.05 * palm_size
                and dist_tip_wrist > dist_mcp_wrist + 0.18 * palm_size
                and dist_tip_palm > dist_pip_palm
            )
            states.append(1 if is_extended else 0)

        return states

    def classify_touchless_control(
        self,
        kpts: np.ndarray,
        fingers: List[int],
        pinch_mode_enabled: bool = False,
        neural_gesture: Optional[str] = None,
        neural_score: float = 0.0,
    ) -> Tuple[str, Optional[float], Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]:
        """
        Phân loại cử chỉ cho Chế độ Điều khiển Thiết bị Không chạm (Touchless Control).
        Kết hợp Neural Gesture Classifier & 21-Keypoint Geometry.
        """
        wrist = kpts[0]
        palm_size = max(self._dist(wrist, kpts[9]), self._dist(kpts[5], kpts[17]), 1.0)
        thumb_tip = (int(kpts[4][0]), int(kpts[4][1]))
        index_tip = (int(kpts[8][0]), int(kpts[8][1]))
        pinch_dist = self._dist(kpts[4], kpts[8])

        # Chế độ Pinch Volume: CHỈ kích hoạt khi người dùng bật checkbox VÀ tạo đúng tư thế chữ L/nhúm (Cái + Trỏ mở [1, 1, 0, 0, 0])
        if pinch_mode_enabled and fingers == [1, 1, 0, 0, 0]:
            min_d = 0.18 * palm_size
            max_d = 1.25 * palm_size
            ratio = float(np.clip((pinch_dist - min_d) / max(max_d - min_d, 1.0), 0.0, 1.0))
            return "PINCH_VOLUME", ratio, (thumb_tip, index_tip)

        # Ưu tiên kết hợp Neural Gesture từ MediaPipe Tasks nếu độ tự tin cao
        if neural_gesture and neural_score >= 0.60:
            if neural_gesture == "Open_Palm" and sum(fingers) >= 4:
                return "OPEN_PALM", None, None
            if neural_gesture == "Closed_Fist" and sum(fingers) <= 1:
                return "FIST", None, None
            if neural_gesture == "Victory" and fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0 and fingers[4] == 0:
                return "PEACE", None, None
            if neural_gesture == "Thumb_Up" and sum(fingers[1:]) == 0:
                return "THUMBS_UP", None, None
            if neural_gesture == "Thumb_Down" and sum(fingers[1:]) == 0:
                return "THUMBS_DOWN", None, None

        # 1. OPEN_PALM (5 ngón xòe mở): Play / Pause Media
        if sum(fingers) == 5:
            return "OPEN_PALM", None, None

        # 2. FIST (5 ngón nắm lại): Mute / Unmute Audio
        if sum(fingers) == 0:
            # Kiểm tra xem ngón cái có đang giơ thẳng lên hoặc chúc thẳng xuống không
            dy_thumb = kpts[4][1] - kpts[2][1]
            dist_thumb_palm = self._dist(kpts[4], kpts[9])
            if dist_thumb_palm > 0.55 * palm_size:
                if dy_thumb < -0.28 * palm_size:
                    return "THUMBS_UP", None, None
                elif dy_thumb > 0.28 * palm_size:
                    return "THUMBS_DOWN", None, None
            return "FIST", None, None

        # 3. THUMBS_UP / THUMBS_DOWN (Chỉ ngón cái mở, 4 ngón kia gập)
        if fingers == [1, 0, 0, 0, 0]:
            dy = kpts[4][1] - kpts[2][1]
            if dy < -0.18 * palm_size:
                return "THUMBS_UP", None, None
            elif dy > 0.18 * palm_size:
                return "THUMBS_DOWN", None, None

        # 4. PEACE (Ngón trỏ + Ngón giữa mở): Chụp ảnh màn hình
        if fingers == [0, 1, 1, 0, 0] or (fingers == [1, 1, 1, 0, 0] and neural_gesture == "Victory"):
            return "PEACE", None, None

        # 5. POINT_RIGHT / POINT_LEFT (Chỉ ngón trỏ duỗi): Qua bài / Lùi bài
        if fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            dx = kpts[8][0] - kpts[5][0]
            dy = abs(kpts[8][1] - kpts[5][1])
            if abs(dx) > 0.30 * palm_size and abs(dx) > dy * 0.65:
                if dx > 0:
                    return "POINT_RIGHT", None, None
                else:
                    return "POINT_LEFT", None, None

        return "NONE", None, None

    def classify_asl_letter(
        self,
        kpts: np.ndarray,
        fingers: List[int],
        neural_gesture: Optional[str] = None,
        neural_score: float = 0.0,
    ) -> Tuple[str, float]:
        """
        Phân loại bảng chữ cái Ngôn ngữ Ký hiệu ASL (A-Z) + lệnh SPACE / DEL từ 21 keypoints.
        """
        # 1. Ưu tiên khớp trên tập mẫu 21-keypoints người dùng đã lưu (`models/asl_keypoints_db.npz`)
        if self.sample_features is not None and len(self.sample_features) > 0:
            feat = self.extract_normalized_features(kpts)
            dists = np.linalg.norm(self.sample_features - feat, axis=1)
            min_idx = int(np.argmin(dists))
            min_dist = float(dists[min_idx])
            if min_dist < 0.38:
                conf = float(np.clip(1.0 - min_dist, 0.72, 0.99))
                return str(self.sample_labels[min_idx]), conf

        # 2. Bộ giải hình học 21 khớp + Neural Fusion
        wrist = kpts[0]
        palm = max(self._dist(wrist, kpts[9]), self._dist(kpts[5], kpts[17]), 1.0)
        t, i, m, r, p = fingers

        d_thumb_index = self._dist(kpts[4], kpts[8]) / palm
        d_thumb_middle = self._dist(kpts[4], kpts[12]) / palm
        d_thumb_ring = self._dist(kpts[4], kpts[16]) / palm
        d_index_middle = self._dist(kpts[8], kpts[12]) / palm
        d_middle_ring = self._dist(kpts[12], kpts[16]) / palm

        # Bàn tay xòe 5 ngón -> SPACE (Dấu cách)
        if [t, i, m, r, p] == [1, 1, 1, 1, 1]:
            return "SPACE", 0.94

        # B: 4 ngón trỏ-giữa-áp-út duỗi thẳng, ngón cái gập vào lòng bàn tay
        if [t, i, m, r, p] == [0, 1, 1, 1, 1]:
            return "B", 0.93

        # F: Ngón cái và ngón trỏ chạm nhau tạo vòng tròn (OK), 3 ngón giữa-áp út-út duỗi thẳng
        if [m, r, p] == [1, 1, 1] and i == 0 and d_thumb_index < 0.42:
            return "F", 0.92

        # W: 3 ngón trỏ, giữa, áp út duỗi thẳng; ngón cái và ngón út gập
        if [t, i, m, r, p] == [0, 1, 1, 1, 0] or [t, i, m, r, p] == [1, 1, 1, 1, 0]:
            return "W", 0.92

        # Y: Ngón cái và ngón út duỗi (Shaka), 3 ngón giữa gập
        if [t, i, m, r, p] == [1, 0, 0, 0, 1]:
            return "Y", 0.94

        # I / J: Chỉ duy nhất ngón út duỗi thẳng ([0, 0, 0, 0, 1])
        if [t, i, m, r, p] == [0, 0, 0, 0, 1]:
            dx_p = abs(kpts[20][0] - kpts[17][0])
            dy_p = abs(kpts[20][1] - kpts[17][1])
            if dx_p > dy_p * 0.85:
                return "J", 0.89
            return "I", 0.93

        # L / G / Q: Ngón cái và ngón trỏ mở, 3 ngón còn lại gập ([1, 1, 0, 0, 0])
        if [t, i, m, r, p] == [1, 1, 0, 0, 0]:
            dx = abs(kpts[8][0] - kpts[5][0])
            dy = kpts[8][1] - kpts[5][1]
            if dy > 0.35 * palm:
                return "Q", 0.86
            if dx > abs(dy) * 1.15:
                return "G", 0.87
            return "L", 0.94

        # D / Z / DEL: Chỉ ngón trỏ duỗi ([0, 1, 0, 0, 0])
        if [t, i, m, r, p] == [0, 1, 0, 0, 0]:
            dx = kpts[8][0] - kpts[5][0]
            dy = abs(kpts[8][1] - kpts[5][1])
            if dx < -0.42 * palm and abs(dx) > dy:
                return "DEL", 0.88
            if dx > 0.42 * palm and abs(dx) > dy:
                return "Z", 0.88
            return "D", 0.91

        # V / U / R / K / H / P: Ngón trỏ và ngón giữa duỗi ([_, 1, 1, 0, 0])
        if [i, m, r, p] == [1, 1, 0, 0]:
            dx = abs(kpts[8][0] - kpts[5][0])
            dy = kpts[8][1] - kpts[5][1]
            if dy > 0.35 * palm:
                return "P", 0.86
            if dx > abs(dy) * 1.15:
                return "H", 0.88
            if t == 1:
                return "K", 0.88
            if d_index_middle < 0.16:
                return "R", 0.86
            elif d_index_middle < 0.28:
                return "U", 0.90
            else:
                return "V", 0.94

        # A: Ngón cái duỗi dọc cạnh nắm đấm ([1, 0, 0, 0, 0])
        if [t, i, m, r, p] == [1, 0, 0, 0, 0]:
            return "A", 0.90

        # O / C / S / E / M / N / T / X: Khi cả 5 ngón đều cong hoặc nắm ([0, 0, 0, 0, 0])
        if [t, i, m, r, p] == [0, 0, 0, 0, 0]:
            index_pip_angle = self._angle_deg(kpts[5], kpts[6], kpts[8])
            # O: Đầu ngón cái và đầu ngón trỏ chạm sát nhau tạo chữ O
            if d_thumb_index < 0.28 and d_thumb_middle < 0.36:
                return "O", 0.90
            # C: Ngón trỏ cong hình vòng cung và cách ngón cái một khoảng vừa phải
            if 75.0 < index_pip_angle < 135.0 and 0.32 <= d_thumb_index <= 0.78:
                return "C", 0.86
            # X: Ngón trỏ hơi nhô cao hơn hẳn 3 ngón giữa-áp-út và cong ở khớp PIP
            if kpts[6][1] < kpts[10][1] - 0.18 * palm and index_pip_angle < 120.0:
                return "X", 0.84
            # M / N / T: Dựa trên vị trí đầu ngón cái (kpt 4) luồn dưới các ngón tay
            if d_thumb_ring < 0.26:
                return "M", 0.85
            if d_thumb_middle < 0.26:
                return "N", 0.85
            if d_thumb_index < 0.30 and kpts[4][1] < kpts[8][1]:
                return "T", 0.85
            # S vs E:
            if kpts[4][1] < kpts[6][1]:
                return "S", 0.88
            return "E", 0.85

        return "NOTHING", 0.0

    def analyze(
        self,
        bbox: Tuple[int, int, int, int],
        keypoints: np.ndarray,
        det_conf: float,
        pinch_mode_enabled: bool = False,
        neural_gesture: Optional[str] = None,
        neural_score: float = 0.0,
    ) -> HandPoseAnalysis:
        """Phân tích toàn diện 1 bàn tay từ 21 keypoints + Neural Gesture."""
        if not self.is_valid_hand_skeleton(bbox, keypoints):
            return HandPoseAnalysis(
                bbox=bbox,
                keypoints=keypoints,
                det_confidence=det_conf,
                fingers_up=[0, 0, 0, 0, 0],
                asl_label="NOTHING",
                asl_confidence=0.0,
                control_gesture="NONE",
                pinch_ratio=None,
                pinch_points=None,
            )

        fingers = self.get_finger_states(keypoints)
        asl_label, asl_conf = self.classify_asl_letter(
            keypoints, fingers, neural_gesture=neural_gesture, neural_score=neural_score
        )
        ctrl_gesture, pinch_ratio, pinch_pts = self.classify_touchless_control(
            keypoints,
            fingers,
            pinch_mode_enabled=pinch_mode_enabled,
            neural_gesture=neural_gesture,
            neural_score=neural_score,
        )

        return HandPoseAnalysis(
            bbox=bbox,
            keypoints=keypoints,
            det_confidence=det_conf,
            fingers_up=fingers,
            asl_label=asl_label,
            asl_confidence=asl_conf,
            control_gesture=ctrl_gesture,
            pinch_ratio=pinch_ratio,
            pinch_points=pinch_pts,
        )
