"""
Hệ thống thiết kế (Design System) dùng chung cho toàn bộ giao diện PyQt6.

Nguyên tắc:
  - Một màu nhấn duy nhất (ACCENT) cho hành động chính và viền focus.
  - Màu ngữ nghĩa (SUCCESS / WARNING / DANGER) chỉ dùng cho TRẠNG THÁI và luôn đi kèm chữ/ký hiệu.
  - Thang khoảng cách 4 / 8 / 12 / 16 / 24 và 2 mức bo góc (điều khiển 8px, thẻ 12px).
  - Mọi widget tạo kiểu qua thuộc tính `role` / `variant` / `tone` thay vì setStyleSheet rải rác.
"""

from __future__ import annotations

import os
import tempfile
from string import Template
from typing import Callable, Optional, Sequence, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class T:
    """Design tokens."""

    # Bề mặt
    BG = "#0b1220"
    SURFACE = "#111a2c"
    RAISED = "#18253d"
    RAISED_HOVER = "#203253"
    INSET = "#0a101c"
    BORDER = "#24324a"
    BORDER_STRONG = "#3a4d6d"

    # Chữ (tương phản trên SURFACE: TEXT ~14:1, MUTED ~6.9:1)
    TEXT = "#e6edf7"
    MUTED = "#93a4bd"
    DISABLED = "#5d6e89"

    # Màu nhấn duy nhất
    ACCENT = "#38bdf8"
    ACCENT_HOVER = "#62cbfa"
    ACCENT_PRESSED = "#1f9fd8"
    ACCENT_DEEP = "#0f7bb0"  # nền thanh tiến trình: chữ trắng đạt 4.7:1
    ON_ACCENT = "#04131f"

    # Màu trạng thái
    SUCCESS = "#34d399"
    SUCCESS_DEEP = "#0f7a55"
    WARNING = "#fbbf24"
    DANGER = "#f87171"
    DANGER_BG = "#b42323"
    DANGER_BG_HOVER = "#cc2d2d"

    # Thang khoảng cách
    SP_1 = 4
    SP_2 = 8
    SP_3 = 12
    SP_4 = 16
    SP_6 = 24

    # Bo góc
    RADIUS_CONTROL = 8
    RADIUS_CARD = 12


def _rgba(hex_color: str, alpha: int) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


def _ensure_icons() -> Tuple[str, str]:
    """Sinh icon dấu tick (checkbox) và mũi tên (combobox) để trạng thái không chỉ dựa vào màu."""
    base = os.path.join(tempfile.gettempdir(), "nhandien_cuchitay_ui")
    check_path = os.path.join(base, "check.png")
    chevron_path = os.path.join(base, "chevron.png")
    try:
        os.makedirs(base, exist_ok=True)

        pm = QPixmap(18, 18)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(T.ON_ACCENT), 2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPolyline([_pt(4.5, 9.5), _pt(7.8, 12.8), _pt(13.5, 5.8)])
        p.end()
        pm.save(check_path, "PNG")

        pm2 = QPixmap(12, 12)
        pm2.fill(Qt.GlobalColor.transparent)
        p2 = QPainter(pm2)
        p2.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen2 = QPen(QColor(T.MUTED), 1.8)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen2.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p2.setPen(pen2)
        p2.drawPolyline([_pt(2.5, 4.5), _pt(6.0, 8.0), _pt(9.5, 4.5)])
        p2.end()
        pm2.save(chevron_path, "PNG")
    except Exception:
        return "", ""
    return check_path.replace("\\", "/"), chevron_path.replace("\\", "/")


def _pt(x: float, y: float):
    from PyQt6.QtCore import QPointF

    return QPointF(x, y)


