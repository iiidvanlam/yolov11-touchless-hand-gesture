from typing import Dict
import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QKeyEvent, QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.pose_analyzer import HAND_SKELETON_CONNECTIONS
from src.ui import theme
from src.ui.theme import T


# Bảng hướng dẫn chi tiết cách đặt ngón tay cho toàn bộ 26 chữ cái A-Z + SPACE + DEL
# Thứ tự 5 ngón: [Cái, Trỏ, Giữa, Áp út, Út] (1 = Duỗi mở, 0 = Gập/Cong)
ASL_GESTURE_GUIDE: Dict[str, Dict[str, object]] = {
    "A": {
        "fingers": "[1, 0, 0, 0, 0]",
        "short": "Nắm 4 ngón, ngón Cái duỗi áp sát cạnh ngón trỏ",
        "detail": "• Gập kín 4 ngón (Trỏ, Giữa, Áp út, Út) vào lòng bàn tay.\n• Ngón Cái duỗi thẳng hướng lên dọc theo cạnh bên của ngón Trỏ.\n• Mã trạng thái 5 ngón: [1, 0, 0, 0, 0].",
        "pose": "thumb_up_side",
    },
    "B": {
        "fingers": "[0, 1, 1, 1, 1]",
        "short": "Duỗi thẳng 4 ngón (Trỏ, Giữa, Áp, Út), gập ngón Cái vào lòng bàn tay",
        "detail": "• Duỗi thẳng đứng 4 ngón: Trỏ, Giữa, Áp út, Út khép cạnh nhau.\n• Gập ngón Cái ngang qua trước lòng bàn tay.\n• Mã trạng thái 5 ngón: [0, 1, 1, 1, 1].",
        "pose": "four_up",
    },
    "C": {
        "fingers": "[0, 0, 0, 0, 0]",
        "short": "Khum cong cả 5 ngón tay tạo thành hình chữ C",
        "detail": "• Uốn cong nhẹ 4 ngón tay và ngón Cái đối diện nhau tạo thành vòng cung hở giống chữ C.\n• Giữ khoảng cách giữa đầu ngón Cái và đầu ngón Trỏ vừa phải (không chạm sát như chữ O).\n• Mã trạng thái 5 ngón: [0, 0, 0, 0, 0] (cong hình cung).",
        "pose": "c_curve",
    },
    "D": {
        "fingers": "[0, 1, 0, 0, 0]",
        "short": "Chỉ duỗi thẳng ngón Trỏ hướng lên trên, 4 ngón còn lại gập",
        "detail": "• Duỗi thẳng đứng duy nhất ngón Trỏ hướng lên trên.\n• Gập 3 ngón Giữa, Áp út, Út chạm vào ngón Cái.\n• Mã trạng thái 5 ngón: [0, 1, 0, 0, 0].",
        "pose": "index_up",
    },
    "E": {
        "fingers": "[0, 0, 0, 0, 0]",
        "short": "Gập kín 4 ngón xuống thấp, ngón Cái gập nằm dưới 4 đầu ngón tay",
        "detail": "• Gập cả 4 ngón tay xuống sát lòng bàn tay.\n• Ngón Cái gập ngang nằm ở phía dưới các đầu ngón Trỏ - Giữa (thấp hơn khớp ngón trỏ).\n• Mã trạng thái 5 ngón: [0, 0, 0, 0, 0].",
        "pose": "fist_e",
    },
    "F": {
        "fingers": "[0, 0, 1, 1, 1]",
        "short": "Chạm đầu ngón Cái & Trỏ thành vòng tròn (OK), duỗi thẳng 3 ngón Giữa-Áp-Út",
        "detail": "• Đưa đầu ngón Trỏ chạm vào đầu ngón Cái tạo thành vòng tròn (giống ký hiệu OK).\n• Duỗi thẳng hoàn toàn 3 ngón còn lại: Giữa, Áp út và Út hướng lên trên.\n• Mã trạng thái 5 ngón: [0, 0, 1, 1, 1] (hoặc [1, 0, 1, 1, 1]).",
        "pose": "ok_f",
    },
    "G": {
        "fingers": "[1, 1, 0, 0, 0]",
        "short": "Mở ngón Cái & ngón Trỏ song song chỉ ngang sang bên, 3 ngón kia gập",
        "detail": "• Mở ngón Cái và ngón Trỏ, xoay cổ tay để ngón Trỏ và ngón Cái chỉ ngang (nằm ngang).\n• Gập 3 ngón Giữa, Áp út, Út vào lòng bàn tay.\n• Mã trạng thái 5 ngón: [1, 1, 0, 0, 0] (ngón trỏ nằm ngang).",
        "pose": "g_horiz",
    },
    "H": {
        "fingers": "[0, 1, 1, 0, 0]",
        "short": "Duỗi 2 ngón Trỏ & Giữa khép sát chỉ ngang sang bên",
        "detail": "• Duỗi thẳng 2 ngón Trỏ và Giữa, nhưng xoay bàn tay để 2 ngón này chỉ ngang sang bên.\n• Gập ngón Cái, Áp út và Út.\n• Mã trạng thái 5 ngón: [0, 1, 1, 0, 0] (nằm ngang).",
        "pose": "h_horiz",
    },
    "I": {
        "fingers": "[0, 0, 0, 0, 1]",
        "short": "Chỉ duỗi thẳng đứng duy nhất ngón Út, 4 ngón còn lại nắm",
        "detail": "• Nắm 4 ngón Cái, Trỏ, Giữa, Áp út vào lòng bàn tay.\n• Duỗi thẳng đứng duy nhất ngón Út hướng lên trên.\n• Mã trạng thái 5 ngón: [0, 0, 0, 0, 1].",
        "pose": "pinky_up",
    },
    "J": {
        "fingers": "[0, 0, 0, 0, 1]",
        "short": "Chỉ mở ngón Út và nghiêng cổ tay ngang để móc chữ J",
        "detail": "• Giống chữ I (chỉ mở ngón Út), nhưng nghiêng cổ tay sang ngang để ngón Út tạo đường móc chữ J.\n• Mã trạng thái 5 ngón: [0, 0, 0, 0, 1] (ngón út nghiêng ngang).",
        "pose": "pinky_side",
    },
    "K": {
        "fingers": "[1, 1, 1, 0, 0]",
        "short": "Duỗi 3 ngón: Cái, Trỏ và Giữa hướng lên trên (Áp út & Út gập)",
        "detail": "• Duỗi thẳng ngón Trỏ và ngón Giữa tạo hình chữ V, đồng thời mở thẳng cả ngón Cái.\n• Gập 2 ngón Áp út và Út xuống lòng bàn tay.\n• Mã trạng thái 5 ngón: [1, 1, 1, 0, 0].",
        "pose": "three_k",
    },
    "L": {
        "fingers": "[1, 1, 0, 0, 0]",
        "short": "Mở ngón Cái ngang và ngón Trỏ thẳng đứng tạo góc vuông chữ L",
        "detail": "• Duỗi thẳng đứng ngón Trỏ hướng lên trên.\n• Mở ngón Cái hướng ngang tạo góc 90 độ (hình chữ L).\n• Gập kín 3 ngón Giữa, Áp út, Út.\n• Mã trạng thái 5 ngón: [1, 1, 0, 0, 0].",
        "pose": "l_shape",
    },
    "M": {
        "fingers": "[0, 0, 0, 0, 0]",
        "short": "Nắm tay, luồn đầu ngón Cái chạm sát gốc ngón Áp út",
        "detail": "• Gập các ngón tay lại, đưa đầu ngón Cái luồn dưới 3 ngón (Trỏ, Giữa, Áp út) sao cho đầu ngón Cái nằm gần ngón Áp út.\n• Có thể dùng nút 'Lưu mẫu tư thế tay hiện tại' ở dưới để cá nhân hóa chữ M theo tay bạn!",
        "pose": "fist_m",
    },
    "N": {
        "fingers": "[0, 0, 0, 0, 0]",
        "short": "Nắm tay, luồn đầu ngón Cái nằm giữa ngón Giữa và Áp út",
        "detail": "• Gập các ngón tay lại, đưa đầu ngón Cái luồn dưới 2 ngón (Trỏ và Giữa) chạm gần đầu ngón Giữa.\n• Có thể dùng nút 'Lưu mẫu tư thế tay hiện tại' để lưu mẫu chữ N chuẩn theo tay bạn.",
        "pose": "fist_n",
    },
    "O": {
        "fingers": "[0, 0, 0, 0, 0]",
        "short": "Chụm đầu ngón Cái chạm sát đầu ngón Trỏ & Giữa tạo vòng tròn kín chữ O",
        "detail": "• Uốn cong các ngón tay và chụm đầu ngón Cái chạm sát vào đầu ngón Trỏ và ngón Giữa tạo thành hình tròn chữ O.\n• Mã trạng thái 5 ngón: [0, 0, 0, 0, 0] (đầu ngón cái & trỏ chạm nhau).",
        "pose": "o_circle",
    },
    "P": {
        "fingers": "[0, 1, 1, 0, 0]",
        "short": "Duỗi 2 ngón Trỏ & Giữa nhưng chúc mũi ngón tay hướng xuống dưới",
        "detail": "• Mở 2 ngón Trỏ và Giữa, gập Áp út và Út, sau đó chúc bàn tay để 2 ngón Trỏ - Giữa hướng xuống dưới.\n• Mã trạng thái 5 ngón: [_, 1, 1, 0, 0] (hướng xuống).",
        "pose": "p_down",
    },
    "Q": {
        "fingers": "[1, 1, 0, 0, 0]",
        "short": "Mở ngón Cái & ngón Trỏ nhưng chúc 2 đầu ngón hướng xuống dưới",
        "detail": "• Mở ngón Cái và ngón Trỏ (gập 3 ngón cuối), sau đó chúc cổ tay để ngón Cái và Trỏ hướng xuống dưới.\n• Mã trạng thái 5 ngón: [1, 1, 0, 0, 0] (hướng xuống).",
        "pose": "q_down",
    },
    "R": {
        "fingers": "[0, 1, 1, 0, 0]",
        "short": "Duỗi thẳng 2 ngón Trỏ & Giữa đan chéo / ép thật sát vào nhau",
        "detail": "• Duỗi thẳng 2 ngón Trỏ và Giữa hướng lên trên, đồng thời bắt chéo hoặc ép sát 2 đầu ngón Trỏ và Giữa dính liền nhau.\n• Gập ngón Cái, Áp út và Út.\n• Mã trạng thái 5 ngón: [0, 1, 1, 0, 0] (2 đầu ngón sát nhau).",
        "pose": "r_cross",
    },
    "S": {
        "fingers": "[0, 0, 0, 0, 0]",
        "short": "Nắm đấm kín, ngón Cái khóa ngang phía trên mặt ngoài các ngón tay",
        "detail": "• Nắm chặt 4 ngón tay vào lòng bàn tay.\n• Đặt ngón Cái đè ngang lên phía trên đốt giữa của ngón Trỏ và ngón Giữa.\n• Mã trạng thái 5 ngón: [0, 0, 0, 0, 0] (ngón cái đặt cao).",
        "pose": "fist_s",
    },
    "T": {
        "fingers": "[0, 0, 0, 0, 0]",
        "short": "Nắm tay, kẹp đầu ngón Cái vào giữa ngón Trỏ và ngón Giữa",
        "detail": "• Gập 4 ngón tay lại, luồn đầu ngón Cái nhô lên ở khe giữa ngón Trỏ và ngón Giữa.\n• Mã trạng thái 5 ngón: [0, 0, 0, 0, 0].",
        "pose": "fist_t",
    },
    "U": {
        "fingers": "[0, 1, 1, 0, 0]",
        "short": "Duỗi thẳng đứng 2 ngón Trỏ & Giữa song song khép cạnh nhau",
        "detail": "• Duỗi thẳng đứng 2 ngón Trỏ và Giữa song song, đặt sát cạnh nhau (không tách rộng như chữ V).\n• Gập ngón Cái, Áp út và Út.\n• Mã trạng thái 5 ngón: [0, 1, 1, 0, 0] (song song).",
        "pose": "u_parallel",
    },
    "V": {
        "fingers": "[0, 1, 1, 0, 0]",
        "short": "Giơ 2 ngón Trỏ & Giữa tách rộng tạo thành hình chữ V (Victory)",
        "detail": "• Duỗi thẳng 2 ngón Trỏ và Giữa hướng lên trên và tách rộng 2 ngón ra thành hình chữ V.\n• Gập ngón Cái, Áp út và Út.\n• Mã trạng thái 5 ngón: [0, 1, 1, 0, 0] (tách rộng).",
        "pose": "v_peace",
    },
    "W": {
        "fingers": "[0, 1, 1, 1, 0]",
        "short": "Giơ 3 ngón giữa (Trỏ, Giữa, Áp út) xòe hình chữ W; gập Cái & Út",
        "detail": "• Duỗi thẳng 3 ngón: Trỏ, Giữa và Áp út hướng lên trên tạo thành chữ W (hoặc số 3).\n• Gập ngón Cái và ngón Út vào lòng bàn tay.\n• Mã trạng thái 5 ngón: [0, 1, 1, 1, 0].",
        "pose": "w_three",
    },
    "X": {
        "fingers": "[0, 0, 0, 0, 0]",
        "short": "Gập kín 3 ngón cuối, riêng ngón Trỏ nhô cao và cong gập như dấu móc câu",
        "detail": "• Nắm ngón Cái, Giữa, Áp út và Út xuống thấp.\n• Giơ riêng ngón Trỏ lên nhưng uốn cong đốt đầu ngón Trỏ lại giống hình móc câu.\n• Mã trạng thái 5 ngón: [0, 0, 0, 0, 0] (khớp ngón trỏ nhô cao).",
        "pose": "x_hook",
    },
    "Y": {
        "fingers": "[1, 0, 0, 0, 1]",
        "short": "Mở ngón Cái và ngón Út (cử chỉ Shaka / Gọi điện), gập 3 ngón giữa",
        "detail": "• Duỗi rộng ngón Cái sang một bên và ngón Út sang bên đối diện.\n• Gập kín 3 ngón ở giữa (Trỏ, Giữa, Áp út) vào lòng bàn tay.\n• Mã trạng thái 5 ngón: [1, 0, 0, 0, 1].",
        "pose": "y_shaka",
    },
    "Z": {
        "fingers": "[0, 1, 0, 0, 0]",
        "short": "Chỉ mở duy nhất ngón Trỏ và nghiêng chỉ sang bên Phải",
        "detail": "• Chỉ mở ngón Trỏ ([0, 1, 0, 0, 0]), gập 4 ngón còn lại và nghiêng ngón Trỏ chỉ sang phía bên Phải khung hình.",
        "pose": "z_right",
    },
    "SPACE": {
        "fingers": "[1, 1, 1, 1, 1]",
        "short": "Xòe mở cả 5 ngón tay -> Thêm Dấu cách (Khoảng trắng)",
        "detail": "• Xòe thẳng cả 5 ngón tay (Cái, Trỏ, Giữa, Áp út, Út) hướng vào camera để gõ Dấu cách (Space) tách từ.\n• Mã trạng thái 5 ngón: [1, 1, 1, 1, 1].",
        "pose": "open_five",
    },
    "DEL": {
        "fingers": "[0, 1, 0, 0, 0]",
        "short": "Chỉ mở ngón Trỏ và trỏ ngang sang bên Trái -> Xóa 1 ký tự (Backspace)",
        "detail": "• Chỉ mở duy nhất ngón Trỏ ([0, 1, 0, 0, 0]) và chỉ mũi ngón Trỏ sang phía bên Trái màn hình để xóa chữ cái vừa gõ.",
        "pose": "del_left",
    },
}


