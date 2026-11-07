import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np


class ThreadedCamera:
    """
    Đọc luồng video từ Webcam trên một luồng (Thread) riêng biệt.
    Giúp giao diện Desktop và mô hình YOLO luôn lấy được frame mới nhất mà không bị trễ buffer.
    """

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, flip_horizontal: bool = True):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.flip_horizontal = flip_horizontal

        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        self.latest_frame: Optional[np.ndarray] = None
        self.ret = False
        self.fps = 0.0
        self._last_time = time.perf_counter()

    def start(self) -> bool:
        """Khởi động camera và luồng đọc frame."""
        if self.running:
            return True

        # Ưu tiên CAP_DSHOW trên Windows để mở webcam nhanh hơn
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.ret, frame = self.cap.read()
        if self.ret and frame is not None:
            if self.flip_horizontal:
                frame = cv2.flip(frame, 1)
            self.latest_frame = frame

        self.running = True
        self._last_time = time.perf_counter()
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        return True

    def _update_loop(self) -> None:
        """Vòng lặp chạy ngầm liên tục cập nhật frame mới nhất."""
        while self.running and self.cap is not None:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            if self.flip_horizontal:
                frame = cv2.flip(frame, 1)

            now = time.perf_counter()
            dt = now - self._last_time
            self._last_time = now
            if dt > 0:
                instant_fps = 1.0 / dt
                self.fps = 0.85 * self.fps + 0.15 * instant_fps if self.fps > 0 else instant_fps

            with self.lock:
                self.ret = ret
                self.latest_frame = frame

    def read(self) -> Tuple[bool, Optional[np.ndarray], float]:
        """Trả về (thành_công, bản_sao_frame_mới_nhất, fps_hiện_tại)."""
        with self.lock:
            if not self.ret or self.latest_frame is None:
                return False, None, 0.0
            return True, self.latest_frame.copy(), self.fps

    def stop(self) -> None:
        """Dừng luồng đọc và giải phóng thiết bị Webcam."""
        self.running = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        with self.lock:
            self.latest_frame = None
            self.ret = False
