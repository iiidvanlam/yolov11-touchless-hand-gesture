import ctypes
import datetime
import os
from typing import Optional
import cv2
import numpy as np


# Mã phím ảo Windows (Virtual-Key Codes) cho điều khiển Media không cần cài thêm thư viện ngoài
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


class WindowsMediaController:
    """
    Bộ điều khiển thiết bị Windows không chạm (Touchless Control).
    Hỗ trợ:
      - Điều chỉnh phần trăm âm lượng hệ thống trực tiếp (qua PyCAW hoặc Windows Virtual Key API có sẵn).
      - Bật/Tắt tiếng (Mute/Unmute).
      - Tạm dừng / Phát tiếp video hoặc nhạc (Play/Pause).
      - Chuyển bài tiếp theo / Quay lại bài trước (Next / Previous Track).
      - Chụp ảnh màn hình nhanh.
    """

    def __init__(self):
        self._audio_endpoint = None
        self.current_volume_percent: int = 50
        self.is_muted: bool = False
        self._init_pycaw_audio()

    def _init_pycaw_audio(self) -> None:
        """Khởi tạo giao tiếp trực tiếp với Windows Core Audio API nếu có cài pycaw."""
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._audio_endpoint = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            scalar = float(self._audio_endpoint.GetMasterVolumeLevelScalar())
            self.current_volume_percent = int(round(scalar * 100))
            self.is_muted = bool(self._audio_endpoint.GetMute())
        except Exception:
            self._audio_endpoint = None

    @staticmethod
    def _send_vk_key(vk_code: int) -> None:
        """Gửi phím ảo cấp hệ điều hành Windows qua user32.dll (hoạt động 100% không cần thư viện ngoài)."""
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def set_volume_percent(self, percent: int) -> int:
        """Đặt mức âm lượng chính xác (0% - 100%) dùng cho cử chỉ kéo Pinch (Ngón cái - Ngón trỏ)."""
        target = int(np.clip(percent, 0, 100))
        if self._audio_endpoint is not None:
            try:
                self._audio_endpoint.SetMasterVolumeLevelScalar(target / 100.0, None)
                self.current_volume_percent = target
                return self.current_volume_percent
            except Exception:
                pass

        # Fallback bằng VK_VOLUME_UP / VK_VOLUME_DOWN nếu chưa cài pycaw
        diff = target - self.current_volume_percent
        steps = abs(diff) // 2
        vk = VK_VOLUME_UP if diff > 0 else VK_VOLUME_DOWN
        for _ in range(min(steps, 5)):
            self._send_vk_key(vk)
        self.current_volume_percent = target
        return self.current_volume_percent

    def change_volume_step(self, delta_percent: int = 6) -> str:
        """Tăng hoặc giảm âm lượng theo nấc."""
        if self._audio_endpoint is not None:
            new_vol = int(np.clip(self.current_volume_percent + delta_percent, 0, 100))
            self.set_volume_percent(new_vol)
            return f"Âm lượng: {self.current_volume_percent}%"

        if delta_percent > 0:
            for _ in range(max(1, abs(delta_percent) // 2)):
                self._send_vk_key(VK_VOLUME_UP)
            self.current_volume_percent = min(100, self.current_volume_percent + delta_percent)
            return f"Tăng âm lượng (+{delta_percent}%) -> ~{self.current_volume_percent}%"
        else:
            for _ in range(max(1, abs(delta_percent) // 2)):
                self._send_vk_key(VK_VOLUME_DOWN)
            self.current_volume_percent = max(0, self.current_volume_percent + delta_percent)
            return f"Giảm âm lượng ({delta_percent}%) -> ~{self.current_volume_percent}%"

    def toggle_play_pause(self) -> str:
        """Tạm dừng hoặc phát tiếp Video / Nhạc (YouTube, Spotify, Media Player...)."""
        self._send_vk_key(VK_MEDIA_PLAY_PAUSE)
        return "Play / Pause Media"

    def toggle_mute(self) -> str:
        """Bật / Tắt tiếng hệ thống."""
        if self._audio_endpoint is not None:
            try:
                self.is_muted = not bool(self._audio_endpoint.GetMute())
                self._audio_endpoint.SetMute(int(self.is_muted), None)
                return "Đã tắt tiếng (Muted)" if self.is_muted else "Đã bật tiếng (Unmuted)"
            except Exception:
                pass

        self._send_vk_key(VK_VOLUME_MUTE)
        self.is_muted = not self.is_muted
        return "Mute / Unmute Audio"

    def next_track(self) -> str:
        """Chuyển sang bài hát / video tiếp theo."""
        self._send_vk_key(VK_MEDIA_NEXT_TRACK)
        return "Bài tiếp theo (Next Track)"

    def prev_track(self) -> str:
        """Quay lại bài hát / video trước đó."""
        self._send_vk_key(VK_MEDIA_PREV_TRACK)
        return "Bài trước đó (Previous Track)"

    def take_screenshot(self, frame: Optional[np.ndarray] = None) -> str:
        """Lưu ảnh chụp nhanh vào thư mục screenshots/."""
        os.makedirs("screenshots", exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join("screenshots", f"capture_{ts}.png")
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=filepath)
            return f"Đã chụp màn hình: {filepath}"
        except Exception:
            if frame is not None:
                cv2.imwrite(filepath, frame)
                return f"Đã chụp khung hình Camera: {filepath}"
        return "Chụp màn hình thất bại"

    def execute_gesture_command(self, gesture: str, frame: Optional[np.ndarray] = None) -> Optional[str]:
        """Thực thi lệnh hệ thống tương ứng với cử chỉ đã được xác nhận."""
        if gesture == "OPEN_PALM":
            return self.toggle_play_pause()
        elif gesture == "FIST":
            return self.toggle_mute()
        elif gesture == "THUMBS_UP":
            return self.change_volume_step(+6)
        elif gesture == "THUMBS_DOWN":
            return self.change_volume_step(-6)
        elif gesture == "POINT_RIGHT":
            return self.next_track()
        elif gesture == "POINT_LEFT":
            return self.prev_track()
        elif gesture == "PEACE":
            return self.take_screenshot(frame)
        return None

