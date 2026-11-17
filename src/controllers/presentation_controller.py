"""
Chế độ Thuyết trình thông minh:
  - Chỉ ngón trỏ (các ngón khác gập) : Hiện tia laser đỏ ảo trên toàn màn hình.
  - Xòe bàn tay và vẫy sang TRÁI      : Slide tiếp theo (phím Mũi tên Phải).
  - Xòe bàn tay và vẫy sang PHẢI      : Slide trước (phím Mũi tên Trái).
Hoạt động với PowerPoint (chế độ trình chiếu), Google Slides, trình đọc PDF...
"""

import ctypes
from ctypes import wintypes
import time
from collections import deque
from typing import Deque, Dict, Optional, Tuple

import numpy as np

from src.controllers.air_mouse import DEFAULT_ACTIVE_REGION, map_to_region

VK_LEFT = 0x25
VK_RIGHT = 0x27
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", _MOUSEINPUT),
        ("ki", _KEYBDINPUT),
        ("hi", _HARDWAREINPUT),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


class PresentationController:
    def __init__(
        self,
        swipe_dist_ratio: float = 0.14,   # Quãng vẫy tối thiểu (14% chiều rộng khung hình)
        window_s: float = 0.85,           # Cửa sổ thời gian thoải mái cho thao tác vẫy tự nhiên
        cooldown_s: float = 0.90,         # Thời gian nghỉ sau mỗi lần chuyển slide (chống hồi tay)
        grace_frames: int = 5,            # Cho phép mất dấu/mờ ảnh tối đa 5 frame khi vẫy nhanh
        region=DEFAULT_ACTIVE_REGION,
    ):
        self.swipe_dist_ratio = swipe_dist_ratio
        self.window_s = window_s
        self.cooldown_s = cooldown_s
        self.grace_frames = grace_frames
        self.region = region
        self.history: Deque[Tuple[float, float, float]] = deque()
        self.last_swipe_t = 0.0
        self.slide_count = 0
        self.miss_count = 0
        self.pointing_streak = 0

    @staticmethod
    def _press(vk: int) -> None:
        """Gửi phím mũi tên qua Windows SendInput kèm mã quét phần cứng (wScan)."""
        try:
            user32 = ctypes.windll.user32
            scan = int(user32.MapVirtualKeyW(vk, 0))
            flags_down = KEYEVENTF_EXTENDEDKEY
            flags_up = KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP

            inputs = (_INPUT * 2)()
            inputs[0].type = INPUT_KEYBOARD
            inputs[0].union.ki = _KEYBDINPUT(vk, scan, flags_down, 0, 0)
            inputs[1].type = INPUT_KEYBOARD
            inputs[1].union.ki = _KEYBDINPUT(vk, scan, flags_up, 0, 0)

            sent = user32.SendInput(2, inputs, ctypes.sizeof(_INPUT))
            if sent == 0:
                user32.keybd_event(vk, scan, flags_down, 0)
                user32.keybd_event(vk, scan, flags_up, 0)
        except Exception:
            pass

    def reset(self) -> None:
        self.history.clear()
        self.miss_count = 0
        self.pointing_streak = 0

    def on_no_hand(self) -> None:
        """Gọi khi 1 khung hình không phát hiện bàn tay: dùng grace_frames để không cắt đứt cú vẫy nhanh."""
        self.pointing_streak = 0
        self.miss_count += 1
        if self.miss_count >= self.grace_frames:
            self.history.clear()

    def update(
        self,
        kpts: np.ndarray,
        fingers,
        frame_w: int,
        frame_h: int,
        enable_swipe: bool = True,
    ) -> Dict[str, object]:
        now = time.perf_counter()
        result: Dict[str, object] = {"laser": None, "event": None, "state": "IDLE", "progress": 0.0}

        pointing = fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0
        open_palm = (not pointing) and (sum(fingers) >= 3)

        if pointing:
            self.miss_count = 0
            self.pointing_streak += 1
            if self.pointing_streak >= 3:
                self.history.clear()
            result["laser"] = map_to_region(kpts[8][0], kpts[8][1], frame_w, frame_h, self.region)
            result["state"] = "LASER"
            result["progress"] = 1.0
            return result

        self.pointing_streak = 0

        # Trong thời gian cooldown sau khi vừa chuyển slide: xóa lịch sử để động tác rút tay về không bị lật ngược
        if (now - self.last_swipe_t) < self.cooldown_s:
            self.history.clear()
            self.miss_count = 0
            result["state"] = "COOLDOWN"
            return result

        if not open_palm:
            self.miss_count += 1
            if self.miss_count >= self.grace_frames:
                self.history.clear()
                result["state"] = "IDLE"
            elif self.history:
                result["state"] = "SWIPE_READY"
            return result

        self.miss_count = 0
        result["state"] = "SWIPE_READY"

        # Theo dõi tâm lòng bàn tay kết hợp đầu ngón giữa để bắt cả vẫy cánh tay lẫn lắc cổ tay
        center = np.mean(kpts[[0, 5, 9, 12, 13, 17], :2], axis=0)
        cx = float(center[0]) / max(frame_w, 1)
        cy = float(center[1]) / max(frame_h, 1)
        self.history.append((now, cx, cy))
        while self.history and (now - self.history[0][0]) > self.window_s:
            self.history.popleft()

        if len(self.history) < 3:
            return result

        # Tìm điểm cực tiểu và cực đại theo trục X trong cửa sổ thời gian để không bị hụt nếu cuối cú vẫy hơi chững lại
        min_idx = min(range(len(self.history)), key=lambda i: self.history[i][1])
        max_idx = max(range(len(self.history)), key=lambda i: self.history[i][1])
        t_min, x_min, y_min = self.history[min_idx]
        t_max, x_max, y_max = self.history[max_idx]

        span_x = x_max - x_min
        span_y = abs(y_max - y_min)
        result["progress"] = min(1.0, span_x / max(self.swipe_dist_ratio, 1e-5))

        if enable_swipe and span_x >= self.swipe_dist_ratio and span_y < 0.90 * span_x:
            if t_min > t_max:
                # Tay đi từ Phải -> Trái (dx < 0)
                self._press(VK_RIGHT)
                self.slide_count += 1
                result["event"] = "Slide tiếp theo ▶"
            else:
                # Tay đi từ Trái -> Phải (dx > 0)
                self._press(VK_LEFT)
                self.slide_count = max(0, self.slide_count - 1)
                result["event"] = "◀ Slide trước"
            result["progress"] = 1.0
            self.last_swipe_t = now
            self.history.clear()
        return result