_QSS = Template(
    """
QWidget {
    color: $TEXT;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background-color: $BG; }
QWidget#Root { background-color: $BG; }
QLabel { background: transparent; }

QFrame#Header {
    background-color: $SURFACE;
    border: none;
    border-bottom: 1px solid $BORDER;
}
QFrame#Card {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 12px;
}
QFrame#Inset {
    background-color: $INSET;
    border: 1px solid $BORDER;
    border-radius: 8px;
}

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QFrame#Inset QScrollArea { background: transparent; border: none; }

/* ---------- Chữ theo vai trò ---------- */
QLabel[role="caption"]  { color: $MUTED; font-size: 11px; font-weight: 600; }
QLabel[role="title"]    { font-size: 15px; font-weight: 600; }
QLabel[role="subtitle"] { color: $MUTED; font-size: 12px; }
QLabel[role="body"]     { color: $TEXT; }
QLabel[role="mono"]     { color: $MUTED; font-family: Consolas, "Cascadia Mono", monospace; font-size: 12px; }
QLabel[role="hero"]     { color: $MUTED; font-size: 22px; font-weight: 700; padding: 2px 0px; }
QLabel[role="hero"][tone="active"] { color: $ACCENT; }
QLabel[role="hero"][tone="ok"]     { color: $SUCCESS; }

QLabel[role="viewport"] {
    background-color: $INSET;
    border: 1px solid $BORDER;
    border-radius: 8px;
    color: $MUTED;
    font-size: 14px;
}
QLabel[role="diagram"] {
    background-color: $INSET;
    border: 1px solid $BORDER_STRONG;
    border-radius: 10px;
}
QLabel[role="detail"] {
    background-color: $INSET;
    border: 1px solid $BORDER;
    border-radius: 8px;
    color: $TEXT;
    padding: 12px;
    font-size: 13px;
}
QLabel[role="guide-row"] {
    color: $TEXT;
    font-size: 12px;
    padding: 4px 2px;
    border-bottom: 1px solid $BORDER;
}

/* ---------- Pill trạng thái (luôn có chữ/ký hiệu đi kèm) ---------- */
QLabel[role="pill"] {
    background-color: $RAISED;
    border: 1px solid $BORDER_STRONG;
    border-radius: 12px;
    color: $MUTED;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 600;
}
QLabel[role="pill"][tone="info"]    { background-color: $ACCENT_BG; border-color: $ACCENT_BORDER; color: $ACCENT; }
QLabel[role="pill"][tone="ok"]      { background-color: $SUCCESS_BG; border-color: $SUCCESS_BORDER; color: $SUCCESS; }
QLabel[role="pill"][tone="warn"]    { background-color: $WARNING_BG; border-color: $WARNING_BORDER; color: $WARNING; }
QLabel[role="pill"][tone="danger"]  { background-color: $DANGER_SOFT_BG; border-color: $DANGER_BORDER; color: $DANGER; }

/* ---------- Khung trạng thái / thông báo ---------- */
QLabel[role="status"] {
    background-color: $INSET;
    border: 1px solid $BORDER;
    border-left: 3px solid $ACCENT;
    border-radius: 8px;
    color: $TEXT;
    padding: 8px 12px;
    font-weight: 600;
}
QLabel[role="status"][tone="idle"]   { border-left-color: $BORDER_STRONG; color: $MUTED; }
QLabel[role="status"][tone="ok"]     { border-left-color: $SUCCESS; }
QLabel[role="status"][tone="warn"]   { border-left-color: $WARNING; }
QLabel[role="status"][tone="danger"] { border-left-color: $DANGER; }

QLabel[role="keycap"] {
    background-color: $RAISED;
    border: 1px solid $BORDER_STRONG;
    border-radius: 6px;
    color: $TEXT;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 600;
}

/* ---------- Nút ---------- */
QPushButton {
    background-color: $RAISED;
    color: $TEXT;
    border: 1px solid $BORDER_STRONG;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
    min-height: 20px;
}
QPushButton[variant="primary"] {
    background-color: $ACCENT;
    color: $ON_ACCENT;
    border: 1px solid $ACCENT;
}
QPushButton[variant="danger"] {
    background-color: $DANGER_BG;
    color: #ffffff;
    border: 1px solid $DANGER_BG;
}
QPushButton[variant="ghost"] {
    background-color: transparent;
    border: 1px solid $BORDER_STRONG;
}
QPushButton[role="tab"] {
    background-color: $INSET;
    border: 1px solid $BORDER;
    text-align: left;
    padding: 10px 14px;
}
QPushButton[role="chip"] {
    border-radius: 14px;
    padding: 4px 12px;
    min-height: 18px;
    font-size: 12px;
}
QPushButton[role="key"] {
    padding: 4px 0px;
    min-width: 38px;
    font-family: Consolas, "Cascadia Mono", monospace;
}

QPushButton:hover { background-color: $RAISED_HOVER; border-color: $MUTED; }
QPushButton[variant="primary"]:hover { background-color: $ACCENT_HOVER; border-color: $ACCENT_HOVER; }
QPushButton[variant="danger"]:hover  { background-color: $DANGER_BG_HOVER; border-color: $DANGER_BG_HOVER; }
QPushButton[variant="ghost"]:hover   { background-color: $RAISED; }
QPushButton[role="tab"]:hover        { background-color: $RAISED; }

QPushButton:pressed { background-color: $INSET; }
QPushButton[variant="primary"]:pressed { background-color: $ACCENT_PRESSED; border-color: $ACCENT_PRESSED; }
QPushButton[variant="danger"]:pressed  { background-color: $DANGER_BG; }

QPushButton[role="tab"]:checked {
    background-color: $ACCENT_BG;
    border: 1px solid $ACCENT;
    border-left: 3px solid $ACCENT;
    padding-left: 12px;
    color: $TEXT;
}
QPushButton[role="key"]:checked {
    background-color: $ACCENT_BG;
    border: 1px solid $ACCENT;
    color: $ACCENT;
}

QPushButton:focus { border: 2px solid $ACCENT; padding: 6px 13px; outline: none; }
QPushButton[role="tab"]:focus { padding: 9px 13px; }
QPushButton[role="tab"]:checked:focus { border: 2px solid $ACCENT; border-left: 3px solid $ACCENT; padding: 9px 13px 9px 12px; }
QPushButton[role="chip"]:focus { padding: 3px 11px; }
QPushButton[role="key"]:focus { padding: 3px 0px; }

QPushButton:disabled {
    background-color: $INSET;
    color: $DISABLED;
    border: 1px solid $BORDER;
}

/* ---------- Nhập liệu ---------- */
QLineEdit {
    background-color: $INSET;
    color: $TEXT;
    border: 1px solid $BORDER_STRONG;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 16px;
    font-weight: 600;
    selection-background-color: $ACCENT;
    selection-color: $ON_ACCENT;
}
QLineEdit:focus { border: 2px solid $ACCENT; padding: 7px 11px; }
QLineEdit[role="sentence"] {
    background-color: $INSET;
    color: $ACCENT;
    border: 1px solid $ACCENT_BORDER;
    border-left: 3px solid $ACCENT;
    border-radius: 10px;
    padding: 9px 14px 9px 12px;
    font-size: 22px;
    font-weight: 700;
    min-height: 28px;
}
QLineEdit[role="sentence"]:focus {
    border: 2px solid $ACCENT;
    border-left: 3px solid $ACCENT;
    padding: 8px 13px 8px 12px;
}
QLineEdit[role="sentence"][tone="ok"] {
    border-color: $SUCCESS_BORDER;
    border-left: 3px solid $SUCCESS;
}

QComboBox {
    background-color: $INSET;
    color: $TEXT;
    border: 1px solid $BORDER_STRONG;
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 20px;
}
QComboBox:hover { border-color: $MUTED; }
QComboBox:focus, QComboBox:on { border: 2px solid $ACCENT; padding: 5px 11px; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow { image: url("$CHEVRON"); width: 12px; height: 12px; }
QComboBox QAbstractItemView {
    background-color: $SURFACE;
    border: 1px solid $BORDER_STRONG;
    selection-background-color: $ACCENT_BG;
    selection-color: $TEXT;
    outline: none;
    padding: 4px;
}

QCheckBox { spacing: 10px; padding: 3px 4px; border-radius: 6px; }
QCheckBox:focus { background-color: $ACCENT_BG; }
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid $BORDER_STRONG;
    border-radius: 5px;
    background-color: $INSET;
}
QCheckBox::indicator:hover { border-color: $MUTED; }
QCheckBox::indicator:checked {
    background-color: $ACCENT;
    border-color: $ACCENT;
    image: url("$CHECK");
}

/* ---------- Tiến trình ---------- */
QProgressBar {
    background-color: $INSET;
    border: 1px solid $BORDER;
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
    min-height: 18px;
    max-height: 18px;
}
QProgressBar::chunk { background-color: $ACCENT_DEEP; border-radius: 7px; }
QProgressBar[tone="ok"]::chunk { background-color: $SUCCESS_DEEP; }

/* ---------- Thanh cuộn, tooltip, splitter ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $BORDER_STRONG; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: $MUTED; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $BORDER_STRONG; border-radius: 4px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: $MUTED; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0px; width: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QToolTip {
    background-color: $RAISED;
    color: $TEXT;
    border: 1px solid $BORDER_STRONG;
    padding: 6px 8px;
}
QSplitter::handle { background: transparent; }
QSplitter::handle:hover { background-color: $BORDER; }
"""
)