def render_pose_illustration(pose_type: str, label: str, width: int = 240, height: int = 240) -> np.ndarray:
    """
    Vẽ hình minh họa trực quan 21 khớp xương bàn tay cho từng chữ cái ASL lên ảnh BGR.
    Giúp người dùng nhìn vào là biết ngay ngón nào cần mở (chấm vàng trên đỉnh), ngón nào cần gập.
    """
    # Nền BGR khớp T.INSET (#0a101c -> BGR 28, 16, 10)
    canvas = np.full((height, width, 3), (28, 16, 10), dtype=np.uint8)
    cx, cy = width // 2, int(height * 0.78)

    # Khởi tạo gốc cổ tay (0) và 4 khớp MCP (5, 9, 13, 17)
    kpts = np.zeros((21, 2), dtype=np.float32)
    kpts[0] = [cx, cy]
    kpts[1] = [cx - 26, cy - 18]
    kpts[2] = [cx - 44, cy - 42]
    kpts[5] = [cx - 32, cy - 68]
    kpts[9] = [cx - 10, cy - 74]
    kpts[13] = [cx + 12, cy - 70]
    kpts[17] = [cx + 34, cy - 62]

    info = ASL_GESTURE_GUIDE.get(label, ASL_GESTURE_GUIDE["SPACE"])
    f_str = str(info["fingers"]).strip("[]").split(",")
    fingers = [int(x.strip()) for x in f_str]

    # Ngón cái (3, 4)
    if fingers[0] == 1:
        if pose_type == "thumb_up_side":
            kpts[3] = [cx - 46, cy - 72]
            kpts[4] = [cx - 46, cy - 100]
        elif pose_type in ("q_down",):
            kpts[3] = [cx - 52, cy - 20]
            kpts[4] = [cx - 58, cy + 8]
        else:
            kpts[3] = [cx - 66, cy - 60]
            kpts[4] = [cx - 86, cy - 78]
    else:
        if pose_type == "o_circle":
            kpts[3] = [cx - 42, cy - 72]
            kpts[4] = [cx - 28, cy - 95]
        elif pose_type == "ok_f":
            kpts[3] = [cx - 42, cy - 75]
            kpts[4] = [cx - 30, cy - 96]
        elif pose_type == "fist_s":
            kpts[3] = [cx - 22, cy - 76]
            kpts[4] = [cx + 2, cy - 78]
        else:
            kpts[3] = [cx - 24, cy - 58]
            kpts[4] = [cx - 6, cy - 58]

    # 4 ngón: Trỏ (5-8), Giữa (9-12), Áp (13-16), Út (17-20)
    specs = [
        (5, 6, 7, 8, -32, -8, 1),
        (9, 10, 11, 12, -10, -2, 2),
        (13, 14, 15, 16, 12, 4, 3),
        (17, 18, 19, 20, 34, 12, 4),
    ]
    for mcp, pip, dip, tip, base_dx, spread_dx, f_idx in specs:
        mx, my = kpts[mcp]
        if fingers[f_idx] == 1:
            if pose_type in ("g_horiz", "h_horiz", "del_left"):
                kpts[pip] = [mx - 28, my - 6]
                kpts[dip] = [mx - 54, my - 6]
                kpts[tip] = [mx - 78, my - 6]
            elif pose_type == "z_right":
                kpts[pip] = [mx + 28, my - 6]
                kpts[dip] = [mx + 54, my - 6]
                kpts[tip] = [mx + 78, my - 6]
            elif pose_type == "pinky_side" and f_idx == 4:
                kpts[pip] = [mx + 24, my - 16]
                kpts[dip] = [mx + 46, my - 26]
                kpts[tip] = [mx + 68, my - 34]
            elif pose_type in ("p_down", "q_down"):
                kpts[pip] = [mx, my + 24]
                kpts[dip] = [mx, my + 46]
                kpts[tip] = [mx, my + 68]
            elif pose_type == "u_parallel" and f_idx in (1, 2):
                sx = -18 if f_idx == 1 else -4
                kpts[pip] = [cx + sx, my - 30]
                kpts[dip] = [cx + sx, my - 56]
                kpts[tip] = [cx + sx, my - 80]
            elif pose_type == "r_cross" and f_idx in (1, 2):
                sx = -8 if f_idx == 1 else -14
                kpts[pip] = [cx + sx, my - 30]
                kpts[dip] = [cx - 11, my - 56]
                kpts[tip] = [cx - 11, my - 80]
            elif pose_type == "v_peace" and f_idx in (1, 2):
                sp = -22 if f_idx == 1 else 14
                kpts[pip] = [mx + sp * 0.4, my - 28]
                kpts[dip] = [mx + sp * 0.8, my - 54]
                kpts[tip] = [mx + sp * 1.2, my - 78]
            else:
                kpts[pip] = [mx + spread_dx * 0.4, my - 28]
                kpts[dip] = [mx + spread_dx * 0.8, my - 54]
                kpts[tip] = [mx + spread_dx * 1.2, my - 78]
        else:
            if pose_type == "o_circle" and f_idx in (1, 2):
                kpts[pip] = [mx - 6, my - 34]
                kpts[dip] = [mx - 12, my - 30]
                kpts[tip] = [cx - 26, cy - 95]
            elif pose_type == "ok_f" and f_idx == 1:
                kpts[pip] = [mx - 6, my - 34]
                kpts[dip] = [mx - 10, my - 28]
                kpts[tip] = [cx - 28, cy - 96]
            elif pose_type == "c_curve":
                kpts[pip] = [mx - 4, my - 36]
                kpts[dip] = [mx - 16, my - 46]
                kpts[tip] = [mx - 26, my - 38]
            elif pose_type == "x_hook" and f_idx == 1:
                kpts[pip] = [mx, my - 38]
                kpts[dip] = [mx - 4, my - 46]
                kpts[tip] = [mx - 8, my - 28]
            else:
                kpts[pip] = [mx, my - 16]
                kpts[dip] = [mx, my - 4]
                kpts[tip] = [mx, my + 8]

    colors = [
        (0, 180, 255),
        (0, 255, 120),
        (255, 200, 0),
        (255, 0, 180),
        (80, 80, 255),
    ]
    for idx, (u, v) in enumerate(HAND_SKELETON_CONNECTIONS):
        pt1 = (int(kpts[u][0]), int(kpts[u][1]))
        pt2 = (int(kpts[v][0]), int(kpts[v][1]))
        c = colors[idx // 4] if idx < 20 else (180, 180, 180)
        cv2.line(canvas, pt1, pt2, c, 2, cv2.LINE_AA)

    for i in range(21):
        px, py = int(kpts[i][0]), int(kpts[i][1])
        r = 5 if i in (0, 4, 8, 12, 16, 20) else 3
        fc = (0, 255, 255) if i in (0, 4, 8, 12, 16, 20) else (255, 255, 255)
        cv2.circle(canvas, (px, py), r, fc, -1, cv2.LINE_AA)

    cv2.putText(
        canvas,
        f"Ky hieu: {label}",
        (12, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (248, 189, 56),
        2,
        cv2.LINE_AA,
    )
    return canvas


class ASLGuideDialog(QDialog):
    """
    Cửa sổ tra cứu trực quan toàn bộ Bảng chữ cái Ngôn ngữ Ký hiệu ASL (A-Z + SPACE + DEL)
    kèm sơ đồ 21 điểm khớp xương bàn tay minh họa.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Hướng dẫn cử chỉ bảng chữ cái ASL (A–Z)")
        self.setMinimumSize(780, 560)
        self.resize(920, 660)
        self.setStyleSheet(theme.build_stylesheet())

        root = QHBoxLayout(self)
        root.setContentsMargins(T.SP_4, T.SP_4, T.SP_4, T.SP_4)
        root.setSpacing(T.SP_4)

        # Cột trái: Lưới phím A–Z, SPACE, DEL + bảng tra cứu nhanh
        left_card, left_layout = theme.card(spacing=T.SP_3)
        left_layout.addLayout(
            theme.panel_header(
                "Bảng chữ cái ASL (A–Z)",
                "Bấm phím chữ cái (hoặc gõ trực tiếp trên bàn phím) để xem sơ đồ 21 khớp.",
            )
        )

        grid = QGridLayout()
        grid.setSpacing(T.SP_2)
        self._key_group = QButtonGroup(self)
        self._key_group.setExclusive(True)
        self._key_buttons: Dict[str, QPushButton] = {}
        for idx, k in enumerate(ASL_GESTURE_GUIDE.keys()):
            btn = theme.button(
                k,
                role="key",
                checkable=True,
                tooltip=f"Xem hướng dẫn ký hiệu {k}",
                on_click=lambda letter=k: self.show_letter(letter),
            )
            btn.setAccessibleName(f"Ký hiệu {k}")
            btn.setAutoDefault(False)
            self._key_group.addButton(btn)
            self._key_buttons[k] = btn
            grid.addWidget(btn, idx // 7, idx % 7)
        left_layout.addLayout(grid)

        # Danh sách tra cứu nhanh cuộn được
        list_inset, list_inset_layout = theme.inset(spacing=T.SP_1, margins=(12, 10, 4, 10))
        list_inset_layout.addWidget(theme.caption("Tra nhanh [Cái, Trỏ, Giữa, Áp, Út] · 1 = mở, 0 = gập"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, T.SP_2, 0)
        list_layout.setSpacing(T.SP_1)

        for k, meta in ASL_GESTURE_GUIDE.items():
            row_lbl = theme.label(
                f"<b style='color:{T.ACCENT};'>{k}</b>&nbsp;&nbsp;"
                f"<span style='color:{T.SUCCESS}; font-family:Consolas;'>{meta['fingers']}</span>&nbsp;&nbsp;"
                f"<span style='color:{T.TEXT};'>{meta['short']}</span>",
                role="guide-row",
                wrap=True,
            )
            list_layout.addWidget(row_lbl)
        list_layout.addStretch()

        scroll.setWidget(list_container)
        list_inset_layout.addWidget(scroll, stretch=1)
        left_layout.addWidget(list_inset, stretch=1)
        root.addWidget(left_card, stretch=3)

        # Cột phải: Sơ đồ 21 khớp + hướng dẫn chi tiết từng ngón
        right_card, right_layout = theme.card(spacing=T.SP_3)
        right_layout.addWidget(theme.caption("Chi tiết ký hiệu"))

        self.lbl_letter_title = theme.label("Ký hiệu: A", role="hero", tone="active")
        self.lbl_letter_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.lbl_letter_title)

        self.lbl_diagram = theme.label("", role="diagram")
        self.lbl_diagram.setFixedSize(256, 256)
        self.lbl_diagram.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_diagram.setAccessibleName("Sơ đồ 21 điểm khớp minh họa")
        right_layout.addWidget(self.lbl_diagram, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_fingers_code = theme.pill("[Cái, Trỏ, Giữa, Áp, Út] = [1, 0, 0, 0, 0]", "info")
        self.lbl_fingers_code.setAccessibleName("Mã trạng thái 5 ngón")
        right_layout.addWidget(self.lbl_fingers_code, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_detail_text = theme.label("", role="detail", wrap=True)
        self.lbl_detail_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        right_layout.addWidget(self.lbl_detail_text, stretch=1)

        btn_close = theme.button(
            "Đóng bảng hướng dẫn",
            variant="primary",
            tooltip="Đóng cửa sổ (Esc)",
            on_click=self.accept,
        )
        right_layout.addWidget(btn_close)

        root.addWidget(right_card, stretch=2)
        self.show_letter("A")

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt API)
        key = event.key()
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            self.show_letter(chr(key))
            return
        if key == Qt.Key.Key_Space:
            self.show_letter("SPACE")
            return
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.show_letter("DEL")
            return
        super().keyPressEvent(event)

    def show_letter(self, letter: str) -> None:
        meta = ASL_GESTURE_GUIDE.get(letter, ASL_GESTURE_GUIDE["A"])
        if letter in self._key_buttons:
            btn = self._key_buttons[letter]
            btn.blockSignals(True)
            btn.setChecked(True)
            btn.blockSignals(False)
            btn.setFocus()

        self.lbl_letter_title.setText(f"Ký hiệu: {letter}")
        self.lbl_fingers_code.setText(f"[Cái, Trỏ, Giữa, Áp, Út] = {meta['fingers']}")
        self.lbl_detail_text.setText(f"{meta['short']}\n\n{meta['detail']}")

        bgr = render_pose_illustration(str(meta["pose"]), letter, width=240, height=240)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.lbl_diagram.setPixmap(QPixmap.fromImage(qimg))

