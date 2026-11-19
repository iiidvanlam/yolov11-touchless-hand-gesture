"""
Chuột không chạm (Air Mouse):
  - Đầu ngón trỏ (Keypoint 8) điều khiển con trỏ chuột Windows.
  - Chụm Cái + Trỏ (4-8)  : Nhấn chuột trái (giữ > 0.35s = kéo thả / drag).
  - Chụm Cái + Giữa (4-12): Nhấp chuột phải.
  - Co ngón trỏ vào lòng bàn tay (nắm tay): "Ly hợp" - tạm dừng con trỏ để đặt lại vị trí tay.
"""

import ctypes
import math
import time
from typing import Dict, Optional, Tuple

import numpy as np

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

# Vùng hoạt động trong khung hình camera (chuẩn hóa 0..1) ánh xạ ra toàn màn hình.
# Thu nhỏ vùng giúp không phải với tay ra sát mép camera.
DEFAULT_ACTIVE_REGION = (0.15, 0.12, 0.85, 0.72)  # (x1, y1, x2, y2)


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(math.hypot(float(a[0] - b[0]), float(a[1] - b[1])))


def palm_size(kpts: np.ndarray) -> float:
    return max(_dist(kpts[0], kpts[9]), _dist(kpts[5], kpts[17]), 1.0)


def map_to_region(
    px: float, py: float, frame_w: int, frame_h: int,
    region: Tuple[float, float, float, float] = DEFAULT_ACTIVE_REGION,
) -> Tuple[float, float]:
    """Ánh xạ tọa độ pixel trong khung hình sang tọa độ chuẩn hóa 0..1 của màn hình."""
    x1, y1, x2, y2 = region
    w_reg = max(x2 - x1, 1e-6)
    h_reg = max(y2 - y1, 1e-6)
    nx = (px / max(frame_w, 1) - x1) / w_reg
    ny = (py / max(frame_h, 1) - y1) / h_reg
    return float(np.clip(nx, 0.0, 1.0)), float(np.clip(ny, 0.0, 1.0))