def build_stylesheet() -> str:
    """Tạo stylesheet toàn cục từ token. Cần gọi sau khi QApplication đã tồn tại (để sinh icon)."""
    check, chevron = _ensure_icons()
    values = {
        k: v
        for k, v in vars(T).items()
        if k.isupper() and isinstance(v, str)
    }
    values.update(
        {
            "ACCENT_BG": _rgba(T.ACCENT, 38),
            "ACCENT_BORDER": _rgba(T.ACCENT, 115),
            "SUCCESS_BG": _rgba(T.SUCCESS, 34),
            "SUCCESS_BORDER": _rgba(T.SUCCESS, 115),
            "WARNING_BG": _rgba(T.WARNING, 34),
            "WARNING_BORDER": _rgba(T.WARNING, 115),
            "DANGER_SOFT_BG": _rgba(T.DANGER, 34),
            "DANGER_BORDER": _rgba(T.DANGER, 115),
            "CHECK": check,
            "CHEVRON": chevron,
        }
    )
    return _QSS.safe_substitute(values)


# ======================================================================
# Hàm trợ giúp dựng widget theo design system
# ======================================================================
def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_prop(widget: QWidget, name: str, value: str) -> None:
    """Đổi thuộc tính kiểu (chỉ repolish khi giá trị thực sự thay đổi để tránh tốn CPU mỗi khung hình)."""
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    repolish(widget)


