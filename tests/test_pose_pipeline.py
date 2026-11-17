import unittest
import numpy as np

from src.controllers.air_mouse import AirMouseController, map_to_region
from src.controllers.presentation_controller import PresentationController
from src.controllers.sign_translator import SignLanguageTranslator
from src.core.pose_analyzer import HandPoseAnalyzer
from src.core.smoother import CommandCooldown, VotingBuffer


class TestPosePipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = HandPoseAnalyzer(custom_keypoints_db_path="non_existent.npz")

    @staticmethod
    def _make_open_palm_keypoints() -> np.ndarray:
        """Tạo 21 điểm khớp xương giả lập bàn tay xòe 5 ngón chuẩn."""
        kpts = np.zeros((21, 3), dtype=np.float32)
        kpts[:, 2] = 0.95  # Confidence
        # Cổ tay (0)
        kpts[0, :2] = [300, 400]
        # Ngón cái (1-4) mở sang phải
        kpts[1, :2] = [340, 380]
        kpts[2, :2] = [375, 355]
        kpts[3, :2] = [405, 330]
        kpts[4, :2] = [435, 305]
        # Ngón trỏ (5-8) duỗi thẳng lên
        kpts[5, :2] = [330, 310]
        kpts[6, :2] = [335, 260]
        kpts[7, :2] = [340, 215]
        kpts[8, :2] = [345, 170]
        # Ngón giữa (9-12) duỗi thẳng lên
        kpts[9, :2] = [300, 300]
        kpts[10, :2] = [300, 245]
        kpts[11, :2] = [300, 195]
        kpts[12, :2] = [300, 150]
        # Ngón áp út (13-16) duỗi thẳng lên
        kpts[13, :2] = [270, 310]
        kpts[14, :2] = [265, 260]
        kpts[15, :2] = [260, 215]
        kpts[16, :2] = [255, 175]
        # Ngón út (17-20) duỗi thẳng lên
        kpts[17, :2] = [240, 325]
        kpts[18, :2] = [230, 285]
        kpts[19, :2] = [220, 245]
        kpts[20, :2] = [210, 210]
        return kpts

    def test_open_palm_detection(self) -> None:
        kpts = self._make_open_palm_keypoints()
        res = self.analyzer.analyze((200, 140, 450, 420), kpts, det_conf=0.92)
        self.assertEqual(res.fingers_up, [1, 1, 1, 1, 1])
        self.assertEqual(res.control_gesture, "OPEN_PALM")

    def test_voting_buffer_stabilization(self) -> None:
        buf = VotingBuffer(window_size=5, min_votes=4, min_confidence=0.6)
        for _ in range(3):
            committed, progress, cand = buf.update("A", 0.85)
            self.assertIsNone(committed)
            self.assertEqual(cand, "A")
        committed, progress, _ = buf.update("A", 0.90)
        self.assertEqual(committed, "A")
        self.assertEqual(progress, 1.0)

    def test_sign_translator_and_autocomplete(self) -> None:
        tr = SignLanguageTranslator()
        tr.append_symbol("H")
        tr.append_symbol("E")
        self.assertEqual(tr.text_buffer, "HE")
        suggs = tr.get_word_suggestions()
        self.assertIn("HELLO", suggs)
        tr.apply_suggestion("HELLO")
        self.assertEqual(tr.text_buffer, "HELLO ")

    def test_air_mouse_mapping_and_states(self) -> None:
        nx, ny = map_to_region(320, 210, 640, 480)
        self.assertTrue(0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0)

        kpts = self._make_open_palm_keypoints()
        mouse = AirMouseController()
        mouse._move = lambda x, y: None  # tránh di chuyển chuột thật khi chạy unit test
        mouse._mouse = lambda flag: None
        info1 = mouse.update(kpts, 640, 480, fingers=[1, 1, 1, 1, 1])
        self.assertEqual(info1["state"], "READY")
        info2 = mouse.update(kpts, 640, 480, fingers=[1, 1, 1, 1, 1])
        self.assertEqual(info2["state"], "MOVE")

    def test_presentation_laser_mode(self) -> None:
        kpts = self._make_open_palm_keypoints()
        pres = PresentationController()
        # Chỉ ngón trỏ mở [0, 1, 0, 0, 0] -> chế độ LASER
        res = pres.update(kpts, [0, 1, 0, 0, 0], 640, 480)
        self.assertEqual(res["state"], "LASER")
        self.assertIsNotNone(res["laser"])
    def test_pinch_volume_lock_and_rollback(self) -> None:
        import time as _t
        from src.core.smoother import PinchVolumeLock

        # 1) Yêu cầu đủ entry_frames mới kích hoạt, sau đó giữ yên -> khóa, bỏ qua chuyển động rút tay
        lock = PinchVolumeLock(stable_seconds=0.05, entry_frames=2)
        val, state, _ = lock.update(0.40, pre_pinch_ratio=0.50)
        self.assertIsNone(val)
        self.assertEqual(state, "ARMING")
        val, state, _ = lock.update(0.40, pre_pinch_ratio=0.50)
        self.assertAlmostEqual(val, 0.40)
        self.assertEqual(state, "ADJUST")
        _t.sleep(0.07)
        val, state, _ = lock.update(0.41)
        self.assertEqual(state, "LOCKED")
        val, state, _ = lock.update(0.95)  # rút tay -> ngón tách xa
        self.assertIsNone(val)
        self.assertEqual(state, "LOCKED")

        # 2) Chưa khóa, rút tay làm ratio vọt lên -> khi rời Pinch phải hoàn tác về giá trị cũ
        lock2 = PinchVolumeLock(stable_seconds=5.0, rollback_s=0.05, entry_frames=1, exit_frames=2)
        lock2.update(0.30, pre_pinch_ratio=0.50)
        _t.sleep(0.08)
        lock2.update(0.90)  # động tác rút tay
        self.assertIsNone(lock2.on_not_pinch())
        rb = lock2.on_not_pinch()
        self.assertAlmostEqual(rb, 0.30)

        # 3) Nháy Pinch quá ngắn (< rollback_s) rồi thoát -> hoàn tác về pre_pinch_ratio ban đầu
        lock3 = PinchVolumeLock(stable_seconds=5.0, rollback_s=0.5, entry_frames=2, exit_frames=2)
        lock3.update(0.75, pre_pinch_ratio=0.40)
        lock3.update(0.75, pre_pinch_ratio=0.40)
        self.assertIsNone(lock3.on_not_pinch())
        rb3 = lock3.on_not_pinch()
        self.assertAlmostEqual(rb3, 0.40)

    def test_fist_not_misclassified_as_thumbs_up(self) -> None:
        kpts = np.zeros((21, 3), dtype=np.float32)
        kpts[:, 2] = 0.95
        kpts[0, :2] = [300, 400]
        # Nắm đấm: 4 ngón gập xuống lòng bàn tay, ngón cái đặt cạnh khớp trỏ
        kpts[1, :2] = [335, 375]
        kpts[2, :2] = [355, 345]
        kpts[3, :2] = [350, 320]
        kpts[4, :2] = [330, 305]
        for base_idx, bx in [(5, 330), (9, 300), (13, 270), (17, 240)]:
            kpts[base_idx, :2] = [bx, 310]
            kpts[base_idx + 1, :2] = [bx, 285]
            kpts[base_idx + 2, :2] = [bx, 320]
            kpts[base_idx + 3, :2] = [bx, 355]
        res = self.analyzer.analyze((220, 270, 370, 415), kpts, det_conf=0.92)
        self.assertEqual(res.control_gesture, "FIST")

        # Giơ ngón cái thẳng đứng lên rõ rệt -> THUMBS_UP
        kpts_up = kpts.copy()
        kpts_up[1, :2] = [335, 360]
        kpts_up[2, :2] = [345, 315]
        kpts_up[3, :2] = [348, 265]
        kpts_up[4, :2] = [350, 215]
        res_up = self.analyzer.analyze((220, 200, 370, 415), kpts_up, det_conf=0.92)
        self.assertEqual(res_up.control_gesture, "THUMBS_UP")


if __name__ == "__main__":
    unittest.main()

