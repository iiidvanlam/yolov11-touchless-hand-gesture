"""
Biểu đồ Telemetry thời gian thực (vẽ bằng QPainter, không cần thư viện ngoài).
Dùng để hiển thị:
  - Tọa độ đầu ngón trỏ (Keypoint 8): Raw (trước lọc) vs sau bộ lọc 1€.
  - FPS và độ trễ suy luận (ms) theo thời gian.
"""

from collections import deque
from typing import Deque, List, Optional, Sequence, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


class TelemetryChart(QWidget):
    """Biểu đồ đường nhiều chuỗi, cuộn theo thời gian, tự co giãn trục Y."""

    def __init__(
        self,
        title: str,
        series: Sequence[Tuple[str, str]],
        max_points: int = 150,
        unit: str = "",
        fixed_range: Optional[Tuple[float, float]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title = title
        self.series_names = [s[0] for s in series]
        self.series_colors = [QColor(s[1]) for s in series]
        self.unit = unit
        self.fixed_range = fixed_range
        self.data: List[Deque[Optional[float]]] = [deque(maxlen=max_points) for _ in series]
        self.max_points = max_points
        self.footer_text = ""
        self.setMinimumHeight(118)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def push(self, values: Sequence[Optional[float]]) -> None:
        for buf, v in zip(self.data, values):
            buf.append(None if v is None else float(v))
        self.update()

    def set_footer(self, text: str) -> None:
        self.footer_text = text

    def clear(self) -> None:
        for buf in self.data:
            buf.clear()
        self.update()

    def _y_range(self) -> Tuple[float, float]:
        if self.fixed_range is not None:
            return self.fixed_range
        vals = [v for buf in self.data for v in buf if v is not None]
        if not vals:
            return 0.0, 1.0
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-6:
            lo, hi = lo - 1.0, hi + 1.0
        pad = (hi - lo) * 0.12
        return lo - pad, hi + pad

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(self.rect(), QColor("#020617"))
        p.setPen(QPen(QColor("#334155"), 1))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 6, 6)

        # Tiêu đề + chú thích
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(QColor("#94a3b8"))
        p.drawText(8, 14, self.title)

        lx = w - 8
        for name, color, buf in reversed(list(zip(self.series_names, self.series_colors, self.data))):
            last = next((v for v in reversed(buf) if v is not None), None)
            label = f"{name}: {last:.1f}{self.unit}" if last is not None else f"{name}: -"
            tw = p.fontMetrics().horizontalAdvance(label)
            lx -= tw
            p.setPen(color)
            p.drawText(int(lx), 14, label)
            lx -= 14
            p.fillRect(QRectF(lx + 3, 7, 8, 8), color)
            lx -= 6

        # Vùng vẽ
        top, bottom = 22, h - (18 if self.footer_text else 8)
        left, right = 36, w - 8
        plot_h = max(1, bottom - top)
        plot_w = max(1, right - left)
        y_lo, y_hi = self._y_range()

        p.setFont(QFont("Consolas", 7))
        for i in range(4):
            yy = top + plot_h * i / 3.0
            p.setPen(QPen(QColor("#1e293b"), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(left, yy), QPointF(right, yy))
            val = y_hi - (y_hi - y_lo) * i / 3.0
            p.setPen(QColor("#64748b"))
            p.drawText(2, int(yy) + 4, f"{val:.0f}")

        def to_pt(idx: int, v: float) -> QPointF:
            x = left + plot_w * idx / max(1, self.max_points - 1)
            y = top + plot_h * (1.0 - (v - y_lo) / (y_hi - y_lo))
            return QPointF(x, min(max(y, top), bottom))

        for color, buf in zip(self.series_colors, self.data):
            offset = self.max_points - len(buf)
            path = QPainterPath()
            pen_down = False
            for i, v in enumerate(buf):
                if v is None:
                    pen_down = False
                    continue
                pt = to_pt(offset + i, v)
                if pen_down:
                    path.lineTo(pt)
                else:
                    path.moveTo(pt)
                    pen_down = True
            p.setPen(QPen(color, 1.6))
            p.drawPath(path)

        if self.footer_text:
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(QColor("#fbbf24"))
            p.drawText(8, h - 5, self.footer_text)
        p.end()
