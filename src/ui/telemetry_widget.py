"""
Biểu đồ Telemetry thời gian thực (vẽ bằng QPainter, không cần thư viện ngoài).
Dùng để hiển thị:
  - Tọa độ đầu ngón trỏ (Keypoint 8): Raw (trước lọc) vs sau bộ lọc 1€.
  - FPS và độ trễ suy luận (ms) theo thời gian.
"""

from collections import deque
from typing import Deque, List, Optional, Sequence, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from src.ui.theme import T


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
        self.setMinimumHeight(124)
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

    def _y_range(self) -> Tuple[float, float, bool]:
        if self.fixed_range is not None:
            return self.fixed_range[0], self.fixed_range[1], True
        vals = [v for buf in self.data for v in buf if v is not None]
        if not vals:
            return 0.0, 1.0, False
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-6:
            lo, hi = lo - 1.0, hi + 1.0
        pad = (hi - lo) * 0.14
        return lo - pad, hi + pad, True

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Nền và viền bo góc khớp với theme Inset (không lem góc đen)
        outer = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        p.setBrush(QColor(T.INSET))
        p.setPen(QPen(QColor(T.BORDER), 1.0))
        p.drawRoundedRect(outer, float(T.RADIUS_CONTROL), float(T.RADIUS_CONTROL))

        # Chú thích chuỗi ở góc trên phải
        header_font = QFont("Segoe UI Variable Text", 8, QFont.Weight.DemiBold)
        p.setFont(header_font)
        fm = p.fontMetrics()

        lx = float(w - 10)
        for name, color, buf in reversed(list(zip(self.series_names, self.series_colors, self.data))):
            last = next((v for v in reversed(buf) if v is not None), None)
            label = f"{name}: {last:.1f}{self.unit}" if last is not None else f"{name}: —"
            tw = fm.horizontalAdvance(label)
            lx -= tw
            p.setPen(QColor(T.TEXT) if last is not None else QColor(T.MUTED))
            p.drawText(int(lx), 17, label)
            lx -= 12
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(QPointF(lx + 4, 13.5), 3.2, 3.2)
            lx -= 8

        # Tiêu đề góc trên trái (cắt gọn nếu màn hình hẹp để không đè chú thích)
        title_avail = max(40, int(lx) - 12)
        title_elided = fm.elidedText(self.title, Qt.TextElideMode.ElideRight, title_avail)
        p.setPen(QColor(T.MUTED))
        p.drawText(10, 17, title_elided)

        # Đường ngăn mảnh dưới tiêu đề
        p.setPen(QPen(QColor(T.BORDER), 1.0))
        p.drawLine(QPointF(10, 24), QPointF(w - 10, 24))

        # Vùng đồ thị
        top = 30.0
        bottom = float(h - (22 if self.footer_text else 10))
        left = 38.0
        right = float(w - 10)
        plot_h = max(1.0, bottom - top)
        plot_w = max(1.0, right - left)
        y_lo, y_hi, has_data = self._y_range()

        if not has_data:
            p.setFont(QFont("Segoe UI Variable Text", 8))
            p.setPen(QColor(T.DISABLED))
            p.drawText(
                QRectF(10, top, w - 20, plot_h),
                Qt.AlignmentFlag.AlignCenter,
                "Đang chờ dữ liệu…",
            )
        else:
            # Lưới ngang và nhãn trục Y
            axis_font = QFont("Consolas", 7)
            p.setFont(axis_font)
            grid_pen = QPen(QColor(T.RAISED), 1.0, Qt.PenStyle.DashLine)
            for i in range(4):
                yy = top + plot_h * i / 3.0
                p.setPen(grid_pen)
                p.drawLine(QPointF(left, yy), QPointF(right, yy))
                val = y_hi - (y_hi - y_lo) * i / 3.0
                p.setPen(QColor(T.DISABLED))
                p.drawText(
                    QRectF(4, yy - 6, left - 8, 12),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    f"{val:.0f}",
                )

            def to_pt(idx: int, v: float) -> QPointF:
                x = left + plot_w * idx / max(1, self.max_points - 1)
                y = top + plot_h * (1.0 - (v - y_lo) / (y_hi - y_lo))
                return QPointF(x, min(max(y, top), bottom))

            # Vẽ từng chuỗi (chuỗi cuối cùng có tô mờ nhẹ bên dưới để nổi bật đường chính)
            n_series = len(self.series_colors)
            for s_idx, (color, buf) in enumerate(zip(self.series_colors, self.data)):
                offset = self.max_points - len(buf)
                path = QPainterPath()
                fill_path = QPainterPath()
                pen_down = False
                seg_start_x = left
                last_pt: Optional[QPointF] = None

                for i, v in enumerate(buf):
                    if v is None:
                        if pen_down and last_pt is not None:
                            fill_path.lineTo(last_pt.x(), bottom)
                            fill_path.lineTo(seg_start_x, bottom)
                            fill_path.closeSubpath()
                        pen_down = False
                        continue
                    pt = to_pt(offset + i, v)
                    if pen_down:
                        path.lineTo(pt)
                        fill_path.lineTo(pt)
                    else:
                        path.moveTo(pt)
                        fill_path.moveTo(pt)
                        seg_start_x = pt.x()
                        pen_down = True
                    last_pt = pt

                if pen_down and last_pt is not None:
                    fill_path.lineTo(last_pt.x(), bottom)
                    fill_path.lineTo(seg_start_x, bottom)
                    fill_path.closeSubpath()

                if s_idx == n_series - 1:
                    grad = QLinearGradient(0, top, 0, bottom)
                    c_top = QColor(color)
                    c_top.setAlpha(42)
                    c_bot = QColor(color)
                    c_bot.setAlpha(0)
                    grad.setColorAt(0.0, c_top)
                    grad.setColorAt(1.0, c_bot)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(grad)
                    p.drawPath(fill_path)

                p.setBrush(Qt.BrushStyle.NoBrush)
                stroke = 1.9 if s_idx == n_series - 1 else 1.3
                p.setPen(QPen(color, stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.drawPath(path)

        # Thanh chân biểu đồ (số liệu tóm tắt)
        if self.footer_text:
            p.setFont(QFont("Consolas", 8))
            p.setPen(QColor(T.MUTED))
            p.drawText(10, h - 6, self.footer_text)
        p.end()
