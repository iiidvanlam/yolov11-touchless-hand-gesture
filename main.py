"""
Điểm khởi chạy chính của ứng dụng Desktop:
Nhận diện Ngôn ngữ Ký hiệu (ASL A-Z) & Điều khiển Thiết bị Không chạm với YOLOv11-Pose.
"""

import sys
from PyQt6.QtWidgets import QApplication
from src.ui.app_window import SignAndGestureApp


def main() -> None:
    app = QApplication(sys.argv)
    window = SignAndGestureApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

