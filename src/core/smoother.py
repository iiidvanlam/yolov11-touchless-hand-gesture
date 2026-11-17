from collections import Counter, deque
import math
import time
from typing import Dict, Optional, Tuple
import numpy as np


class OneEuroFilter:
    """
    Bộ lọc thông thấp thích ứng One-Euro Filter (1€ Filter - Casiez et al., CHI 2012).
    Tiêu chuẩn vàng trong theo dõi bàn tay VR/AR (Meta Quest / Apple Vision Pro):
      - Khi bàn tay đứng yên: tần số cắt giảm xuống `min_cutoff`, triệt tiêu 99% rung nhiễu (jitter).
      - Khi bàn tay di chuyển nhanh: tần số cắt tự động mở rộng theo tốc độ (`beta`), triệt tiêu độ trễ (lag).
    """

    def __init__(
        self,
        min_cutoff: float = 1.4,
        beta: float = 0.035,
        d_cutoff: float = 1.0,
    ):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev: Optional[np.ndarray] = None
        self.dx_prev: Optional[np.ndarray] = None
        self.t_prev: Optional[float] = None

    @staticmethod
    def _smoothing_factor(t_e: float, cutoff: np.ndarray) -> np.ndarray:
        r = 2.0 * math.pi * cutoff * t_e
        return r / (r + 1.0)

    def filter(self, x: np.ndarray, timestamp: Optional[float] = None) -> np.ndarray:
        t = time.perf_counter() if timestamp is None else timestamp
        x_arr = np.asarray(x, dtype=np.float32)

        if self.x_prev is None or self.t_prev is None:
            self.x_prev = x_arr.copy()
            self.dx_prev = np.zeros_like(x_arr, dtype=np.float32)
            self.t_prev = t
            return x_arr.copy()

        t_e = max(1e-3, min(0.25, t - self.t_prev))
        self.t_prev = t

        # Nếu tọa độ nhảy quá xa (bàn tay mới xuất hiện ở vị trí khác), reset ngay lập tức
        jump_dist = float(np.max(np.linalg.norm(x_arr - self.x_prev, axis=-1)))
        if jump_dist > 140.0:
            self.x_prev = x_arr.copy()
            self.dx_prev = np.zeros_like(x_arr, dtype=np.float32)
            return x_arr.copy()

        a_d = self._smoothing_factor(t_e, np.full_like(x_arr, self.d_cutoff))
        dx = (x_arr - self.x_prev) / t_e
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)
        a = self._smoothing_factor(t_e, cutoff)
        x_hat = a * x_arr + (1.0 - a) * self.x_prev

        self.x_prev = x_hat.copy()
        self.dx_prev = dx_hat.copy()
        return x_hat

    def reset(self) -> None:
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None


class OneEuroKeypointSmoother:
    """Bộ làm mượt 21 điểm khớp xương bàn tay `(21, 3)` bằng thuật toán 1€ Filter."""

    def __init__(self, min_cutoff: float = 1.4, beta: float = 0.035):
        self.coord_filter = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=1.0)

    def update(self, keypoints: np.ndarray) -> np.ndarray:
        out = keypoints.copy().astype(np.float32)
        out[:, :2] = self.coord_filter.filter(out[:, :2])
        return out

    def reset(self) -> None:
        self.coord_filter.reset()


