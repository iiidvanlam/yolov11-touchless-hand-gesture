import importlib.util
import os
import threading
import time
from collections import deque
from typing import Callable, List, Optional
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QImage, QKeySequence, QPalette, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
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
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.controllers.air_mouse import DEFAULT_ACTIVE_REGION, AirMouseController
from src.controllers.media_controller import WindowsMediaController
from src.controllers.presentation_controller import PresentationController
from src.controllers.sign_translator import SignLanguageTranslator
from src.ui import theme
from src.ui.theme import T
from src.ui.laser_overlay import LaserOverlay
from src.ui.telemetry_widget import TelemetryChart
from src.core.camera import ThreadedCamera
from src.core.detector import YoloPoseHandDetector
from src.core.paths import PROJECT_ROOT, resolve_project_path
from src.core.pose_analyzer import HandPoseAnalysis, HandPoseAnalyzer
from src.core.smoother import CommandCooldown, ExponentialMovingAverage, PinchVolumeLock, VotingBuffer
from src.ui.asl_guide_dialog import ASL_GESTURE_GUIDE, ASLGuideDialog


class _InferenceWorker(threading.Thread):
    """Luồng chạy ngầm suy luận AI (YOLOv11-Pose + MediaPipe 3D), tách khỏi luồng giao diện Qt."""

    def __init__(
        self,
        camera: ThreadedCamera,
        detector: YoloPoseHandDetector,
        get_pinch_enabled: Callable[[], bool],
    ):
        super().__init__(daemon=True)
        self.camera = camera
        self.detector = detector
        self._get_pinch_enabled = get_pinch_enabled
        self.running = False
        self._lock = threading.Lock()
        self._last_cam_id = 0
        self._seq = 0
        self._latest_packet = None

    def run(self) -> None:
        self.running = True
        ai_fps = 0.0
        last_done = time.perf_counter()
        while self.running:
            ok, frame, cam_fps, cam_id = self.camera.read_if_newer(self._last_cam_id)
            if not ok or frame is None:
                time.sleep(0.002)
                continue
            self._last_cam_id = cam_id

            t0 = time.perf_counter()
            annotated, analyses = self.detector.detect(
                frame, pinch_mode_enabled=self._get_pinch_enabled()
            )
            now = time.perf_counter()
            infer_ms = (now - t0) * 1000.0
            dt = now - last_done
            last_done = now
            if dt > 0:
                inst = 1.0 / dt
                ai_fps = 0.85 * ai_fps + 0.15 * inst if ai_fps > 0 else inst

            raw_kpts = (
                self.detector.last_raw_kpts.copy()
                if self.detector.last_raw_kpts is not None
                else None
            )
            with self._lock:
                self._seq += 1
                self._latest_packet = (
                    self._seq,
                    frame,
                    annotated,
                    analyses,
                    raw_kpts,
                    cam_fps,
                    ai_fps,
                    infer_ms,
                )

    def pop_latest(self, last_seq: int):
        with self._lock:
            if self._latest_packet is None or self._latest_packet[0] == last_seq:
                return None
            return self._latest_packet

    def stop(self) -> None:
        self.running = False
        if self.is_alive():
            self.join(timeout=1.5)


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
        self.setMinimumSize(1100, 700)
        self.resize(1360, 860)

        # Module chế độ mới: Chuột không chạm & Thuyết trình
        self.air_mouse = AirMouseController()
        self.presenter = PresentationController()
        self.laser_overlay = LaserOverlay()

        # Bộ đệm số liệu đo jitter thực tế (Keypoint 8, trục Y)
        self._raw_hist: deque = deque(maxlen=45)
        self._smooth_hist: deque = deque(maxlen=45)
        self.setStyleSheet(theme.build_stylesheet())

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
        self._ai_worker: Optional[_InferenceWorker] = None
        self._last_ai_seq: int = 0

        self._build_ui()

        # Bộ định thời làm mới giao diện 60 Hz (không chặn bởi suy luận AI)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._process_frame)

        # Tự động bật camera khi khởi động
        self.toggle_camera(start_only=True)

    # ------------------------------------------------------------------
    # Xây dựng giao diện (theo design system trong src/ui/theme.py)
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("Root")
        central.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QSplitter(Qt.Orientation.Horizontal)
        body.setChildrenCollapsible(False)
        body.setHandleWidth(T.SP_3)
        body.addWidget(self._build_camera_column())
        body.addWidget(self._build_control_column())
        body.setStretchFactor(0, 6)
        body.setStretchFactor(1, 5)
        body.setSizes([780, 620])

        wrap = QWidget()
        wrap_layout = QVBoxLayout(wrap)
        wrap_layout.setContentsMargins(T.SP_4, T.SP_4, T.SP_4, T.SP_4)
        wrap_layout.addWidget(body)
        root.addWidget(wrap, stretch=1)

        self._install_shortcuts()
        central.setFocus()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("Header")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(T.SP_4, 10, T.SP_4, 10)
        lay.setSpacing(T.SP_2)

        brand = QVBoxLayout()
        brand.setSpacing(0)
        brand.addWidget(theme.label("Nhận diện cử chỉ tay", role="title"))
        brand.addWidget(theme.label("YOLOv11-Pose · 21 khớp xương thời gian thực", role="subtitle"))
        lay.addLayout(brand)
        lay.addStretch()

        self.lbl_cam_status = theme.pill("■ Camera: kết nối…", "warn")
        self.lbl_cam_status.setAccessibleName("Trạng thái camera")

        model_tone = "neutral" if self.detector.model is not None else "warn"
        self.lbl_model_status = theme.pill(f"Model: {self.detector.model_loaded_name}", model_tone)
        self.lbl_model_status.setAccessibleName("Mô hình đang dùng")
        self.lbl_model_status.setToolTip("Trọng số YOLOv11-Pose và thiết bị đang dùng")

        self.lbl_fps = theme.pill("Cam 0.0 · AI 0.0 FPS", "info")
        self.lbl_fps.setAccessibleName("Tốc độ khung hình")
        self.lbl_fps.setToolTip("Cam: tốc độ camera · AI: tốc độ suy luận")

        lay.addWidget(self.lbl_cam_status)
        lay.addWidget(self.lbl_model_status)
        lay.addWidget(self.lbl_fps)
        return header

    def _build_camera_column(self) -> QWidget:
        cam_card, cam_layout = theme.card(spacing=T.SP_3)

        cam_layout.addWidget(theme.caption("Camera & HUD khung xương 21 điểm"))

        self.video_label = theme.label(
            "Đang kết nối webcam…\nHãy đảm bảo camera không bị ứng dụng khác chiếm dụng.",
            role="viewport",
        )
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(480, 300)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.video_label.setAccessibleName("Khung hình camera trực tiếp")
        cam_layout.addWidget(self.video_label, stretch=1)

        # Biểu đồ Telemetry thời gian thực
        self.chart_kpt = TelemetryChart(
            "Ngón trỏ (Kpt 8 · Y)",
            [("Raw", T.MUTED), ("1€ Filter", T.ACCENT)],
            unit="",
        )
        self.chart_kpt.setAccessibleName("Biểu đồ so sánh tọa độ thô và sau bộ lọc One-Euro")
        self.chart_perf = TelemetryChart(
            "Hiệu năng",
            [("FPS", T.ACCENT), ("AI (ms)", T.WARNING)],
            unit="",
        )
        self.chart_perf.setAccessibleName("Biểu đồ FPS và độ trễ suy luận")
        charts_row = QHBoxLayout()
        charts_row.setSpacing(T.SP_3)
        charts_row.addWidget(self.chart_kpt, stretch=3)
        charts_row.addWidget(self.chart_perf, stretch=2)
        cam_layout.addLayout(charts_row)

        # Điều khiển camera & nạp model
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(T.SP_2)
        self.btn_cam_toggle = theme.button(
            "Tạm dừng Camera",
            tooltip="Bật/tắt camera (Ctrl+Space)",
            on_click=lambda: self.toggle_camera(start_only=False),
        )
        btn_load_model = theme.button(
            "Nạp trọng số YOLO (.pt / .onnx)",
            variant="ghost",
            tooltip="Chọn tệp trọng số YOLOv11-Pose khác",
            on_click=self._browse_model_file,
        )
        btn_bar.addWidget(self.btn_cam_toggle)
        btn_bar.addWidget(btn_load_model)
        cam_layout.addLayout(btn_bar)
        return cam_card

    def _build_control_column(self) -> QWidget:
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(T.SP_3)

        col.addWidget(self._build_mode_card())
        col.addWidget(self._build_status_card())

        self.stacked_panels = QStackedWidget()
        # Mode 1 (ASL) đã có vùng cuộn riêng cho danh sách Tra nhanh nên đặt trực tiếp để
        # Bảng hiển thị chữ & nút thao tác luôn cố định, không bao giờ bị cuộn khuất.
        self.stacked_panels.addWidget(self._create_asl_panel())
        for page in (
            self._create_touchless_panel(),
            self._create_air_mouse_panel(),
            self._create_presentation_panel(),
        ):
            self.stacked_panels.addWidget(self._wrap_scroll(page))
        col.addWidget(self.stacked_panels, stretch=1)
        return panel

    @staticmethod
    def _wrap_scroll(widget: QWidget) -> QScrollArea:
        """Bọc bảng chế độ trong QScrollArea trong suốt để chỉ cuộn khi cửa sổ nhỏ, giữ cố định bộ chọn chế độ."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        return scroll

    def _build_mode_card(self) -> QWidget:
        mode_card, mode_layout = theme.card(spacing=T.SP_2)
        mode_layout.addWidget(theme.caption("Chế độ hoạt động"))

        grid = QGridLayout()
        grid.setSpacing(T.SP_2)
        mode_defs = [
            (self.MODE_ASL, "1 · Ngôn ngữ ký hiệu", "Nhận diện bảng chữ cái ASL A–Z, ghép câu và đọc thành tiếng"),
            (self.MODE_TOUCHLESS, "2 · Điều khiển media", "Âm lượng, phát/dừng, chuyển bài, chụp màn hình bằng cử chỉ"),
            (self.MODE_AIR_MOUSE, "3 · Chuột không chạm", "Điều khiển con trỏ chuột bằng đầu ngón trỏ"),
            (self.MODE_PRESENTATION, "4 · Thuyết trình", "Tia laser ảo và lật slide bằng cách vẫy tay"),
        ]
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_buttons = {}
        for idx, (mode_id, text, hint) in enumerate(mode_defs):
            btn = theme.button(
                text,
                role="tab",
                checkable=True,
                tooltip=f"{hint}  (Ctrl+{idx + 1})",
                on_click=lambda m=mode_id: self._switch_mode(m),
            )
            btn.setChecked(mode_id == self.MODE_ASL)
            btn.setAccessibleName(f"Chế độ {text}")
            self.mode_group.addButton(btn)
            grid.addWidget(btn, idx // 2, idx % 2)
            self.mode_buttons[mode_id] = btn
        mode_layout.addLayout(grid)
        return mode_card

    def _build_status_card(self) -> QWidget:
        detect_card, detect_layout = theme.card(spacing=T.SP_2)
        detect_layout.addWidget(theme.caption("Trạng thái nhận diện"))

        self.lbl_current_symbol = theme.label("Đang chờ bàn tay…", role="hero", tone="idle", wrap=True)
        self.lbl_current_symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_current_symbol.setMinimumHeight(44)
        self.lbl_current_symbol.setAccessibleName("Cử chỉ đang nhận diện")
        detect_layout.addWidget(self.lbl_current_symbol)
        self._hero_tone = "idle"

        self.progress_hold = QProgressBar()
        self.progress_hold.setRange(0, 100)
        self.progress_hold.setValue(0)
        self.progress_hold.setFormat("Độ ổn định cử chỉ: %p%")
        self.progress_hold.setAccessibleName("Độ ổn định cử chỉ")
        detect_layout.addWidget(self.progress_hold)

        self.lbl_fingers_debug = theme.label(
            "5 ngón [Cái, Trỏ, Giữa, Áp, Út]: [-, -, -, -, -]", role="mono"
        )
        self.lbl_fingers_debug.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detect_layout.addWidget(self.lbl_fingers_debug)
        return detect_card

    def _install_shortcuts(self) -> None:
        for idx, mode_id in enumerate(
            (self.MODE_ASL, self.MODE_TOUCHLESS, self.MODE_AIR_MOUSE, self.MODE_PRESENTATION)
        ):
            sc = QShortcut(QKeySequence(f"Ctrl+{idx + 1}"), self)
            sc.activated.connect(lambda m=mode_id: self._switch_mode(m))
        cam_sc = QShortcut(QKeySequence("Ctrl+Space"), self)
        cam_sc.activated.connect(lambda: self.toggle_camera(start_only=False))

    def _set_hero_tone(self, tone: str) -> None:
        """Đổi màu nhãn chính theo trạng thái (chỉ repolish khi có thay đổi)."""
        if tone != self._hero_tone:
            self._hero_tone = tone
            theme.set_tone(self.lbl_current_symbol, tone)

    # ------------------------------------------------------------------
    # Các bảng điều khiển theo chế độ
    # ------------------------------------------------------------------
    def _create_asl_panel(self) -> QWidget:
        """Chế độ ASL: bảng hiển thị chữ A-Z, gợi ý từ, đọc thành tiếng, tra nhanh và cá nhân hóa mẫu."""
        card, layout = theme.card(spacing=T.SP_2, margins=(16, 12, 16, 12))

        # Tiêu đề bảng hiển thị chữ + bộ đếm ký tự trực tiếp
        head_row = QHBoxLayout()
        head_row.setSpacing(T.SP_2)
        head_row.addWidget(theme.caption("Bảng hiển thị chữ đã nhận diện (ASL A–Z)"))
        head_row.addStretch()
        self.lbl_char_count = theme.pill("0 ký tự", "neutral")
        self.lbl_char_count.setAccessibleName("Số ký tự đã ghép")
        head_row.addWidget(self.lbl_char_count)
        layout.addLayout(head_row)

        self.txt_sentence = QLineEdit()
        self.txt_sentence.setProperty("role", "sentence")
        self.txt_sentence.setPlaceholderText("Chữ cái A–Z sẽ hiện tại đây…")
        pal = self.txt_sentence.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(T.MUTED))
        self.txt_sentence.setPalette(pal)
        self.txt_sentence.setAccessibleName("Bảng hiển thị chữ đã nhận diện")
        self.txt_sentence.textChanged.connect(self._on_sentence_edited)
        layout.addWidget(self.txt_sentence)

        # Gợi ý từ (Autocomplete)
        sugg_layout = QHBoxLayout()
        sugg_layout.setSpacing(T.SP_2)
        sugg_layout.addWidget(theme.caption("Gợi ý từ"))
        self.sugg_buttons: List[QPushButton] = []
        for _ in range(3):
            btn = theme.button("-", role="chip", tooltip="Bấm để chọn từ gợi ý")
            btn.clicked.connect(self._on_suggestion_clicked)
            sugg_layout.addWidget(btn)
            self.sugg_buttons.append(btn)
        sugg_layout.addStretch()
        layout.addLayout(sugg_layout)
        self._refresh_suggestion_buttons()

        # Thao tác văn bản, giọng nói & mở bảng minh họa A–Z (gọn trong 2 hàng)
        btn_speak = theme.button(
            "Đọc to câu",
            variant="primary",
            tooltip="Đọc câu hiện tại thành tiếng (Text-to-Speech)",
            on_click=lambda: self.translator.speak_async(self.txt_sentence.text()),
        )
        btn_guide = theme.button(
            "Hướng dẫn A–Z",
            tooltip="Mở cửa sổ hình minh họa 21 khớp cho từng chữ cái A–Z",
            on_click=self._open_asl_guide_dialog,
        )
        btn_space = theme.button("Dấu cách", tooltip="Chèn dấu cách (Space)", on_click=self._action_space)
        btn_backspace = theme.button("Xóa 1 chữ", tooltip="Xóa ký tự cuối (Backspace)", on_click=self._action_backspace)
        btn_clear = theme.button("Xóa hết", variant="danger", tooltip="Xóa toàn bộ câu (Clear)", on_click=self._action_clear)

        actions = QGridLayout()
        actions.setSpacing(T.SP_2)
        actions.addWidget(btn_speak, 0, 0, 1, 2)
        actions.addWidget(btn_guide, 0, 2)
        actions.addWidget(btn_space, 1, 0)
        actions.addWidget(btn_backspace, 1, 1)
        actions.addWidget(btn_clear, 1, 2)
        layout.addLayout(actions)

        # Vùng cuộn duy nhất phía dưới (Cá nhân hóa + Tra nhanh A–Z),
        # để phần Bảng hiển thị chữ & nút thao tác phía trên luôn cố định ở mọi độ phân giải.
        lower_scroll = QScrollArea()
        lower_scroll.setWidgetResizable(True)
        lower_scroll.setFrameShape(QFrame.Shape.NoFrame)
        lower_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lower_scroll.setMinimumHeight(72)

        lower_inner = QWidget()
        lower_layout = QVBoxLayout(lower_inner)
        lower_layout.setContentsMargins(0, 0, T.SP_1, 0)
        lower_layout.setSpacing(T.SP_2)

        # Cá nhân hóa nhanh mẫu 21 điểm khớp
        calib_frame, calib_layout = theme.inset(spacing=T.SP_1, margins=(12, 8, 12, 8))
        calib_layout.addWidget(theme.caption("Cá nhân hóa 21 điểm khớp cho tay của bạn"))
        calib_row = QHBoxLayout()
        calib_row.setSpacing(T.SP_2)
        self.combo_calib_letter = QComboBox()
        self.combo_calib_letter.setMinimumWidth(88)
        self.combo_calib_letter.setAccessibleName("Ký hiệu cần lưu mẫu")
        for ch in [chr(c) for c in range(ord("A"), ord("Z") + 1)] + ["SPACE", "DEL"]:
            self.combo_calib_letter.addItem(ch)
        self.combo_calib_letter.currentTextChanged.connect(self._on_calib_letter_changed)
        btn_save_kpt = theme.button(
            "Lưu mẫu tư thế hiện tại",
            tooltip="Lưu tư thế tay đang hiển thị làm mẫu cho ký hiệu đã chọn",
            on_click=self._save_current_keypoint_sample,
        )
        calib_row.addWidget(self.combo_calib_letter)
        calib_row.addWidget(btn_save_kpt, stretch=1)
        calib_layout.addLayout(calib_row)

        self.lbl_calib_hint = theme.label("", role="subtitle", wrap=True)
        calib_layout.addWidget(self.lbl_calib_hint)
        self._on_calib_letter_changed("A")
        lower_layout.addWidget(calib_frame)

        # Bảng tra nhanh cử chỉ A–Z
        guide_frame, guide_layout = theme.inset(spacing=T.SP_1, margins=(12, 8, 12, 8))
        guide_layout.addWidget(theme.caption("Tra nhanh [Cái, Trỏ, Giữa, Áp, Út] · 1 = mở, 0 = gập"))
        for k, meta in ASL_GESTURE_GUIDE.items():
            row = theme.label(
                f"<b style='color:{T.ACCENT};'>{k}</b>&nbsp;&nbsp;"
                f"<span style='color:{T.SUCCESS}; font-family:Consolas;'>{meta['fingers']}</span>&nbsp;&nbsp;"
                f"<span style='color:{T.TEXT};'>{meta['short']}</span>",
                role="guide-row",
                wrap=True,
            )
            guide_layout.addWidget(row)
        lower_layout.addWidget(guide_frame)
        lower_layout.addStretch()

        lower_scroll.setWidget(lower_inner)
        layout.addWidget(lower_scroll, stretch=1)
        return card

    def _create_touchless_panel(self) -> QWidget:
        """Chế độ điều khiển media không chạm."""
        card, layout = theme.card(spacing=T.SP_2, margins=(16, 14, 16, 14))
        layout.addLayout(
            theme.panel_header(
                "Điều khiển Windows không chạm",
                "Thực hiện cử chỉ và giữ ổn định để kích hoạt lệnh.",
            )
        )

        vol_row = QHBoxLayout()
        vol_row.setSpacing(T.SP_3)
        vol_row.addWidget(theme.caption("Âm lượng Windows"))
        self.progress_volume = QProgressBar()
        self.progress_volume.setRange(0, 100)
        self.progress_volume.setValue(self.media_ctrl.current_volume_percent)
        self.progress_volume.setFormat("%p%")
        self.progress_volume.setProperty("tone", "ok")
        self.progress_volume.setAccessibleName("Âm lượng Windows hiện tại")
        vol_row.addWidget(self.progress_volume, stretch=1)
        layout.addLayout(vol_row)

        self.chk_pinch_volume = QCheckBox("Bật Pinch Volume")
        self.chk_pinch_volume.setChecked(False)
        self.chk_pinch_volume.setToolTip("Giơ Cái + Trỏ [1,1,0,0,0], kéo khoảng cách để chỉnh âm lượng 0–100%")
        layout.addWidget(self.chk_pinch_volume)
        layout.addWidget(
            theme.label(
                "Giơ ngón Cái + Trỏ, kéo khoảng cách để chỉnh 0–100%. "
                "Giữ yên ~0,7 giây để khóa mức âm lượng.",
                role="subtitle",
                wrap=True,
            )
        )

        self.lbl_last_command = theme.label("Lệnh gần nhất: Chưa có", role="status", tone="idle", wrap=True)
        layout.addWidget(self.lbl_last_command)

        layout.addWidget(theme.caption("Bảng cử chỉ"))
        layout.addWidget(
            theme.guide_list(
                [
                    ("Xòe 5 ngón", "Phát / tạm dừng video và nhạc"),
                    ("Nắm đấm", "Bật / tắt tiếng"),
                    ("Ngón cái lên", "Tăng âm lượng +6%"),
                    ("Ngón cái xuống", "Giảm âm lượng −6%"),
                    ("Chỉ trỏ phải / trái", "Bài kế tiếp / bài trước"),
                    ("Hai ngón chữ V", "Chụp ảnh màn hình"),
                ]
            )
        )
        layout.addStretch()
        return card

    def _create_air_mouse_panel(self) -> QWidget:
        """Chế độ chuột không chạm."""
        card, layout = theme.card(spacing=T.SP_3)
        layout.addLayout(
            theme.panel_header(
                "Chuột không chạm (Air Mouse)",
                f"Điều khiển con trỏ trên màn hình {self.air_mouse.screen_w} × {self.air_mouse.screen_h}.",
            )
        )

        self.chk_air_mouse = QCheckBox("Kích hoạt điều khiển con trỏ chuột")
        self.chk_air_mouse.setChecked(False)
        self.chk_air_mouse.setToolTip("Bỏ chọn để tạm dừng, chuột thật sẽ được trả lại ngay")
        self.chk_air_mouse.toggled.connect(lambda on: None if on else self.air_mouse.release())
        layout.addWidget(self.chk_air_mouse)

        self.lbl_mouse_state = theme.label("Trạng thái: Chưa kích hoạt", role="status", tone="idle", wrap=True)
        layout.addWidget(self.lbl_mouse_state)

        pinch_row = QHBoxLayout()
        pinch_row.setSpacing(T.SP_3)
        pinch_row.addWidget(theme.caption("Độ chụm Cái–Trỏ"))
        self.progress_pinch_left = QProgressBar()
        self.progress_pinch_left.setRange(0, 100)
        self.progress_pinch_left.setFormat("%p%")
        self.progress_pinch_left.setAccessibleName("Độ chụm ngón cái và ngón trỏ")
        pinch_row.addWidget(self.progress_pinch_left, stretch=1)
        layout.addLayout(pinch_row)

        layout.addWidget(theme.caption("Hướng dẫn"))
        layout.addWidget(
            theme.guide_list(
                [
                    ("Di chuyển ngón trỏ", "Điều khiển con trỏ trong khung xanh trên camera"),
                    ("Chụm Cái + Trỏ", "Nhấp chuột trái · giữ hơn 0,35 giây để kéo thả"),
                    ("Chụm Cái + Giữa", "Nhấp chuột phải (ngón trỏ vẫn mở)"),
                    ("Nắm tay", "Tạm dừng con trỏ để đặt lại vị trí tay"),
                ]
            )
        )
        layout.addStretch()
        return card

    def _create_presentation_panel(self) -> QWidget:
        """Chế độ thuyết trình: tia laser ảo và lật slide bằng vẫy tay."""
        card, layout = theme.card(spacing=T.SP_3)
        layout.addLayout(
            theme.panel_header(
                "Thuyết trình thông minh",
                "Tia laser ảo và lật slide bằng cử chỉ, không cần cầm điều khiển.",
            )
        )

        self.chk_laser = QCheckBox("Hiển thị tia laser đỏ trên toàn màn hình")
        self.chk_laser.setChecked(True)
        layout.addWidget(self.chk_laser)

        self.chk_swipe = QCheckBox("Cho phép lật slide bằng vẫy tay")
        self.chk_swipe.setChecked(True)
        layout.addWidget(self.chk_swipe)

        self.lbl_present_state = theme.label("Trạng thái: Chờ cử chỉ", role="status", tone="idle", wrap=True)
        layout.addWidget(self.lbl_present_state)

        self.lbl_slide_event = theme.label("Lệnh slide gần nhất: Chưa có", role="status", tone="idle", wrap=True)
        layout.addWidget(self.lbl_slide_event)

        layout.addWidget(theme.caption("Hướng dẫn"))
        layout.addWidget(
            theme.guide_list(
                [
                    ("Chỉ ngón trỏ", "Hiện tia laser đỏ theo đầu ngón tay"),
                    ("Xòe tay, vẫy trái", "Slide tiếp theo (phím →)"),
                    ("Xòe tay, vẫy phải", "Slide trước (phím ←)"),
                ]
            )
        )
        layout.addWidget(
            theme.label(
                "Mẹo: mở PowerPoint ở chế độ trình chiếu (F5) rồi bấm vào cửa sổ trình chiếu "
                "để nó nhận phím.",
                role="subtitle",
                wrap=True,
            )
        )
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
        self.cooldown_timer.check_trigger(None)
        self._block_cmds_until = 0.0
        self.progress_hold.setValue(0)
        if mode == self.MODE_TOUCHLESS:
            self.progress_volume.setValue(self.media_ctrl.refresh_volume())
        for mode_id, btn in self.mode_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(mode_id == mode)
            btn.blockSignals(False)
        self.stacked_panels.setCurrentIndex(mode)

    def _is_pinch_active(self) -> bool:
        return (
            self.current_mode == self.MODE_TOUCHLESS
            and hasattr(self, "chk_pinch_volume")
            and self.chk_pinch_volume.isChecked()
        )

    def _start_ai_worker(self) -> None:
        if self._ai_worker is None or not self._ai_worker.is_alive():
            self._ai_worker = _InferenceWorker(
                self.camera, self.detector, self._is_pinch_active
            )
            self._ai_worker.start()

    def _stop_ai_worker(self) -> None:
        if self._ai_worker is not None:
            self._ai_worker.stop()
            self._ai_worker = None

    def toggle_camera(self, start_only: bool = False) -> None:
        if not self.camera.running:
            ok = self.camera.start()
            if ok:
                self._start_ai_worker()
                self.timer.start(16)
                self.btn_cam_toggle.setText("Tạm dừng Camera")
                self.lbl_cam_status.setText("● Camera: bật")
                theme.set_tone(self.lbl_cam_status, "ok")
            else:
                self.btn_cam_toggle.setText("Bật lại Camera")
                self.video_label.setText(
                    "Không tìm thấy webcam.\nKiểm tra kết nối camera rồi bấm “Bật lại Camera”."
                )
                self.lbl_cam_status.setText("▲ Không có camera")
                theme.set_tone(self.lbl_cam_status, "danger")
        elif not start_only:
            self.timer.stop()
            self._stop_ai_worker()
            self.camera.stop()
            self.air_mouse.release()
            self.presenter.reset()
            self.laser_overlay.set_point(None)
            self.btn_cam_toggle.setText("Bật lại Camera")
            self.video_label.setPixmap(QPixmap())
            self.video_label.setText("Camera đang tạm dừng.\nBấm “Bật lại Camera” hoặc Ctrl+Space để tiếp tục.")
            self.lbl_cam_status.setText("■ Camera: tắt")
            theme.set_tone(self.lbl_cam_status, "warn")
            self._set_hero_tone("idle")
            self.lbl_current_symbol.setText("Camera đang tạm dừng")

    def _browse_model_file(self) -> None:
        models_dir = os.path.join(PROJECT_ROOT, "models")
        initial_dir = models_dir if os.path.isdir(models_dir) else PROJECT_ROOT
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file trọng số YOLOv11-Pose (.pt / .onnx)",
            initial_dir,
            "YOLO Weights (*.pt *.onnx)",
        )
        if filepath:
            if filepath.lower().endswith(".onnx") and importlib.util.find_spec("onnxruntime") is None:
                QMessageBox.warning(
                    self,
                    "Thiếu thư viện ONNX Runtime",
                    f"Không thể nạp file ONNX '{filepath}' vì môi trường chưa cài đặt 'onnxruntime'.\n"
                    "Vui lòng cài đặt 'onnxruntime' hoặc chọn file trọng số PyTorch (.pt).",
                )
                return
            was_running = self.camera.running
            self._stop_ai_worker()
            ok = self.detector.load_model(filepath)
            self.lbl_model_status.setText(f"Model: {self.detector.model_loaded_name}")
            theme.set_tone(self.lbl_model_status, "neutral" if ok else "danger")
            if was_running:
                self._start_ai_worker()
            if not ok:
                QMessageBox.warning(
                    self,
                    "Lỗi nạp model",
                    f"Không thể nạp file: {filepath}\nTrạng thái: {self.detector.model_loaded_name}",
                )

    @staticmethod
    def _draw_active_region(frame: np.ndarray, p1: tuple, p2: tuple, color: tuple) -> None:
        """Vẽ khung vùng hoạt động gọn gàng kèm 4 góc nhấn cho Air Mouse / Thuyết trình."""
        cv2.rectangle(frame, p1, p2, color, 1, cv2.LINE_AA)
        x1, y1 = p1
        x2, y2 = p2
        arm = 14
        for (cx, cy, dx, dy) in (
            (x1, y1, arm, arm),
            (x2, y1, -arm, arm),
            (x1, y2, arm, -arm),
            (x2, y2, -arm, -arm),
        ):
            cv2.line(frame, (cx, cy), (cx + dx, cy), color, 2, cv2.LINE_AA)
            cv2.line(frame, (cx, cy), (cx, cy + dy), color, 2, cv2.LINE_AA)

    @staticmethod
    def _draw_asl_badge(frame: np.ndarray, bbox: tuple, label: str, conf: float, committed: bool) -> None:
        """Vẽ nhãn chữ cái ASL đang nhận diện ngay phía trên khung bàn tay."""
        h_f, w_f = frame.shape[:2]
        x1, y1, _, _ = bbox
        txt = f"ASL: {label} ({conf * 100:.0f}%)"
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(txt, font, 0.65, 2)
        px = max(8, min(x1, w_f - tw - 20))
        py = max(th + 14, y1 - 8)
        bg_p1 = (px - 6, py - th - 8)
        bg_p2 = (px + tw + 8, py + 6)
        border = (153, 211, 52) if committed else (248, 189, 56)
        cv2.rectangle(frame, bg_p1, bg_p2, (32, 18, 11), -1)
        cv2.rectangle(frame, bg_p1, bg_p2, border, 1, cv2.LINE_AA)
        cv2.putText(frame, txt, (px, py), font, 0.65, border, 2, cv2.LINE_AA)

    @staticmethod
    def _draw_asl_caption_bar(frame: np.ndarray, sentence: str) -> None:
        """Vẽ dải phụ đề văn bản đã ghép ở mép dưới khung camera khi ở chế độ ASL."""
        clean = "".join(ch for ch in sentence if 32 <= ord(ch) < 127)
        if not clean:
            return
        display = clean[-30:]
        if len(clean) > 30:
            display = "..." + display
        h_f, w_f = frame.shape[:2]
        bar_h = 38
        y0 = max(0, h_f - bar_h)
        roi = frame[y0:h_f, 0:w_f]
        overlay = np.full_like(roi, (32, 18, 11))
        cv2.addWeighted(overlay, 0.78, roi, 0.22, 0.0, roi)
        cv2.line(frame, (0, y0), (w_f, y0), (248, 189, 56), 1, cv2.LINE_AA)
        cv2.putText(
            frame,
            f"TEXT: {display}",
            (14, h_f - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (248, 189, 56),
            2,
            cv2.LINE_AA,
        )

    def _process_frame(self) -> None:
        if self._ai_worker is None:
            return
        packet = self._ai_worker.pop_latest(self._last_ai_seq)
        if packet is None:
            return

        seq, frame, annotated, analyses, raw_kpts, cam_fps, ai_fps, infer_ms = packet
        self._last_ai_seq = seq
        self.lbl_fps.setText(f"Cam {cam_fps:.1f} · AI {ai_fps:.1f} FPS")
        self.last_analyses = analyses

        # Cập nhật biểu đồ hiệu năng (FPS & Latency ms)
        self.chart_perf.push([cam_fps, infer_ms])
        self.chart_perf.set_footer(f"Cam: {cam_fps:.1f} fps · AI: {infer_ms:.1f} ms")

        h_f, w_f = annotated.shape[:2]

        # Nếu ở chế độ Air Mouse hoặc Thuyết trình, vẽ khung vùng hoạt động chuẩn hóa lên HUD
        if self.current_mode in (self.MODE_AIR_MOUSE, self.MODE_PRESENTATION):
            rx1, ry1, rx2, ry2 = DEFAULT_ACTIVE_REGION
            p1 = (int(rx1 * w_f), int(ry1 * h_f))
            p2 = (int(rx2 * w_f), int(ry2 * h_f))
            # BGR cho T.ACCENT (#38bdf8) và T.DANGER (#f87171)
            box_color = (248, 189, 56) if self.current_mode == self.MODE_AIR_MOUSE else (113, 113, 248)
            self._draw_active_region(annotated, p1, p2, box_color)

        if analyses:
            primary = analyses[0]
            self.lbl_fingers_debug.setText(
                f"5 ngón [Cái, Trỏ, Giữa, Áp, Út]: {primary.fingers_up}"
            )

            # Cập nhật biểu đồ sóng Telemetry (Raw vs 1€ Filter trên đầu ngón trỏ Kpt 8)
            smooth_y = float(primary.keypoints[8][1])
            raw_y = float(raw_kpts[8][1]) if raw_kpts is not None else smooth_y
            self._raw_hist.append(raw_y)
            self._smooth_hist.append(smooth_y)
            self.chart_kpt.push([raw_y, smooth_y])
            if len(self._raw_hist) >= 6:
                raw_jit = float(np.std(np.diff(np.array(self._raw_hist))))
                smt_jit = float(np.std(np.diff(np.array(self._smooth_hist))))
                self.chart_kpt.set_footer(
                    f"Rung ΔRaw: {raw_jit:.2f}px → Δ1€: {smt_jit:.2f}px"
                )

            if self.current_mode == self.MODE_ASL:
                committed, progress, candidate = self.voting_buffer.update(
                    primary.asl_label, primary.asl_confidence
                )
                disp = candidate or primary.asl_label
                self.lbl_current_symbol.setText(f"Ký hiệu: {disp} ({primary.asl_confidence * 100:.0f}%)")
                self._set_hero_tone("ok" if committed else "active")
                self.progress_hold.setValue(int(progress * 100))
                self._draw_asl_badge(annotated, primary.bbox, disp, primary.asl_confidence, bool(committed))

                if committed:
                    new_text = self.translator.append_symbol(committed)
                    self.txt_sentence.setText(new_text)
                    theme.set_tone(self.txt_sentence, "ok")
                    self._refresh_suggestion_buttons()
                elif progress < 0.99:
                    theme.set_tone(self.txt_sentence, "active")

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
                        self._set_hero_tone("ok")
                        self.lbl_current_symbol.setText(f"Đã khóa âm lượng: {vol_pct}%")
                        self.progress_hold.setValue(100)
                        self.lbl_last_command.setText(
                            f"Đã chốt âm lượng {vol_pct}%. Hạ tay hoặc đổi tư thế rồi làm lại để chỉnh tiếp."
                        )
                        theme.set_tone(self.lbl_last_command, "ok")
                        cv2.putText(
                            annotated,
                            f"LOCKED: {vol_pct}%",
                            (16, 36),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.85,
                            (153, 211, 52),
                            2,
                            cv2.LINE_AA,
                        )
                    elif lock_state == "ARMING":
                        self._set_hero_tone("idle")
                        self.lbl_current_symbol.setText("Pinch: đang kích hoạt…")
                        self.progress_hold.setValue(0)
                    else:
                        self._set_hero_tone("active")
                        self.lbl_current_symbol.setText(f"Pinch Volume: {vol_pct}%")
                        self.progress_hold.setValue(int(lock_prog * 100))
                        self.lbl_last_command.setText(
                            f"Đang chỉnh {vol_pct}% — giữ yên tay để khóa"
                        )
                        theme.set_tone(self.lbl_last_command, "active")
                else:
                    self.pinch_ema.reset()
                    self._handle_pinch_exit()
                    now = time.perf_counter()
                    if now < self._block_cmds_until:
                        # Đang trong thời gian chặn sau Pinch: không kích hoạt lệnh nào
                        self.cooldown_timer.check_trigger(None)
                        self._set_hero_tone("idle")
                        self.lbl_current_symbol.setText(f"Cử chỉ: {gesture} (tạm chặn)")
                        self.progress_hold.setValue(0)
                    else:
                        triggered, progress = self.cooldown_timer.check_trigger(gesture)
                        self._set_hero_tone("ok" if triggered else "active")
                        self.lbl_current_symbol.setText(f"Cử chỉ: {gesture}")
                        self.progress_hold.setValue(int(progress * 100))
                        if triggered:
                            action_msg = self.media_ctrl.execute_gesture_command(gesture, frame=frame)
                            if action_msg:
                                self.lbl_last_command.setText(f"Lệnh gần nhất: {action_msg}")
                                theme.set_tone(self.lbl_last_command, "ok")
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
                    is_click = state in ("LEFT_DOWN", "DRAG", "RIGHT_CLICK")
                    self._set_hero_tone("ok" if is_click else ("idle" if state == "PAUSE" else "active"))
                    self.lbl_current_symbol.setText(f"Air Mouse: {state}")
                    if ev:
                        self.lbl_mouse_state.setText(f"Sự kiện: {ev} ({state})")
                        theme.set_tone(self.lbl_mouse_state, "ok")
                    else:
                        self.lbl_mouse_state.setText(f"Trạng thái: {state}")
                        theme.set_tone(self.lbl_mouse_state, "idle" if state == "PAUSE" else "active")

                    # Vẽ tâm ngắm tại đầu ngón trỏ (Keypoint 8)
                    ix, iy = int(primary.keypoints[8][0]), int(primary.keypoints[8][1])
                    c_ring = (153, 211, 52) if state in ("LEFT_DOWN", "DRAG") else (248, 189, 56)
                    cv2.circle(annotated, (ix, iy), 12, c_ring, 2, cv2.LINE_AA)
                else:
                    self.air_mouse.release()
                    self._set_hero_tone("idle")
                    self.lbl_current_symbol.setText("Air Mouse: đang tắt")
                    self.lbl_mouse_state.setText("Trạng thái: Chưa kích hoạt")
                    theme.set_tone(self.lbl_mouse_state, "idle")
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
                    theme.set_tone(self.lbl_slide_event, "ok")
                    self.laser_overlay.show_banner(str(slide_ev))

                if self.chk_laser.isChecked() and laser_pt is not None:
                    self.laser_overlay.set_point(laser_pt)
                    ix, iy = int(primary.keypoints[8][0]), int(primary.keypoints[8][1])
                    cv2.circle(annotated, (ix, iy), 14, (68, 68, 248), 3, cv2.LINE_AA)
                    cv2.circle(annotated, (ix, iy), 5, (255, 255, 255), -1, cv2.LINE_AA)
                    self._set_hero_tone("active")
                    self.lbl_current_symbol.setText("Tia laser: đang bật")
                    self.lbl_present_state.setText("Trạng thái: Đang chiếu tia laser đỏ")
                    theme.set_tone(self.lbl_present_state, "active")
                    self.progress_hold.setValue(100)
                else:
                    self.laser_overlay.set_point(None)
                    if time.perf_counter() < self._slide_banner_until:
                        self._set_hero_tone("ok")
                        self.lbl_current_symbol.setText(self._slide_banner_text)
                        self.lbl_present_state.setText(f"Đã thực thi: {self._slide_banner_text}")
                        theme.set_tone(self.lbl_present_state, "ok")
                        self.progress_hold.setValue(100)
                        hud_txt = "NEXT SLIDE >>" if "tiếp" in self._slide_banner_text else "<< PREV SLIDE"
                        cv2.putText(
                            annotated,
                            hud_txt,
                            (16, 36),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.85,
                            (248, 189, 56),
                            2,
                            cv2.LINE_AA,
                        )
                    elif p_state == "SWIPE_READY":
                        self._set_hero_tone("active")
                        self.lbl_current_symbol.setText("Sẵn sàng vẫy chuyển slide")
                        self.lbl_present_state.setText("Trạng thái: Đang xòe tay — vẫy trái/phải để lật slide")
                        theme.set_tone(self.lbl_present_state, "active")
                        self.progress_hold.setValue(int(swipe_prog * 100))
                    else:
                        self._set_hero_tone("idle")
                        self.lbl_current_symbol.setText(f"Thuyết trình: {p_state}")
                        self.lbl_present_state.setText(f"Trạng thái: {p_state}")
                        theme.set_tone(self.lbl_present_state, "idle")
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
                self._set_hero_tone("ok")
                self.lbl_current_symbol.setText(self._slide_banner_text)
                self.lbl_present_state.setText(f"Đã thực thi: {self._slide_banner_text}")
                theme.set_tone(self.lbl_present_state, "ok")
                self.progress_hold.setValue(100)
            else:
                self._set_hero_tone("idle")
                self.lbl_current_symbol.setText("Đang chờ bàn tay…")
                self.progress_hold.setValue(0)
                self.lbl_present_state.setText("Trạng thái: Đang chờ bàn tay…")
                theme.set_tone(self.lbl_present_state, "idle")
            self.progress_pinch_left.setValue(0)
            if self.chk_air_mouse.isChecked():
                self.lbl_mouse_state.setText("Trạng thái: Đang chờ bàn tay (con trỏ nghỉ)")
            else:
                self.lbl_mouse_state.setText("Trạng thái: Chưa kích hoạt")
            theme.set_tone(self.lbl_mouse_state, "idle")
            self.lbl_fingers_debug.setText("5 ngón [Cái, Trỏ, Giữa, Áp, Út]: [-, -, -, -, -]")

        if self.current_mode == self.MODE_ASL:
            self._draw_asl_caption_bar(annotated, self.txt_sentence.text())

        # Chuyển frame BGR sang QPixmap hiển thị lên giao diện
        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.video_label.setPixmap(pixmap)

    def _handle_pinch_exit(self) -> None:
        """Khi rời tư thế Pinch: hoàn tác phần âm lượng bị vọt lên do động tác rút tay."""
        rollback = self.pinch_lock.on_not_pinch()
        if rollback is not None:
            vol_pct = self.media_ctrl.set_volume_percent(int(round(rollback * 100)))
            self.progress_volume.setValue(vol_pct)
            self.lbl_last_command.setText(f"Lệnh gần nhất: Giữ âm lượng {vol_pct}% (đã bỏ qua động tác rút tay)")
            theme.set_tone(self.lbl_last_command, "ok")

    def _on_sentence_edited(self, text: str) -> None:
        self.translator.text_buffer = text
        if hasattr(self, "lbl_char_count"):
            self.lbl_char_count.setText(f"{len(text)} ký tự")
            theme.set_tone(self.lbl_char_count, "info" if text else "neutral")
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

        db_path = resolve_project_path(self.detector.analyzer.custom_keypoints_db_path)
        self.detector.analyzer.custom_keypoints_db_path = db_path
        try:
            count = self.detector.analyzer.save_custom_sample(kpts, label)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(
                self,
                "Không thể lưu mẫu 21-Keypoints",
                f"Dữ liệu khung xương hiện tại không hợp lệ hoặc không thể ghi DB cho '{label}': {exc}",
            )
            return
        QMessageBox.information(
            self,
            "Đã lưu mẫu 21-Keypoints",
            f"Đã lưu thành công tư thế 21 điểm khớp cho ký hiệu '{label}' (Tổng số mẫu '{label}': {count}).",
        )

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self._stop_ai_worker()
        self.camera.stop()
        self.detector.close()
        self.air_mouse.release()
        self.laser_overlay.close()
        event.accept()

