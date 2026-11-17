import os
import time
from collections import deque
from typing import List, Optional
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.controllers.air_mouse import DEFAULT_ACTIVE_REGION, AirMouseController
from src.controllers.media_controller import WindowsMediaController
from src.controllers.presentation_controller import PresentationController
from src.controllers.sign_translator import SignLanguageTranslator
from src.ui.laser_overlay import LaserOverlay
from src.ui.telemetry_widget import TelemetryChart
from src.core.camera import ThreadedCamera
from src.core.detector import YoloPoseHandDetector
from src.core.pose_analyzer import HandPoseAnalysis, HandPoseAnalyzer
from src.core.smoother import CommandCooldown, ExponentialMovingAverage, PinchVolumeLock, VotingBuffer
from src.ui.asl_guide_dialog import ASL_GESTURE_GUIDE, ASLGuideDialog


DARK_STYLESHEET = """
QMainWindow {
    background-color: #0f172a;
    color: #f8fafc;
}
QLabel {
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
}
QFrame#Card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #3b82f6;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton#ModeActive {
    background-color: #10b981;
    color: #052e16;
    font-weight: 700;
}
QPushButton#ModeInactive {
    background-color: #334155;
    color: #cbd5e1;
}
QPushButton#DangerBtn {
    background-color: #dc2626;
}
QPushButton#DangerBtn:hover {
    background-color: #ef4444;
}
QLineEdit {
    background-color: #0f172a;
    color: #38bdf8;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px;
    font-size: 18px;
    font-weight: bold;
}
QProgressBar {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 5px;
    text-align: center;
    color: #f8fafc;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #10b981;
    border-radius: 4px;
}
QComboBox {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 5px;
    padding: 5px 10px;
}
QCheckBox {
    color: #e2e8f0;
    font-size: 13px;
    spacing: 8px;
}
"""


