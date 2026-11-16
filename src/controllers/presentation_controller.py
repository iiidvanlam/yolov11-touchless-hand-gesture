"""
Chế độ Thuyết trình thông minh:
  - Chỉ ngón trỏ (các ngón khác gập) : Hiện tia laser đỏ ảo trên toàn màn hình.
  - Xòe bàn tay và vẫy sang TRÁI      : Slide tiếp theo (phím Mũi tên Phải).
  - Xòe bàn tay và vẫy sang PHẢI      : Slide trước (phím Mũi tên Trái).
Hoạt động với PowerPoint (chế độ trình chiếu), Google Slides, trình đọc PDF...
"""

import ctypes
import time
from collections import deque
from typing import Deque, Dict, Optional, Tuple

import numpy as np

from src.controllers.air_mouse import DEFAULT_ACTIVE_REGION, map_to_region

VK_LEFT = 0x25
VK_RIGHT = 0x27
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


class PresentationController:
    def __init__(
        self,
        swipe_dist_ratio: float = 0.22,   # Quãng vẫy tối thiểu (tỷ lệ chiều rộng khung hình)
        window_s: float = 0.45,           # Cửa sổ thời gian để hoàn thành cú vẫy
        cooldown_s: float = 1.0,
        region=DEFAULT_ACTIVE_REGION,
    ):
        self.swipe_dist_ratio = swipe_dist_ratio
        self.window_s = window_s
        self.cooldown_s = cooldown_s
        self.region = region
        self.history: Deque[Tuple[float, float, float]] = deque()
        self.last_swipe_t = 0.0
        self.slide_count = 0

    @staticmethod
    def _press(vk: int) -> None:
        try:
            ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
            ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def reset(self) -> None:
        self.history.clear()

    def update(self, kpts: np.ndarray, fingers, frame_w: int, frame_h: int) -> Dict[str, object]:
        now = time.perf_counter()
        result: Dict[str, object] = {"laser": None, "event": None, "state": "IDLE"}

        pointing = fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0
        open_palm = sum(fingers[1:]) >= 3

        if pointing:
            self.history.clear()
            result["laser"] = map_to_region(kpts[8][0], kpts[8][1], frame_w, frame_h, self.region)
            result["state"] = "LASER"
            return result

        if not open_palm:
            self.history.clear()
            return result

        result["state"] = "SWIPE_READY"
        center = np.mean(kpts[[0, 5, 9, 13, 17], :2], axis=0)
        self.history.append((now, float(center[0]) / max(frame_w, 1), float(center[1]) / max(frame_h, 1)))
        while self.history and now - self.history[0][0] > self.window_s:
            self.history.popleft()

        if now - self.last_swipe_t < self.cooldown_s or len(self.history) < 3:
            return result

        dx = self.history[-1][1] - self.history[0][1]
        dy = self.history[-1][2] - self.history[0][2]
        if abs(dx) >= self.swipe_dist_ratio and abs(dy) < 0.6 * abs(dx):
            if dx < 0:
                self._press(VK_RIGHT)
                self.slide_count += 1
                result["event"] = "Slide tiếp theo ▶"
            else:
                self._press(VK_LEFT)
                self.slide_count = max(0, self.slide_count - 1)
                result["event"] = "◀ Slide trước"
            self.last_swipe_t = now
            self.history.clear()
        return result