class VotingBuffer:
    """
    Bộ lọc ổn định khung hình (Sliding Window Voting Buffer).
    Giúp chống nhảy chữ liên tục khi nhận diện bảng chữ cái ASL (A-Z) ở tốc độ 30-60 FPS.
    """

    def __init__(self, window_size: int = 12, min_votes: int = 8, min_confidence: float = 0.65):
        self.window_size = window_size
        self.min_votes = min_votes
        self.min_confidence = min_confidence
        self.buffer: deque = deque(maxlen=window_size)
        self.last_committed_label: Optional[str] = None
        self.none_streak: int = 0

    def update(self, label: Optional[str], confidence: float = 1.0) -> Tuple[Optional[str], float, Optional[str]]:
        """
        Cập nhật dự đoán ở frame hiện tại.
        Trả về:
          - committed_label: Nhãn vừa được xác nhận (hoặc None nếu chưa đủ điều kiện)
          - hold_progress: Tiến độ giữ cử chỉ từ 0.0 -> 1.0 (để vẽ thanh tiến trình lên UI)
          - candidate_label: Nhãn đang chiếm đa số trong buffer
        """
        if not label or confidence < self.min_confidence or label in ("NOTHING", "NONE", "UNKNOWN"):
            self.buffer.append(None)
            self.none_streak += 1
            # Khi hạ tay khỏi khung hình hoặc dừng ký hiệu >= 8 frames, mở khóa để cho phép lặp lại chữ cái cũ
            if self.none_streak >= 8:
                self.last_committed_label = None
            return None, 0.0, None

        self.none_streak = 0
        self.buffer.append(label)
        valid_items = [item for item in self.buffer if item is not None]
        if not valid_items:
            return None, 0.0, None

        most_common_label, count = Counter(valid_items).most_common(1)[0]

        # Nếu người dùng vẫn đang giữ nguyên chữ cái vừa mới gõ xong -> không gõ lặp lại (tránh bị "EEEEE")
        if most_common_label == self.last_committed_label:
            return None, 1.0, most_common_label

        progress = min(1.0, count / float(self.min_votes))

        if count >= self.min_votes:
            self.last_committed_label = most_common_label
            self.buffer.clear()
            return most_common_label, 1.0, most_common_label

        return None, progress, most_common_label

    def reset(self) -> None:
        self.buffer.clear()
        self.last_committed_label = None
        self.none_streak = 0


class CommandCooldown:
    """
    Bộ chống lặp lệnh (Debounce / Cooldown Timer) cho Chế độ Điều khiển Không chạm.
    Mỗi lệnh có thời gian nghỉ riêng (ví dụ: Play/Pause nghỉ 1.5s, Tăng/Giảm âm lượng nghỉ 0.28s).
    """

    DEFAULT_COOLDOWNS: Dict[str, float] = {
        "OPEN_PALM": 1.5,     # Play / Pause Media
        "FIST": 1.5,          # Mute / Unmute
        "THUMBS_UP": 0.70,    # Volume +6% (giữ tay sẽ lặp lại mỗi 0.7s)
        "THUMBS_DOWN": 0.70,  # Volume -6%
        "POINT_RIGHT": 1.1,   # Next Track
        "POINT_LEFT": 1.1,    # Previous Track
        "PEACE": 1.8,         # Chụp màn hình
    }

    def __init__(self, required_hold_frames: int = 4):
        self.required_hold_frames = required_hold_frames
        self.current_gesture: Optional[str] = None
        self.hold_count: int = 0
        self.last_triggered: Dict[str, float] = {}

    def check_trigger(self, gesture: Optional[str]) -> Tuple[bool, float]:
        """
        Kiểm tra xem cử chỉ điều khiển đã được giữ đủ số frame và hết thời gian cooldown chưa.
        Trả về (được_kích_hoạt, tiến_độ_giữ_0_đến_1).
        """
        if not gesture or gesture in ("NONE", "UNKNOWN", "PINCH_VOLUME", "NOTHING"):
            self.current_gesture = None
            self.hold_count = 0
            return False, 0.0

        if gesture == self.current_gesture:
            self.hold_count += 1
        else:
            self.current_gesture = gesture
            self.hold_count = 1

        progress = min(1.0, self.hold_count / float(self.required_hold_frames))
        if self.hold_count < self.required_hold_frames:
            return False, progress

        now = time.perf_counter()
        cooldown = self.DEFAULT_COOLDOWNS.get(gesture, 1.0)
        last_time = self.last_triggered.get(gesture, 0.0)

        if (now - last_time) >= cooldown:
            self.last_triggered[gesture] = now
            return True, 1.0

        return False, progress


class ExponentialMovingAverage:
    """Làm mượt giá trị liên tục (dùng cho khoảng cách Pinch điều chỉnh thanh âm lượng 0-100%)."""

    def __init__(self, alpha: float = 0.25):
        self.alpha = alpha
        self.value: Optional[float] = None

    def update(self, new_val: float) -> float:
        if self.value is None:
            self.value = new_val
        else:
            self.value = self.alpha * new_val + (1.0 - self.alpha) * self.value
        return self.value

    def reset(self) -> None:
        self.value = None