class SignAndGestureApp(QMainWindow):
    """
    Cửa sổ ứng dụng chính:
      - Chế độ 1: Nhận diện Ngôn ngữ Ký hiệu ASL (A-Z) + Ghép câu + Phát giọng nói.
      - Chế độ 2: Điều khiển Thiết bị Không chạm (Âm lượng, Play/Pause, Qua bài, Pinch Volume).
      - Sử dụng YOLOv11-Pose (21 điểm khớp xương bàn tay) trên GPU NVIDIA.
    """

    MODE_ASL = 0
    MODE_TOUCHLESS = 1
    MODE_AIR_MOUSE = 2
    MODE_PRESENTATION = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLOv11-Pose: Nhận diện Ngôn ngữ Ký hiệu (A-Z) & Điều khiển Không chạm")
        self.resize(1280, 880)

        # Module chế độ mới: Chuột không chạm & Thuyết trình
        self.air_mouse = AirMouseController()
        self.presenter = PresentationController()
        self.laser_overlay = LaserOverlay()

        # Bộ đệm số liệu đo jitter thực tế (Keypoint 8, trục Y)
        self._raw_hist: deque = deque(maxlen=45)
        self._smooth_hist: deque = deque(maxlen=45)
        self.setStyleSheet(DARK_STYLESHEET)

        # Khởi tạo các module cốt lõi
        self.camera = ThreadedCamera(camera_index=0, width=640, height=480, flip_horizontal=True)
        self.detector = YoloPoseHandDetector()
        self.voting_buffer = VotingBuffer(window_size=14, min_votes=10, min_confidence=0.60)
        self.cooldown_timer = CommandCooldown(required_hold_frames=5)
        self.pinch_ema = ExponentialMovingAverage(alpha=0.30)
        self.pinch_lock = PinchVolumeLock()
        # Sau khi rời Pinch, chặn các lệnh khác 1 giây (tránh cử chỉ chuyển tiếp như THUMBS_UP kích hoạt nhầm)
        self._block_cmds_until = 0.0
        self._slide_banner_until = 0.0
        self._slide_banner_text = ""

        self.media_ctrl = WindowsMediaController()
        self.translator = SignLanguageTranslator()

        self.current_mode = self.MODE_ASL
        self.last_analyses: List[HandPoseAnalysis] = []
        self.last_action_log: str = "Sẵn sàng"

        self._build_ui()

        # Bộ định thời cập nhật khung hình (30 FPS ~ 33ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._process_frame)

        # Tự động bật camera khi khởi động
        self.toggle_camera(start_only=True)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(14)

        # ================= CỘT TRÁI: KHUNG CAMERA & TRẠNG THÁI MODEL =================
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        cam_card = QFrame()
        cam_card.setObjectName("Card")
        cam_layout = QVBoxLayout(cam_card)

        # Thanh tiêu đề Camera + FPS + Model status
        top_bar = QHBoxLayout()
        self.lbl_model_status = QLabel(f"Model: {self.detector.model_loaded_name}")
        self.lbl_model_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_fps = QLabel("FPS: 0.0")
        self.lbl_fps.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_fps.setStyleSheet("color: #38bdf8;")
        top_bar.addWidget(self.lbl_model_status)
        top_bar.addStretch()
        top_bar.addWidget(self.lbl_fps)
        cam_layout.addLayout(top_bar)

        # Khung hiển thị Video
        self.video_label = QLabel("Đang kết nối Webcam...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 400)
        self.video_label.setStyleSheet("background-color: #020617; border-radius: 8px; color: #64748b; font-size: 16px;")
        cam_layout.addWidget(self.video_label, stretch=1)

        # Biểu đồ Telemetry thời gian thực
        self.chart_kpt = TelemetryChart(
            "ĐẦU NGÓN TRỎ (Kpt 8) - TRỤC Y (px)",
            [("Raw", "#94a3b8"), ("1€ Filter", "#ef4444")],
            unit="",
        )
        self.chart_perf = TelemetryChart(
            "HIỆU NĂNG",
            [("FPS", "#38bdf8"), ("Suy luận ms", "#f59e0b")],
            unit="",
        )
        charts_row = QHBoxLayout()
        charts_row.addWidget(self.chart_kpt, stretch=3)
        charts_row.addWidget(self.chart_perf, stretch=2)
        cam_layout.addLayout(charts_row)

        # Thanh nút điều khiển Camera & Nạp Model
        cam_btn_bar = QHBoxLayout()
        self.btn_cam_toggle = QPushButton("Tạm dừng Camera")
        self.btn_cam_toggle.clicked.connect(lambda: self.toggle_camera(start_only=False))

        btn_load_model = QPushButton("Nạp trọng số YOLO (.pt / .onnx)")
        btn_load_model.clicked.connect(self._browse_model_file)

        cam_btn_bar.addWidget(self.btn_cam_toggle)
        cam_btn_bar.addWidget(btn_load_model)
        cam_layout.addLayout(cam_btn_bar)

        left_col.addWidget(cam_card, stretch=1)
        root_layout.addLayout(left_col, stretch=6)

        # ================= CỘT PHẢI: CHUYỂN CHẾ ĐỘ & BẢNG ĐIỀU KHIỂN =================
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # 1. Thẻ chuyển đổi 2 chế độ
        mode_card = QFrame()
        mode_card.setObjectName("Card")
        mode_layout = QVBoxLayout(mode_card)
        lbl_mode_title = QLabel("CHẾ ĐỘ HOẠT ĐỘNG")
        lbl_mode_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_mode_title.setStyleSheet("color: #94a3b8;")
        mode_layout.addWidget(lbl_mode_title)

        mode_btns = QGridLayout()
        mode_defs = [
            (self.MODE_ASL, "1. Ngôn ngữ Ký hiệu (A-Z)"),
            (self.MODE_TOUCHLESS, "2. Điều khiển Media"),
            (self.MODE_AIR_MOUSE, "3. Chuột không chạm"),
            (self.MODE_PRESENTATION, "4. Thuyết trình (Laser)"),
        ]
        self.mode_buttons = {}
        for idx, (mode_id, text) in enumerate(mode_defs):
            btn = QPushButton(text)
            btn.setObjectName("ModeActive" if mode_id == self.MODE_ASL else "ModeInactive")
            btn.clicked.connect(lambda _=False, m=mode_id: self._switch_mode(m))
            mode_btns.addWidget(btn, idx // 2, idx % 2)
            self.mode_buttons[mode_id] = btn
        mode_layout.addLayout(mode_btns)
        right_col.addWidget(mode_card)

        # 2. Thẻ hiển thị Cử chỉ hiện tại & Thanh tiến trình xác nhận
        detect_card = QFrame()
        detect_card.setObjectName("Card")
        detect_layout = QVBoxLayout(detect_card)

        self.lbl_current_symbol = QLabel("Đang chờ bàn tay...")
        self.lbl_current_symbol.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.lbl_current_symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_current_symbol.setStyleSheet("color: #10b981; padding: 6px;")
        detect_layout.addWidget(self.lbl_current_symbol)

        self.progress_hold = QProgressBar()
        self.progress_hold.setRange(0, 100)
        self.progress_hold.setValue(0)
        self.progress_hold.setFormat("Độ ổn định cử chỉ: %p%")
        detect_layout.addWidget(self.progress_hold)

        self.lbl_fingers_debug = QLabel("Trạng thái 5 ngón [Cái, Trỏ, Giữa, Áp, Út]: [-, -, -, -, -]")
        self.lbl_fingers_debug.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fingers_debug.setStyleSheet("color: #94a3b8; font-size: 12px;")
        detect_layout.addWidget(self.lbl_fingers_debug)

        right_col.addWidget(detect_card)

        # 3. Stacked Widget chứa giao diện riêng của từng chế độ
        self.stacked_panels = QStackedWidget()
        self.stacked_panels.addWidget(self._create_asl_panel())
        self.stacked_panels.addWidget(self._create_touchless_panel())
        self.stacked_panels.addWidget(self._create_air_mouse_panel())
        self.stacked_panels.addWidget(self._create_presentation_panel())
        right_col.addWidget(self.stacked_panels, stretch=1)

        root_layout.addLayout(right_col, stretch=5)

    def _create_asl_panel(self) -> QWidget:
        """Tạo giao diện cho Chế độ 1: Ghép chữ cái Ngôn ngữ Ký hiệu (A-Z) & Phát giọng nói."""
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        title = QLabel("SOẠN THẢO NGÔN NGỮ KÝ HIỆU (ASL A-Z)")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        self.txt_sentence = QLineEdit()
        self.txt_sentence.setPlaceholderText("Các chữ cái A-Z nhận diện được sẽ ghép tại đây...")
        self.txt_sentence.textChanged.connect(self._on_sentence_edited)
        layout.addWidget(self.txt_sentence)

        # Hàng nút gợi ý từ thông minh (Autocomplete)
        sugg_layout = QHBoxLayout()
        sugg_label = QLabel("Gợi ý từ:")
        sugg_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        sugg_layout.addWidget(sugg_label)

        self.sugg_buttons: List[QPushButton] = []
        for _ in range(3):
            btn = QPushButton("-")
            btn.setStyleSheet("background-color: #334155; font-size: 12px; padding: 5px 10px;")
            btn.clicked.connect(self._on_suggestion_clicked)
            sugg_layout.addWidget(btn)
            self.sugg_buttons.append(btn)
        layout.addLayout(sugg_layout)
        self._refresh_suggestion_buttons()

        # Hàng nút thao tác văn bản & giọng nói
        action_grid = QGridLayout()
        btn_speak = QPushButton("Đọc to câu (Speak TTS)")
        btn_speak.setStyleSheet("background-color: #059669; font-size: 14px;")
        btn_speak.clicked.connect(lambda: self.translator.speak_async(self.txt_sentence.text()))

        btn_space = QPushButton("Dấu cách (Space)")
        btn_space.clicked.connect(self._action_space)

        btn_backspace = QPushButton("Xóa 1 chữ (Backspace)")
        btn_backspace.clicked.connect(self._action_backspace)

        btn_clear = QPushButton("Xóa hết (Clear)")
        btn_clear.setObjectName("DangerBtn")
        btn_clear.clicked.connect(self._action_clear)

        action_grid.addWidget(btn_speak, 0, 0, 1, 2)
        action_grid.addWidget(btn_space, 1, 0)
        action_grid.addWidget(btn_backspace, 1, 1)
        action_grid.addWidget(btn_clear, 2, 0, 1, 2)
        layout.addLayout(action_grid)

        # Nút mở cửa sổ Hướng dẫn trực quan 21 khớp xương cho từng chữ cái A-Z
        btn_open_guide = QPushButton("📖 Mở Bảng Hướng Dẫn Cử Chỉ A-Z (Có hình minh họa 21 khớp)")
        btn_open_guide.setStyleSheet(
            "background-color: #7c3aed; color: #ffffff; font-size: 13px; padding: 8px;"
        )
        btn_open_guide.clicked.connect(self._open_asl_guide_dialog)
        layout.addWidget(btn_open_guide)

        # Khung tra cứu nhanh cử chỉ chữ cái A-Z cuộn trực tiếp trên màn hình chính
        guide_scroll = QScrollArea()
        guide_scroll.setWidgetResizable(True)
        guide_scroll.setStyleSheet(
            "QScrollArea { background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; }"
        )
        guide_inner = QWidget()
        guide_inner.setStyleSheet("background-color: #0f172a;")
        guide_inner_layout = QVBoxLayout(guide_inner)
        guide_inner_layout.setContentsMargins(8, 6, 8, 6)
        guide_inner_layout.setSpacing(4)

        lbl_quick_header = QLabel(
            "<b style='color:#f59e0b;'>BẢNG TRA NHANH CỬ CHỈ [Cái, Trỏ, Giữa, Áp, Út] (1=Mở, 0=Gập):</b>"
        )
        lbl_quick_header.setStyleSheet("font-size: 11px;")
        guide_inner_layout.addWidget(lbl_quick_header)

        for k, meta in ASL_GESTURE_GUIDE.items():
            item_lbl = QLabel(
                f"<b style='color:#38bdf8;'>{k}</b> "
                f"<span style='color:#10b981; font-family:Consolas;'>{meta['fingers']}</span>: "
                f"<span style='color:#cbd5e1;'>{meta['short']}</span>"
            )
            item_lbl.setWordWrap(True)
            item_lbl.setStyleSheet("font-size: 11px; padding: 2px 0px; border-bottom: 1px solid #1e293b;")
            guide_inner_layout.addWidget(item_lbl)

        guide_scroll.setWidget(guide_inner)
        layout.addWidget(guide_scroll, stretch=1)

        # Khung dạy nhanh mẫu 21-keypoints cho chữ cái bất kỳ (Quick Calibration)
        calib_box = QFrame()
        calib_box.setStyleSheet("background-color: #0f172a; border-radius: 8px; padding: 6px;")
        calib_layout = QVBoxLayout(calib_box)
        lbl_calib = QLabel("Cá nhân hóa nhanh 21-Keypoints cho tay của bạn:")
        lbl_calib.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: bold;")
        calib_layout.addWidget(lbl_calib)

        calib_row = QHBoxLayout()
        self.combo_calib_letter = QComboBox()
        for ch in [chr(c) for c in range(ord("A"), ord("Z") + 1)] + ["SPACE", "DEL"]:
            self.combo_calib_letter.addItem(ch)
        self.combo_calib_letter.currentTextChanged.connect(self._on_calib_letter_changed)
        btn_save_kpt = QPushButton("Lưu mẫu tư thế tay hiện tại")
        btn_save_kpt.clicked.connect(self._save_current_keypoint_sample)
        calib_row.addWidget(self.combo_calib_letter)
        calib_row.addWidget(btn_save_kpt, stretch=1)
        calib_layout.addLayout(calib_row)

        self.lbl_calib_hint = QLabel()
        self.lbl_calib_hint.setWordWrap(True)
        self.lbl_calib_hint.setStyleSheet("color: #38bdf8; font-size: 11px; padding-top: 2px;")
        calib_layout.addWidget(self.lbl_calib_hint)
        self._on_calib_letter_changed("A")

        layout.addWidget(calib_box)
        return card

    def _create_touchless_panel(self) -> QWidget:
        """Tạo giao diện cho Chế độ 2: Điều khiển Thiết bị Không chạm (Touchless Control)."""
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        title = QLabel("ĐIỀU KHIỂN WINDOWS KHÔNG CHẠM (TOUCHLESS)")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #f59e0b;")
        layout.addWidget(title)

        # Thanh hiển thị âm lượng hệ thống hiện tại
        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Âm lượng Windows:"))
        self.progress_volume = QProgressBar()
        self.progress_volume.setRange(0, 100)
        self.progress_volume.setValue(self.media_ctrl.current_volume_percent)
        self.progress_volume.setFormat("%p%")
        vol_row.addWidget(self.progress_volume, stretch=1)
        layout.addLayout(vol_row)

        # Checkbox bật/tắt kéo âm lượng bằng khoảng cách Ngón cái - Ngón trỏ (Pinch)
        self.chk_pinch_volume = QCheckBox(
            "Bật Pinch Volume (Giơ Cái + Trỏ [1,1,0,0,0] kéo khoảng cách để chỉnh âm lượng 0-100%)"
        )
        self.chk_pinch_volume.setChecked(False)
        layout.addWidget(self.chk_pinch_volume)

        # Trạng thái lệnh vừa thực thi
        self.lbl_last_command = QLabel("Lệnh gần nhất: Chưa có")
        self.lbl_last_command.setStyleSheet(
            "background-color: #0f172a; color: #38bdf8; padding: 8px; border-radius: 6px; font-weight: bold;"
        )
        layout.addWidget(self.lbl_last_command)

        # Bảng hướng dẫn các cử chỉ điều khiển
        guide_text = (
            "BẢNG CỬ CHỈ ĐIỀU KHIỂN:\n"
            "• Xòe 5 ngón (OPEN_PALM)   : Play / Pause Video & Nhạc\n"
            "• Nắm đấm (FIST)           : Bật / Tắt tiếng (Mute / Unmute)\n"
            "• Giơ ngón cái lên (UP)    : Tăng âm lượng (+6%)\n"
            "• Chúc ngón cái xuống      : Giảm âm lượng (-6%)\n"
            "• Chỉ trỏ sang Phải / Trái : Qua bài (Next) / Lùi bài (Prev)\n"
            "• Giơ 2 ngón chữ V (PEACE) : Chụp ảnh màn hình (Screenshot)\n\n"
            "PINCH VOLUME: kéo Cái-Trỏ để chỉnh, GIỮ YÊN ~0,7s để KHÓA.\n"
            "Muốn chỉnh lại: hạ tay hoặc đổi tư thế rồi làm lại."
        )
        lbl_guide = QLabel(guide_text)
        lbl_guide.setStyleSheet(
            "background-color: #0f172a; color: #cbd5e1; padding: 10px; border-radius: 8px; font-size: 12px; line-height: 1.4;"
        )
        layout.addWidget(lbl_guide)
        layout.addStretch()
        return card

    def _create_air_mouse_panel(self) -> QWidget:
        """Chế độ 3: Điều khiển chuột Windows bằng ngón trỏ."""
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        title = QLabel("CHUỘT KHÔNG CHẠM (AIR MOUSE)")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #a78bfa;")
        layout.addWidget(title)

        self.chk_air_mouse = QCheckBox("Kích hoạt điều khiển con trỏ chuột (bỏ chọn để tạm dừng)")
        self.chk_air_mouse.setChecked(False)
        self.chk_air_mouse.toggled.connect(lambda on: None if on else self.air_mouse.release())
        layout.addWidget(self.chk_air_mouse)

        self.lbl_mouse_state = QLabel("Trạng thái: Chưa kích hoạt")
        self.lbl_mouse_state.setStyleSheet(
            "background-color: #0f172a; color: #a78bfa; padding: 8px; border-radius: 6px; font-weight: bold;"
        )
        layout.addWidget(self.lbl_mouse_state)

        pinch_row = QHBoxLayout()
        pinch_row.addWidget(QLabel("Chụm Cái-Trỏ:"))
        self.progress_pinch_left = QProgressBar()
        self.progress_pinch_left.setRange(0, 100)
        self.progress_pinch_left.setFormat("%p%")
        pinch_row.addWidget(self.progress_pinch_left, stretch=1)
        layout.addLayout(pinch_row)

        guide = QLabel(
            "HƯỚNG DẪN:\n"
            "• Di chuyển đầu ngón trỏ trong khung tím : Di chuyển con trỏ\n"
            "• Chụm Cái + Trỏ nhanh rồi nhả         : Nhấp chuột trái\n"
            "• Chụm Cái + Trỏ và giữ > 0,35 giây    : Kéo thả (Drag)\n"
            "• Chụm Cái + Giữa (Trỏ vẫn mở)        : Nhấp chuột phải\n"
            "• Nắm tay lại                           : Tạm dừng con trỏ để\n"
            "                                          đặt lại vị trí tay\n\n"
            f"Màn hình: {self.air_mouse.screen_w} x {self.air_mouse.screen_h}"
        )
        guide.setStyleSheet(
            "background-color: #0f172a; color: #cbd5e1; padding: 10px; border-radius: 8px; font-size: 12px;"
        )
        layout.addWidget(guide)
        layout.addStretch()
        return card

    def _create_presentation_panel(self) -> QWidget:
        """Chế độ 4: Tia laser ảo + lật slide bằng vẫy tay."""
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        title = QLabel("THUYẾT TRÌNH THÔNG MINH (LASER & SLIDE)")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #f87171;")
        layout.addWidget(title)

        self.chk_laser = QCheckBox("Hiển thị tia laser đỏ trên toàn màn hình")
        self.chk_laser.setChecked(True)
        layout.addWidget(self.chk_laser)

        self.chk_swipe = QCheckBox("Cho phép lật slide bằng vẫy tay")
        self.chk_swipe.setChecked(True)
        layout.addWidget(self.chk_swipe)

        self.lbl_present_state = QLabel("Trạng thái: Chờ cử chỉ")
        self.lbl_present_state.setStyleSheet(
            "background-color: #0f172a; color: #f87171; padding: 8px; border-radius: 6px; font-weight: bold;"
        )
        layout.addWidget(self.lbl_present_state)

        self.lbl_slide_event = QLabel("Lệnh slide gần nhất: Chưa có")
        self.lbl_slide_event.setStyleSheet(
            "background-color: #0f172a; color: #38bdf8; padding: 8px; border-radius: 6px; font-weight: bold;"
        )
        layout.addWidget(self.lbl_slide_event)

        guide = QLabel(
            "HƯỚNG DẪN:\n"
            "• Chỉ giơ ngón trỏ       : Hiện tia laser đỏ theo ngón tay\n"
            "• Xòe tay, vẫy sang TRÁI : Slide tiếp theo (phím →)\n"
            "• Xòe tay, vẫy sang PHẢI : Slide trước (phím ←)\n\n"
            "Mẹo: mở PowerPoint ở chế độ trình chiếu (F5) rồi\n"
            "bấm vào cửa sổ trình chiếu để nó nhận phím."
        )
        guide.setStyleSheet(
            "background-color: #0f172a; color: #cbd5e1; padding: 10px; border-radius: 8px; font-size: 12px;"
        )
        layout.addWidget(guide)
        layout.addStretch()
        return card

    def _switch_mode(self, mode: int) -> None:
        # Dọn trạng thái của chế độ cũ
        self.air_mouse.release()
        self.presenter.reset()
        self.pinch_lock.reset()
        self.pinch_ema.reset()
        self.laser_overlay.set_point(None)
        if mode == self.MODE_PRESENTATION:
            self.laser_overlay.show()
        else:
            self.laser_overlay.hide()

        self.current_mode = mode
        self.voting_buffer.reset()
        self.progress_hold.setValue(0)
        if mode == self.MODE_TOUCHLESS:
            self.progress_volume.setValue(self.media_ctrl.refresh_volume())
        for mode_id, btn in self.mode_buttons.items():
            btn.setObjectName("ModeActive" if mode_id == mode else "ModeInactive")
        self.stacked_panels.setCurrentIndex(mode)
        self.setStyleSheet(DARK_STYLESHEET)

    def toggle_camera(self, start_only: bool = False) -> None:
        if not self.camera.running:
            ok = self.camera.start()
            if ok:
                self.timer.start(30)
                self.btn_cam_toggle.setText("Tạm dừng Camera")
            else:
                self.video_label.setText("Không tìm thấy Webcam! Hãy kiểm tra kết nối Camera.")
        elif not start_only:
            self.timer.stop()
            self.camera.stop()
            self.btn_cam_toggle.setText("Bật lại Camera")
            self.video_label.setText("Camera đang tạm dừng.")

    def _browse_model_file(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file trọng số YOLOv11-Pose (.pt / .onnx)",
            os.getcwd(),
            "YOLO Weights (*.pt *.onnx)",
        )
        if filepath:
            ok = self.detector.load_model(filepath)
            self.lbl_model_status.setText(f"Model: {self.detector.model_loaded_name}")
            if not ok:
                QMessageBox.warning(self, "Lỗi nạp model", f"Không thể nạp file: {filepath}")

    def _process_frame(self) -> None:
        ret, frame, fps = self.camera.read()
        if not ret or frame is None:
            return

        self.lbl_fps.setText(f"FPS: {fps:.1f}")
        pinch_enabled = (self.current_mode == self.MODE_TOUCHLESS) and self.chk_pinch_volume.isChecked()

        t_start = time.perf_counter()
        annotated, analyses = self.detector.detect(frame, pinch_mode_enabled=pinch_enabled)
        infer_ms = (time.perf_counter() - t_start) * 1000.0
        self.last_analyses = analyses

        # Cập nhật biểu đồ hiệu năng (FPS & Latency ms)
        self.chart_perf.push([fps, infer_ms])
        self.chart_perf.set_footer(f"FPS: {fps:.1f}  |  Độ trễ AI: {infer_ms:.1f} ms")

        h_f, w_f = annotated.shape[:2]

        # Nếu ở chế độ Air Mouse hoặc Thuyết trình, vẽ khung vùng hoạt động chuẩn hóa lên HUD
        if self.current_mode in (self.MODE_AIR_MOUSE, self.MODE_PRESENTATION):
            rx1, ry1, rx2, ry2 = DEFAULT_ACTIVE_REGION
            p1 = (int(rx1 * w_f), int(ry1 * h_f))
            p2 = (int(rx2 * w_f), int(ry2 * h_f))
            box_color = (250, 139, 167) if self.current_mode == self.MODE_AIR_MOUSE else (113, 113, 248)
            cv2.rectangle(annotated, p1, p2, box_color, 1, cv2.LINE_AA)

        if analyses:
            primary = analyses[0]
            self.lbl_fingers_debug.setText(
                f"Trạng thái 5 ngón [Cái, Trỏ, Giữa, Áp, Út]: {primary.fingers_up}"
            )

            # Cập nhật biểu đồ sóng Telemetry (Raw vs 1€ Filter trên đầu ngón trỏ Kpt 8)
            smooth_y = float(primary.keypoints[8][1])
            raw_y = (
                float(self.detector.last_raw_kpts[8][1])
                if self.detector.last_raw_kpts is not None
                else smooth_y
            )
            self._raw_hist.append(raw_y)
            self._smooth_hist.append(smooth_y)
            self.chart_kpt.push([raw_y, smooth_y])
            if len(self._raw_hist) >= 6:
                raw_jit = float(np.std(np.diff(np.array(self._raw_hist))))
                smt_jit = float(np.std(np.diff(np.array(self._smooth_hist))))
                self.chart_kpt.set_footer(
                    f"Rung ΔRaw: {raw_jit:.2f}px  →  Δ1€: {smt_jit:.2f}px"
                )

            if self.current_mode == self.MODE_ASL:
                committed, progress, candidate = self.voting_buffer.update(
                    primary.asl_label, primary.asl_confidence
                )
                disp = candidate or primary.asl_label
                self.lbl_current_symbol.setText(f"Ký hiệu: {disp} ({primary.asl_confidence * 100:.0f}%)")
                self.progress_hold.setValue(int(progress * 100))

                if committed:
                    new_text = self.translator.append_symbol(committed)
                    self.txt_sentence.setText(new_text)
                    self._refresh_suggestion_buttons()

            elif self.current_mode == self.MODE_TOUCHLESS:
                # Chế độ 2: Điều khiển Không chạm (Touchless Media Control)
                gesture = primary.control_gesture
                if gesture == "PINCH_VOLUME" and primary.pinch_ratio is not None:
                    pre_ratio = None
                    if not self.pinch_lock.active and not self.pinch_lock.locked:
                        pre_ratio = self.media_ctrl.refresh_volume() / 100.0
                    smooth_ratio = self.pinch_ema.update(primary.pinch_ratio)
                    apply_val, lock_state, lock_prog = self.pinch_lock.update(
                        smooth_ratio, pre_pinch_ratio=pre_ratio
                    )
                    if apply_val is not None:
                        self.media_ctrl.set_volume_percent(int(round(apply_val * 100)))
                    vol_pct = self.media_ctrl.current_volume_percent
                    self.progress_volume.setValue(vol_pct)
                    self.cooldown_timer.check_trigger(None)
                    self._block_cmds_until = time.perf_counter() + 1.0
                    if lock_state == "LOCKED":
                        self.lbl_current_symbol.setText(f"🔒 ĐÃ KHÓA: {vol_pct}%")
                        self.progress_hold.setValue(100)
                        self.lbl_last_command.setText(
                            f"Đã chốt âm lượng {vol_pct}%. Hạ tay/đổi tư thế rồi làm lại để chỉnh tiếp."
                        )
                        cv2.putText(
                            annotated,
                            f"LOCKED: {vol_pct}%",
                            (16, 36),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (80, 255, 140),
                            2,
                            cv2.LINE_AA,
                        )
                    elif lock_state == "ARMING":
                        self.lbl_current_symbol.setText(f"PINCH: Đang kích hoạt...")
                        self.progress_hold.setValue(0)
                    else:
                        self.lbl_current_symbol.setText(f"PINCH VOLUME: {vol_pct}%")
                        self.progress_hold.setValue(int(lock_prog * 100))
                        self.lbl_last_command.setText(
                            f"Đang chỉnh {vol_pct}% - giữ yên tay để khóa"
                        )
                else:
                    self.pinch_ema.reset()
                    self._handle_pinch_exit()
                    now = time.perf_counter()
                    if now < self._block_cmds_until:
                        # Đang trong thời gian chặn sau Pinch: không kích hoạt lệnh nào
                        self.cooldown_timer.check_trigger(None)
                        self.lbl_current_symbol.setText(f"Cử chỉ: {gesture} (tạm chặn)")
                        self.progress_hold.setValue(0)
                    else:
                        triggered, progress = self.cooldown_timer.check_trigger(gesture)
                        self.lbl_current_symbol.setText(f"Cử chỉ: {gesture}")
                        self.progress_hold.setValue(int(progress * 100))
                        if triggered:
                            action_msg = self.media_ctrl.execute_gesture_command(gesture, frame=frame)
                            if action_msg:
                                self.lbl_last_command.setText(f"Lệnh gần nhất: {action_msg}")
                                self.progress_volume.setValue(self.media_ctrl.current_volume_percent)

            elif self.current_mode == self.MODE_AIR_MOUSE:
                # Chế độ 3: Điều khiển Chuột Không Chạm (Air Mouse & Pinch Click)
                if self.chk_air_mouse.isChecked():
                    info = self.air_mouse.update(primary.keypoints, w_f, h_f, fingers=primary.fingers_up)
                    state = str(info["state"])
                    ev = str(info["event"])
                    r_left = float(info["r_left"])
                    closeness = int(np.clip((1.0 - r_left / 0.85) * 100, 0, 100))
                    self.progress_pinch_left.setValue(closeness)
                    self.progress_hold.setValue(closeness)
                    self.lbl_current_symbol.setText(f"AIR MOUSE: {state}")
                    if ev:
                        self.lbl_mouse_state.setText(f"Sự kiện: {ev} ({state})")
                    else:
                        self.lbl_mouse_state.setText(f"Trạng thái: {state}")

                    # Vẽ tâm ngắm tại đầu ngón trỏ (Keypoint 8)
                    ix, iy = int(primary.keypoints[8][0]), int(primary.keypoints[8][1])
                    c_ring = (0, 255, 180) if state in ("LEFT_DOWN", "DRAG") else (255, 180, 0)
                    cv2.circle(annotated, (ix, iy), 12, c_ring, 2, cv2.LINE_AA)
                else:
                    self.air_mouse.release()
                    self.lbl_current_symbol.setText("Air Mouse: Đang tắt")
                    self.progress_hold.setValue(0)

            elif self.current_mode == self.MODE_PRESENTATION:
                # Chế độ 4: Thuyết trình Thông minh (Laser đỏ & Lật Slide vẫy tay)
                pres = self.presenter.update(
                    primary.keypoints,
                    primary.fingers_up,
                    w_f,
                    h_f,
                    enable_swipe=self.chk_swipe.isChecked(),
                )
                p_state = str(pres["state"])
                laser_pt = pres["laser"]
                slide_ev = pres["event"]
                swipe_prog = float(pres.get("progress", 0.0))

                if slide_ev:
                    self._slide_banner_text = str(slide_ev)
                    self._slide_banner_until = time.perf_counter() + 1.0
                    self.lbl_slide_event.setText(f"Lệnh slide gần nhất: {slide_ev}")
                    self.laser_overlay.show_banner(str(slide_ev))

                if self.chk_laser.isChecked() and laser_pt is not None:
                    self.laser_overlay.set_point(laser_pt)
                    ix, iy = int(primary.keypoints[8][0]), int(primary.keypoints[8][1])
                    cv2.circle(annotated, (ix, iy), 14, (40, 40, 255), 3, cv2.LINE_AA)
                    cv2.circle(annotated, (ix, iy), 5, (255, 255, 255), -1, cv2.LINE_AA)
                    self.lbl_current_symbol.setText("LASER POINTER: BẬT")
                    self.lbl_present_state.setText("Trạng thái: Đang chiếu tia Laser đỏ")
                    self.progress_hold.setValue(100)
                else:
                    self.laser_overlay.set_point(None)
                    if time.perf_counter() < self._slide_banner_until:
                        self.lbl_current_symbol.setText(self._slide_banner_text)
                        self.lbl_present_state.setText(f"Đã thực thi: {self._slide_banner_text}")
                        self.progress_hold.setValue(100)
                        hud_txt = "NEXT SLIDE >>" if "tiếp" in self._slide_banner_text else "<< PREV SLIDE"
                        cv2.putText(
                            annotated,
                            hud_txt,
                            (16, 36),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.85,
                            (56, 189, 248),
                            2,
                            cv2.LINE_AA,
                        )
                    elif p_state == "SWIPE_READY":
                        self.lbl_current_symbol.setText("THUYẾT TRÌNH: SẴN SÀNG VẪY")
                        self.lbl_present_state.setText("Trạng thái: Đang xòe tay - vẫy Trái/Phải để chuyển slide")
                        self.progress_hold.setValue(int(swipe_prog * 100))
                    else:
                        self.lbl_current_symbol.setText(f"THUYẾT TRÌNH: {p_state}")
                        self.lbl_present_state.setText(f"Trạng thái: {p_state}")
                        self.progress_hold.setValue(0)
        else:
            self.voting_buffer.update(None, 0.0)
            self.cooldown_timer.check_trigger(None)
            self.pinch_ema.reset()
            self._handle_pinch_exit()
            self.air_mouse.release()
            self.presenter.on_no_hand()
            self.laser_overlay.set_point(None)
            self.chart_kpt.push([None, None])
            if self.current_mode == self.MODE_PRESENTATION and time.perf_counter() < self._slide_banner_until:
                self.lbl_current_symbol.setText(self._slide_banner_text)
                self.lbl_present_state.setText(f"Đã thực thi: {self._slide_banner_text}")
                self.progress_hold.setValue(100)
            else:
                self.lbl_current_symbol.setText("Đang chờ bàn tay...")
                self.progress_hold.setValue(0)
                self.lbl_present_state.setText("Trạng thái: Đang chờ bàn tay...")
            self.progress_pinch_left.setValue(0)
            self.lbl_mouse_state.setText("Trạng thái: Đang chờ bàn tay (Con trỏ nghỉ)")
            self.lbl_fingers_debug.setText("Trạng thái 5 ngón [Cái, Trỏ, Giữa, Áp, Út]: [-, -, -, -, -]")

        # Chuyển frame BGR sang QPixmap hiển thị lên giao diện
        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(pixmap)

    def _handle_pinch_exit(self) -> None:
        """Khi rời tư thế Pinch: hoàn tác phần âm lượng bị vọt lên do động tác rút tay."""
        rollback = self.pinch_lock.on_not_pinch()
        if rollback is not None:
            vol_pct = self.media_ctrl.set_volume_percent(int(round(rollback * 100)))
            self.progress_volume.setValue(vol_pct)
            self.lbl_last_command.setText(f"Lệnh gần nhất: Giữ âm lượng {vol_pct}% (đã bỏ qua động tác rút tay)")

    def _on_sentence_edited(self, text: str) -> None:
        self.translator.text_buffer = text
        self._refresh_suggestion_buttons()

    def _refresh_suggestion_buttons(self) -> None:
        suggestions = self.translator.get_word_suggestions(max_results=3)
        for idx, btn in enumerate(self.sugg_buttons):
            if idx < len(suggestions):
                btn.setText(suggestions[idx])
                btn.setEnabled(True)
            else:
                btn.setText("-")
                btn.setEnabled(False)

    def _on_suggestion_clicked(self) -> None:
        sender = self.sender()
        if isinstance(sender, QPushButton) and sender.text() != "-":
            updated = self.translator.apply_suggestion(sender.text())
            self.txt_sentence.setText(updated)
            self._refresh_suggestion_buttons()

    def _action_space(self) -> None:
        self.txt_sentence.setText(self.translator.add_space())
        self._refresh_suggestion_buttons()

    def _action_backspace(self) -> None:
        self.txt_sentence.setText(self.translator.backspace())
        self._refresh_suggestion_buttons()

    def _action_clear(self) -> None:
        self.translator.clear()
        self.txt_sentence.clear()
        self.voting_buffer.reset()
        self._refresh_suggestion_buttons()

    def _open_asl_guide_dialog(self) -> None:
        """Mở cửa sổ tra cứu trực quan toàn bộ Bảng chữ cái A-Z kèm sơ đồ 21 khớp."""
        dlg = ASLGuideDialog(self)
        dlg.exec()

    def _on_calib_letter_changed(self, letter: str) -> None:
        """Cập nhật dòng gợi ý cách đặt ngón tay khi người dùng chọn chữ cái trong hộp chọn."""
        meta = ASL_GESTURE_GUIDE.get(letter)
        if meta and hasattr(self, "lbl_calib_hint"):
            self.lbl_calib_hint.setText(f"Cách làm '{letter}' {meta['fingers']}: {meta['short']}")

    def _save_current_keypoint_sample(self) -> None:
        """Lưu nhanh mẫu 21-keypoints hiện tại từ khung hình camera vào models/asl_keypoints_db.npz."""
        if not self.last_analyses:
            QMessageBox.information(
                self,
                "Chưa phát hiện bàn tay",
                "Hãy đưa bàn tay vào khung hình camera (hiển thị 21 điểm khớp) trước khi bấm Lưu mẫu!",
            )
            return

        label = self.combo_calib_letter.currentText()
        kpts = self.last_analyses[0].keypoints
        feat = HandPoseAnalyzer.extract_normalized_features(kpts)

        os.makedirs("models", exist_ok=True)
        db_path = self.detector.analyzer.custom_keypoints_db_path

        if self.detector.analyzer.sample_features is not None and len(self.detector.analyzer.sample_features) > 0:
            new_feats = np.vstack([self.detector.analyzer.sample_features, feat])
            new_labels = np.append(self.detector.analyzer.sample_labels, label)
        else:
            new_feats = np.array([feat], dtype=np.float32)
            new_labels = np.array([label])

        np.savez_compressed(db_path, features=new_feats, labels=new_labels)
        self.detector.analyzer.reload_custom_samples()
        count = int(np.sum(new_labels == label))
        QMessageBox.information(
            self,
            "Đã lưu mẫu 21-Keypoints",
            f"Đã lưu thành công tư thế 21 điểm khớp cho ký hiệu '{label}' (Tổng số mẫu '{label}': {count}).",
        )

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.camera.stop()
        self.air_mouse.release()
        self.laser_overlay.close()
        event.accept()

