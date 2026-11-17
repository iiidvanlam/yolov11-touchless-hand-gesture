"""
Lớp phủ tia laser ảo: cửa sổ trong suốt, luôn nằm trên cùng, không nhận chuột
(click xuyên qua), vẽ chấm laser đỏ phát sáng kèm vệt đuôi mờ dần và thông báo lật slide.
"""

from collections import deque
import time
from typing import Deque, Optional, Tuple

from PyQt6.QtCore import QPointF, QRectF, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget


class LaserOverlay(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(screen.geometry())
        self.trail: Deque[QPointF] = deque(maxlen=16)
        self.point: Optional[QPointF] = None
        self.banner_text: str = ""
        self.banner_until: float = 0.0

        self._banner_timer = QTimer(self)
        self._banner_timer.setSingleShot(True)
        self._banner_timer.timeout.connect(self._clear_banner)

    def show_banner(self, text: str, duration_ms: int = 1100) -> None:
        self.banner_text = text
        self.banner_until = time.perf_counter() + duration_ms / 1000.0
        self._banner_timer.start(duration_ms)
        self.update()

    def _clear_banner(self) -> None:
        self.banner_text = ""
        self.banner_until = 0.0
        self.update()

    def set_point(self, norm: Optional[Tuple[float, float]]) -> None:
        if norm is None:
            if self.point is not None or self.trail:
                self.point = None
                self.trail.clear()
                self.update()
            return
        nx, ny = norm
        pt = QPointF(nx * self.width(), ny * self.height())
        if self.point is not None:
            # Làm mượt nhẹ để chấm laser không run
            pt = QPointF(0.5 * pt.x() + 0.5 * self.point.x(), 0.5 * pt.y() + 0.5 * self.point.y())
        self.point = pt
        self.trail.append(pt)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        show_banner = bool(self.banner_text) and time.perf_counter() < self.banner_until
        if self.point is None and not show_banner:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.point is not None:
            pts = list(self.trail)
            n = len(pts)
            for i in range(1, n):
                alpha = int(200 * i / n)
                p.setPen(QPen(QColor(255, 40, 40, alpha), 2 + 4 * i / n, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(pts[i - 1], pts[i])

            glow = QRadialGradient(self.point, 26)
            glow.setColorAt(0.0, QColor(255, 255, 255, 255))
            glow.setColorAt(0.18, QColor(255, 60, 60, 255))
            glow.setColorAt(0.55, QColor(255, 0, 0, 110))
            glow.setColorAt(1.0, QColor(255, 0, 0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawEllipse(self.point, 26, 26)

        if show_banner:
            bw, bh = 360, 56
            bx = (self.width() - bw) / 2.0
            by = 36.0
            rect = QRectF(bx, by, bw, bh)
            p.setPen(QPen(QColor(56, 189, 248, 230), 2))
            p.setBrush(QColor(15, 23, 42, 215))
            p.drawRoundedRect(rect, 12, 12)
            p.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            p.setPen(QColor(248, 250, 252))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.banner_text)

        p.end()