class PinchVolumeLock:
    """
    Máy trạng thái cho Pinch Volume, chống hiện tượng "chỉnh xong lại tự tăng":
      - ARMED  : Đợi giữ đúng tư thế Pinch đủ `entry_frames` liên tiếp mới bắt đầu chỉnh (tránh lướt qua).
      - ADJUST : Âm lượng bám theo khoảng cách Cái-Trỏ.
      - LOCKED : Giữ yên tay >= `stable_seconds` -> chốt âm lượng, bỏ qua mọi chuyển động sau đó.
      - Khi rời tư thế Pinch mà CHƯA khóa: hoàn tác về giá trị trước lúc rút tay (`rollback_s` hoặc `pre_pinch_ratio`),
        vì lúc rút tay ngón cái/trỏ tự tách ra làm âm lượng vọt lên ngoài ý muốn.
      - Muốn chỉnh lại sau khi khóa: rời tư thế Pinch >= `rearm_frames` khung hình rồi làm lại.
    """

    def __init__(
        self,
        stable_seconds: float = 0.65,
        stable_tol: float = 0.035,
        rollback_s: float = 0.35,
        entry_frames: int = 3,
        exit_frames: int = 3,
        rearm_frames: int = 10,
        deadband: float = 0.015,
    ):
        self.stable_seconds = stable_seconds
        self.stable_tol = stable_tol
        self.rollback_s = rollback_s
        self.entry_frames = entry_frames
        self.exit_frames = exit_frames
        self.rearm_frames = rearm_frames
        self.deadband = deadband
        self.history: deque = deque()
        self.locked = False
        self.active = False
        self.entry_count = 0
        self.pre_pinch_ratio: Optional[float] = None
        self.anchor: Optional[float] = None
        self.stable_since = 0.0
        self.last_applied: Optional[float] = None
        self.away_frames = 0
        self.exit_start_t: Optional[float] = None

    def update(
        self, ratio: float, pre_pinch_ratio: Optional[float] = None
    ) -> Tuple[Optional[float], str, float]:
        """Gọi mỗi khung hình đang ở tư thế Pinch. Trả về (giá_trị_cần_áp_dụng|None, trạng_thái, tiến_độ_khóa)."""
        now = time.perf_counter()
        self.away_frames = 0
        self.exit_start_t = None
        if self.locked:
            return None, "LOCKED", 1.0

        if not self.active:
            if self.pre_pinch_ratio is None and pre_pinch_ratio is not None:
                self.pre_pinch_ratio = pre_pinch_ratio
            self.entry_count += 1
            if self.entry_count < self.entry_frames:
                return None, "ARMING", 0.0
            self.active = True

        self.history.append((now, ratio))
        while self.history and now - self.history[0][0] > 1.5:
            self.history.popleft()

        if self.anchor is None or abs(ratio - self.anchor) > self.stable_tol:
            self.anchor = ratio
            self.stable_since = now
        elapsed = now - self.stable_since
        lock_progress = min(1.0, elapsed / self.stable_seconds)
        if elapsed >= self.stable_seconds:
            self.locked = True
            self.last_applied = self.anchor
            return self.anchor, "LOCKED", 1.0

        if self.last_applied is None or abs(ratio - self.last_applied) >= self.deadband:
            self.last_applied = ratio
            return ratio, "ADJUST", lock_progress
        return None, "ADJUST", lock_progress

    def on_not_pinch(self) -> Optional[float]:
        """Gọi mỗi khung hình KHÔNG ở tư thế Pinch (kể cả mất bàn tay). Trả về giá trị hoàn tác nếu cần."""
        now = time.perf_counter()
        self.away_frames += 1
        if self.exit_start_t is None:
            self.exit_start_t = now
        if not self.active:
            self.entry_count = 0

        rollback: Optional[float] = None
        # Chỉ coi là "rời tay" khi mất Pinch liên tục vài frame (tránh 1 frame nhiễu làm hoàn tác sai)
        if self.away_frames == self.exit_frames and self.active and not self.locked:
            target_t = self.exit_start_t - self.rollback_s
            older = [r for (t, r) in self.history if t <= target_t]
            if older:
                rollback = older[-1]
            elif self.pre_pinch_ratio is not None:
                rollback = self.pre_pinch_ratio
            self.active = False
            self.entry_count = 0
            self.pre_pinch_ratio = None
            self.history.clear()
            self.anchor = None

        if self.away_frames >= self.rearm_frames:
            self.locked = False
            self.active = False
            self.entry_count = 0
            self.pre_pinch_ratio = None
            self.last_applied = None
            self.anchor = None
            self.history.clear()
        return rollback

    def reset(self) -> None:
        self.history.clear()
        self.locked = False
        self.active = False
        self.entry_count = 0
        self.pre_pinch_ratio = None
        self.anchor = None
        self.last_applied = None
        self.away_frames = 0
        self.exit_start_t = None
