"""
Lớp phủ tia laser ảo: cửa sổ trong suốt, luôn nằm trên cùng, không nhận chuột
(click xuyên qua), vẽ chấm laser đỏ phát sáng kèm vệt đuôi mờ dần.
"""

from collections import deque
from typing import Deque, Optional, Tuple

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPen, QRadialGradient
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
        if self.point is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

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
        p.end()