class AirMouseController:
    PINCH_ON = 0.28       # Tỷ lệ khoảng cách/palm để coi là "chụm"
    PINCH_OFF = 0.40      # Ngưỡng nhả (hysteresis chống nhấp đúp ngoài ý muốn)
    FREEZE_RATIO = 0.50   # Khi ngón cái tiến gần ngón trỏ -> khóa con trỏ để nhấp chính xác
    DRAG_DELAY = 0.35     # Giữ chụm lâu hơn thời gian này -> chuyển sang kéo thả
    RIGHT_COOLDOWN = 0.7
    DEAD_ZONE_PX = 1.5

    def __init__(self, smoothing: float = 0.45, region=DEFAULT_ACTIVE_REGION):
        self.alpha = smoothing
        self.region = region
        self.screen_w, self.screen_h = self._screen_size()
        self.cur_x: Optional[float] = None
        self.cur_y: Optional[float] = None
        self.left_down = False
        self.left_down_t = 0.0
        self.right_armed = True
        self.last_right_t = 0.0
        self.valid_streak = 0

    @staticmethod
    def _screen_size() -> Tuple[int, int]:
        try:
            u32 = ctypes.windll.user32
            return int(u32.GetSystemMetrics(0)), int(u32.GetSystemMetrics(1))
        except Exception:
            return 1920, 1080

    @staticmethod
    def _mouse(flag: int) -> None:
        try:
            ctypes.windll.user32.mouse_event(flag, 0, 0, 0, 0)
        except Exception:
            pass

    def _move(self, x: float, y: float) -> None:
        try:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
        except Exception:
            pass

    def release(self) -> None:
        """Nhả mọi nút chuột đang giữ (gọi khi mất bàn tay hoặc đổi chế độ)."""
        if self.left_down:
            self._mouse(MOUSEEVENTF_LEFTUP)
            self.left_down = False
        self.cur_x = self.cur_y = None
        self.right_armed = True
        self.valid_streak = 0

    def update(
        self,
        kpts: np.ndarray,
        frame_w: int,
        frame_h: int,
        fingers: Optional[list] = None,
    ) -> Dict[str, object]:
        now = time.perf_counter()
        palm = palm_size(kpts)
        r_left = _dist(kpts[4], kpts[8]) / palm
        r_right = _dist(kpts[4], kpts[12]) / palm
        # "Ly hợp": ngón trỏ gập vào lòng bàn tay (và không đang chụm kéo chuột) => tạm dừng con trỏ
        index_folded = (fingers is not None and len(fingers) >= 2 and fingers[1] == 0 and r_left > self.PINCH_OFF)
        clutch = index_folded or (r_left > self.PINCH_OFF and _dist(kpts[8], kpts[0]) < 1.18 * _dist(kpts[5], kpts[0]))

        event = ""
        nx, ny = map_to_region(kpts[8][0], kpts[8][1], frame_w, frame_h, self.region)
        tx, ty = nx * (self.screen_w - 1), ny * (self.screen_h - 1)

        if clutch:
            if self.left_down:
                self._mouse(MOUSEEVENTF_LEFTUP)
                self.left_down = False
            self.cur_x = self.cur_y = None
            return {"state": "CLUTCH", "event": "Tạm dừng con trỏ (gập ngón trỏ / nắm tay)", "nx": nx, "ny": ny,
                    "r_left": r_left, "r_right": r_right, "dragging": False}

        # Đòi hỏi tối thiểu 2 frame bàn tay hợp lệ liên tiếp trước khi cho phép di chuyển chuột thật
        self.valid_streak += 1
        if self.valid_streak < 2:
            return {"state": "READY", "event": "Đang xác nhận bàn tay...", "nx": nx, "ny": ny,
                    "r_left": r_left, "r_right": r_right, "dragging": False}

        # --- Máy trạng thái chuột trái (click + drag) ---
        if not self.left_down and r_left < self.PINCH_ON:
            self._mouse(MOUSEEVENTF_LEFTDOWN)
            self.left_down = True
            self.left_down_t = now
            event = "Nhấn chuột trái"
        elif self.left_down and r_left > self.PINCH_OFF:
            self._mouse(MOUSEEVENTF_LEFTUP)
            self.left_down = False
            event = "Nhả chuột trái"

        dragging = self.left_down and (now - self.left_down_t) >= self.DRAG_DELAY

        # --- Chuột phải (chụm Cái + Giữa trong khi Cái - Trỏ đang mở) ---
        if r_right > self.PINCH_OFF:
            self.right_armed = True
        if (
            not self.left_down
            and self.right_armed
            and r_right < self.PINCH_ON
            and r_left > self.PINCH_OFF
            and now - self.last_right_t > self.RIGHT_COOLDOWN
        ):
            self._mouse(MOUSEEVENTF_RIGHTDOWN)
            self._mouse(MOUSEEVENTF_RIGHTUP)
            self.right_armed = False
            self.last_right_t = now
            event = "Nhấp chuột phải"

        # --- Di chuyển con trỏ ---
        freeze = (self.left_down and not dragging) or (not self.left_down and r_left < self.FREEZE_RATIO)
        if not freeze:
            if self.cur_x is None:
                self.cur_x, self.cur_y = tx, ty
            else:
                nx_s = self.alpha * tx + (1 - self.alpha) * self.cur_x
                ny_s = self.alpha * ty + (1 - self.alpha) * self.cur_y
                if abs(nx_s - self.cur_x) > self.DEAD_ZONE_PX or abs(ny_s - self.cur_y) > self.DEAD_ZONE_PX:
                    self.cur_x, self.cur_y = nx_s, ny_s
            self._move(self.cur_x, self.cur_y)

        if dragging:
            state = "DRAG"
        elif self.left_down:
            state = "LEFT_DOWN"
        elif freeze:
            state = "AIM"
        else:
            state = "MOVE"
        return {"state": state, "event": event, "nx": nx, "ny": ny,
                "r_left": r_left, "r_right": r_right, "dragging": dragging}
