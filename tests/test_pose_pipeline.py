import unittest
import numpy as np

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


if __name__ == "__main__":
    unittest.main()