def set_tone(widget: QWidget, tone: str) -> None:
    set_prop(widget, "tone", tone)


def label(
    text: str = "",
    role: Optional[str] = None,
    tone: Optional[str] = None,
    wrap: bool = False,
) -> QLabel:
    lbl = QLabel(text)
    if role:
        lbl.setProperty("role", role)
    if tone:
        lbl.setProperty("tone", tone)
    lbl.setWordWrap(wrap)
    return lbl


def caption(text: str) -> QLabel:
    lbl = label(text.upper(), role="caption")
    font = lbl.font()
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
    lbl.setFont(font)
    return lbl


def pill(text: str, tone: str = "neutral") -> QLabel:
    lbl = label(text, role="pill", tone=tone)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def button(
    text: str,
    variant: Optional[str] = None,
    role: Optional[str] = None,
    tooltip: Optional[str] = None,
    on_click: Optional[Callable[[], None]] = None,
    checkable: bool = False,
) -> QPushButton:
    btn = QPushButton(text)
    if variant:
        btn.setProperty("variant", variant)
    if role:
        btn.setProperty("role", role)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCheckable(checkable)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click is not None:
        btn.clicked.connect(lambda _checked=False: on_click())
    return btn


def card(spacing: int = T.SP_3, margins: Tuple[int, int, int, int] = (16, 16, 16, 16)) -> Tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


def inset(spacing: int = T.SP_2, margins: Tuple[int, int, int, int] = (12, 12, 12, 12)) -> Tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Inset")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


def panel_header(title: str, subtitle: str) -> QVBoxLayout:
    box = QVBoxLayout()
    box.setSpacing(2)
    box.addWidget(label(title, role="title"))
    box.addWidget(label(subtitle, role="subtitle", wrap=True))
    return box


def guide_list(rows: Sequence[Tuple[str, str]], key_width: int = 148) -> QFrame:
    """Bảng hướng dẫn: [cử chỉ] -> [tác dụng], thay cho chữ căn lề bằng dấu cách."""
    frame, layout = inset(spacing=T.SP_2)
    for key, desc in rows:
        row = QHBoxLayout()
        row.setSpacing(T.SP_3)
        cap = label(key, role="keycap")
        cap.setFixedWidth(key_width)
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(cap, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(label(desc, role="body", wrap=True), 1)
        layout.addLayout(row)
    return frame
