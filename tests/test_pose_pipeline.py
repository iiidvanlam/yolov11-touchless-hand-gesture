import importlib.util
import os
import sys
import tempfile
import threading
import types
import unittest
import warnings
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
import numpy as np

from src.controllers.air_mouse import AirMouseController, MOUSEEVENTF_LEFTDOWN, map_to_region
from src.controllers.media_controller import WindowsMediaController
from src.controllers.presentation_controller import PresentationController
from src.controllers.sign_translator import SignLanguageTranslator
from src.core.detector import YoloPoseHandDetector
from src.core.paths import (
    DEFAULT_ASL_DB_PATH,
    DEFAULT_GESTURE_TASK_PATH,
    DEFAULT_SCREENSHOTS_DIR,
    DEFAULT_YOLO_MODEL_PATH,
    PROJECT_ROOT,
)
from src.core.pose_analyzer import HandPoseAnalyzer
from src.core.smoother import CommandCooldown, OneEuroKeypointSmoother, VotingBuffer


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

    def test_presentation_open_palm_swipe_and_grace(self) -> None:
        from src.controllers.presentation_controller import VK_LEFT, VK_RIGHT

        pressed = []
        pres = PresentationController(swipe_dist_ratio=0.14, cooldown_s=0.15, grace_frames=4)
        pres._press = lambda vk: pressed.append(vk)

        base = self._make_open_palm_keypoints()
        # Vẫy tay xòe sang TRÁI (x giảm từ 300 -> 200), xen kẽ 1 frame mất dấu để kiểm tra grace_frames
        for idx, shift_x in enumerate([80, 40, None, -30]):
            if shift_x is None:
                pres.on_no_hand()
                continue
            k = base.copy()
            k[:, 0] += shift_x
            res = pres.update(k, [1, 1, 1, 1, 1], 640, 480)
        self.assertEqual(res["event"], "Slide tiếp theo ▶")
        self.assertEqual(pressed, [VK_RIGHT])

        # Trong thời gian cooldown, hồi tay sang PHẢI không được kích hoạt Slide trước
        for shift_x in [-30, 30, 100]:
            k = base.copy()
            k[:, 0] += shift_x
            r_cd = pres.update(k, [1, 1, 1, 1, 1], 640, 480)
            self.assertIsNone(r_cd["event"])

        # Hết cooldown, vẫy xòe tay sang PHẢI (x tăng từ 200 -> 350) -> Slide trước
        import time as _t
        _t.sleep(0.18)
        events2 = []
        for shift_x in [-100, -50, 0, 50]:
            k = base.copy()
            k[:, 0] += shift_x
            res2 = pres.update(k, [1, 1, 1, 1, 1], 640, 480)
            if res2["event"]:
                events2.append(res2["event"])
        self.assertEqual(events2, ["◀ Slide trước"])
        self.assertEqual(pressed, [VK_RIGHT, VK_LEFT])
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

    def test_nan_and_inf_keypoints_rejected_cleanly(self) -> None:
        nan_kpts = np.full((21, 3), np.nan, dtype=np.float32)
        self.assertFalse(self.analyzer.is_valid_hand_skeleton((10, 10, 100, 100), nan_kpts))
        res_nan = self.analyzer.analyze((10, 10, 100, 100), nan_kpts, det_conf=0.9)
        self.assertEqual(res_nan.asl_label, "NOTHING")
        self.assertEqual(res_nan.control_gesture, "NONE")

        inf_kpts = self._make_open_palm_keypoints()
        inf_kpts[8, 0] = np.inf
        self.assertFalse(self.analyzer.is_valid_hand_skeleton((200, 140, 450, 420), inf_kpts))

        nan_conf_kpts = self._make_open_palm_keypoints()
        nan_conf_kpts[0, 2] = np.nan
        self.assertFalse(self.analyzer.is_valid_hand_skeleton((200, 140, 450, 420), nan_conf_kpts))

    def test_post_smoothing_invalid_skeleton_rejected_without_ghost(self) -> None:
        det = YoloPoseHandDetector.__new__(YoloPoseHandDetector)
        det.model = None
        det.mp_recognizer = object()
        det.device = "cpu"
        det.model_loaded_name = "mock"
        det.conf_threshold = 0.55
        det.iou_threshold = 0.45
        det.analyzer = HandPoseAnalyzer(custom_keypoints_db_path="non_existent.npz")
        det.kpt_smoother = OneEuroKeypointSmoother()
        det.last_raw_kpts = None
        det._prev_bbox = None
        det._pool = ThreadPoolExecutor(max_workers=2)
        det._last_yolo_warn_t = 0.0
        det._last_mp_warn_t = 0.0

        valid_kpts = self._make_open_palm_keypoints()
        bbox = (200, 140, 450, 420)
        collapsed_kpts = np.zeros((21, 3), dtype=np.float32)
        collapsed_kpts[:, 2] = 0.95
        collapsed_kpts[:, :2] = [300.0, 300.0]

        det._run_yolo = lambda frame: (bbox, valid_kpts, 0.9)
        det._mp_recognize_roi = lambda rgb, b=None: (valid_kpts, bbox, "Open_Palm", 0.9)
        det.kpt_smoother.update = lambda k: collapsed_kpts

        try:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            _, analyses = det.detect(frame)
            self.assertEqual(analyses, [])
            self.assertIsNone(det._prev_bbox)
            self.assertIsNone(det.last_raw_kpts)
        finally:
            det.close()

    def test_mp_recognize_roi_handles_exceptions_and_onnx_missing(self) -> None:
        det = YoloPoseHandDetector.__new__(YoloPoseHandDetector)
        det.model = None
        det.mp_recognizer = mock.Mock()
        det.mp_recognizer.recognize.side_effect = RuntimeError("MP failure")
        det.device = "cpu"
        det.use_gpu = False
        det.model_loaded_name = "mock"
        det._last_mp_warn_t = 0.0
        det._last_yolo_warn_t = 0.0
        det._pool = ThreadPoolExecutor(max_workers=1)

        try:
            rgb = np.zeros((240, 320, 3), dtype=np.uint8)
            res = det._mp_recognize_roi(rgb, (20, 20, 180, 180))
            self.assertEqual(res, (None, None, None, 0.0))

            with mock.patch("src.core.detector.importlib.util.find_spec", return_value=None):
                ok = det.load_model("fake_model.onnx")
            self.assertFalse(ok)
            self.assertIn("onnxruntime", det.model_loaded_name.lower())
        finally:
            det.close()

    def test_air_mouse_pinch_near_knuckle_does_not_trigger_clutch(self) -> None:
        kpts = self._make_open_palm_keypoints()
        # Đưa đầu ngón trỏ (8) và ngón cái (4) chụm sát gần mức khớp đốt gốc (5)
        knuckle = kpts[5, :2].copy()
        kpts[4, :2] = knuckle + np.array([2.0, -4.0], dtype=np.float32)
        kpts[8, :2] = knuckle + np.array([3.0, -5.0], dtype=np.float32)

        events = []
        mouse = AirMouseController()
        mouse._move = lambda x, y: None
        mouse._mouse = lambda flag: events.append(flag)

        info1 = mouse.update(kpts, 640, 480, fingers=[1, 0, 0, 0, 0])
        self.assertEqual(info1["state"], "READY")
        info2 = mouse.update(kpts, 640, 480, fingers=[1, 0, 0, 0, 0])
        self.assertEqual(info2["state"], "LEFT_DOWN")
        self.assertIn(MOUSEEVENTF_LEFTDOWN, events)

    def test_map_to_region_zero_width_height_guard(self) -> None:
        nx, ny = map_to_region(320, 240, 640, 480, region=(0.5, 0.5, 0.5, 0.5))
        self.assertTrue(0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0)

    def test_command_cooldown_initial_trigger_near_t0(self) -> None:
        cd = CommandCooldown(required_hold_frames=2)
        t_vals = iter([0.2, 0.3, 0.4])
        with mock.patch("src.core.smoother.time.perf_counter", side_effect=lambda: next(t_vals)):
            trig1, _ = cd.check_trigger("OPEN_PALM")
            self.assertFalse(trig1)
            trig2, prog2 = cd.check_trigger("OPEN_PALM")
            self.assertTrue(trig2)
            self.assertEqual(prog2, 1.0)
            trig3, _ = cd.check_trigger("OPEN_PALM")
            self.assertFalse(trig3)

    def test_pose_analyzer_thread_safe_reload_and_clean_l_pose(self) -> None:
        # Tạo tư thế chữ 'L' chuẩn: Ngón cái mở ngang, Ngón trỏ thẳng đứng, 3 ngón còn lại gập
        kpts_l = np.zeros((21, 3), dtype=np.float32)
        kpts_l[:, 2] = 0.95
        kpts_l[0, :2] = [300, 400]
        kpts_l[1, :2] = [335, 385]
        kpts_l[2, :2] = [375, 375]
        kpts_l[3, :2] = [415, 370]
        kpts_l[4, :2] = [455, 368]
        kpts_l[5, :2] = [310, 310]
        kpts_l[6, :2] = [310, 260]
        kpts_l[7, :2] = [310, 215]
        kpts_l[8, :2] = [310, 170]
        for base_idx, bx in [(9, 285), (13, 260), (17, 235)]:
            kpts_l[base_idx, :2] = [bx, 315]
            kpts_l[base_idx + 1, :2] = [bx, 295]
            kpts_l[base_idx + 2, :2] = [bx, 330]
            kpts_l[base_idx + 3, :2] = [bx, 360]

        default_analyzer = HandPoseAnalyzer()
        res_l = default_analyzer.analyze((220, 150, 470, 420), kpts_l, det_conf=0.95)
        self.assertEqual(res_l.fingers_up, [1, 1, 0, 0, 0])
        self.assertEqual(res_l.asl_label, "L")

        # Kiểm tra đồng bộ đa luồng giữa reload_custom_samples và classify_asl_letter
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_db.npz")
            feat = HandPoseAnalyzer.extract_normalized_features(kpts_l)
            np.savez_compressed(
                db_path,
                features=np.array([feat], dtype=np.float32),
                labels=np.array(["L"], dtype="<U16"),
            )
            concurrent_analyzer = HandPoseAnalyzer(custom_keypoints_db_path=db_path)
            errors = []

            def writer():
                try:
                    for i in range(40):
                        n = 1 if i % 2 == 0 else 5
                        np.savez_compressed(
                            db_path,
                            features=np.tile(feat, (n, 1)).astype(np.float32),
                            labels=np.array(["L"] * n, dtype="<U16"),
                        )
                        concurrent_analyzer.reload_custom_samples()
                except Exception as exc:
                    errors.append(exc)

            def reader():
                try:
                    for _ in range(80):
                        lbl, _ = concurrent_analyzer.classify_asl_letter(kpts_l, [1, 1, 0, 0, 0])
                        self.assertEqual(lbl, "L")
                except Exception as exc:
                    errors.append(exc)

            t1 = threading.Thread(target=writer)
            t2 = threading.Thread(target=reader)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            self.assertEqual(errors, [])

    def test_sign_translator_com_uninitialized_on_dispatch_error(self) -> None:
        fake_pythoncom = types.SimpleNamespace(
            CoInitialize=mock.Mock(),
            CoUninitialize=mock.Mock(),
        )
        fake_win32_client = types.SimpleNamespace(
            Dispatch=mock.Mock(side_effect=RuntimeError("No SAPI voice"))
        )
        fake_win32com = types.SimpleNamespace(client=fake_win32_client)
        fake_pyttsx3 = types.SimpleNamespace(init=mock.Mock(side_effect=RuntimeError("No pyttsx3")))

        tr = SignLanguageTranslator()
        with mock.patch.dict(
            sys.modules,
            {
                "pythoncom": fake_pythoncom,
                "win32com": fake_win32com,
                "win32com.client": fake_win32_client,
                "pyttsx3": fake_pyttsx3,
            },
        ):
            tr._speak_worker("HELLO")

        fake_pythoncom.CoInitialize.assert_called_once()
        fake_pythoncom.CoUninitialize.assert_called_once()

    def test_cwd_independent_default_paths(self) -> None:
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                self.assertTrue(os.path.isabs(PROJECT_ROOT))
                self.assertTrue(os.path.exists(DEFAULT_YOLO_MODEL_PATH))
                self.assertTrue(os.path.exists(DEFAULT_GESTURE_TASK_PATH))
                self.assertTrue(os.path.exists(DEFAULT_ASL_DB_PATH))
                self.assertEqual(
                    os.path.normpath(WindowsMediaController().screenshot_dir),
                    os.path.normpath(DEFAULT_SCREENSHOTS_DIR),
                )
                analyzer = HandPoseAnalyzer()
                self.assertEqual(
                    os.path.normpath(analyzer.custom_keypoints_db_path),
                    os.path.normpath(DEFAULT_ASL_DB_PATH),
                )
            finally:
                os.chdir(old_cwd)

    def test_collect_pose_data_exits_promptly_without_camera(self) -> None:
        import scripts.collect_pose_data as collect_script

        fake_cap = mock.Mock()
        fake_cap.isOpened.return_value = False
        fake_det = mock.Mock()

        with mock.patch.object(collect_script, "YoloPoseHandDetector", return_value=fake_det), mock.patch.object(
            collect_script.cv2, "VideoCapture", return_value=fake_cap
        ):
            collect_script.main()

        fake_cap.release.assert_called_once()
        fake_det.close.assert_called_once()

    def test_concurrent_save_reload_and_classify_preserves_all_samples(self) -> None:
        kpts_l = np.zeros((21, 3), dtype=np.float32)
        kpts_l[:, 2] = 0.95
        kpts_l[0, :2] = [300, 400]
        kpts_l[1, :2] = [335, 385]
        kpts_l[2, :2] = [375, 375]
        kpts_l[3, :2] = [415, 370]
        kpts_l[4, :2] = [455, 368]
        kpts_l[5, :2] = [310, 310]
        kpts_l[6, :2] = [310, 260]
        kpts_l[7, :2] = [310, 215]
        kpts_l[8, :2] = [310, 170]
        for base_idx, bx in [(9, 285), (13, 260), (17, 235)]:
            kpts_l[base_idx, :2] = [bx, 315]
            kpts_l[base_idx + 1, :2] = [bx, 295]
            kpts_l[base_idx + 2, :2] = [bx, 330]
            kpts_l[base_idx + 3, :2] = [bx, 360]

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "concurrent_db.npz")
            analyzer = HandPoseAnalyzer(custom_keypoints_db_path=db_path)

            for trial in range(10):
                feat = HandPoseAnalyzer.extract_normalized_features(kpts_l)
                np.savez_compressed(
                    db_path,
                    features=np.array([feat], dtype=np.float32),
                    labels=np.array(["L"], dtype="<U16"),
                )
                analyzer.reload_custom_samples()

                errors = []
                barrier = threading.Barrier(4)

                def writer_save():
                    try:
                        barrier.wait()
                        for _ in range(8):
                            analyzer.save_custom_sample(kpts_l, "L")
                    except Exception as exc:
                        errors.append(exc)

                def writer_reload():
                    try:
                        barrier.wait()
                        for _ in range(20):
                            analyzer.reload_custom_samples()
                            self.assertIsNotNone(analyzer.sample_features)
                    except Exception as exc:
                        errors.append(exc)

                def reader_classify():
                    try:
                        barrier.wait()
                        for _ in range(40):
                            lbl, _ = analyzer.classify_asl_letter(kpts_l, [1, 1, 0, 0, 0])
                            self.assertEqual(lbl, "L")
                    except Exception as exc:
                        errors.append(exc)

                threads = [
                    threading.Thread(target=writer_save),
                    threading.Thread(target=writer_reload),
                    threading.Thread(target=reader_classify),
                    threading.Thread(target=reader_classify),
                ]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                self.assertEqual(errors, [], f"Trial {trial} failed: {errors}")
                self.assertIsNotNone(analyzer.sample_features)
                self.assertEqual(len(analyzer.sample_features), 9, f"Lost samples in trial {trial}")

            # Transient corrupt file on disk must not wipe already-loaded valid in-memory state
            with open(db_path, "wb") as f:
                f.write(b"corrupted-zip-header")
            analyzer.reload_custom_samples()
            self.assertIsNotNone(analyzer.sample_features)
            self.assertEqual(len(analyzer.sample_features), 9)

    def test_invalid_shapes_and_non_finite_rejected_cleanly(self) -> None:
        bad_inputs = [
            np.empty((0, 3), dtype=np.float32),
            np.empty((0, 0), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            np.zeros((21,), dtype=np.float32),
            np.zeros((17, 3), dtype=np.float32),
            np.zeros((20, 3), dtype=np.float32),
            np.zeros((21, 1), dtype=np.float32),
            np.zeros((1, 21, 3), dtype=np.float32),
            np.full((21, 3), np.nan, dtype=np.float32),
        ]
        inf_kpts = self._make_open_palm_keypoints()
        inf_kpts[4, 1] = np.inf
        nan_xy = self._make_open_palm_keypoints()
        nan_xy[8, 0] = np.nan
        bad_inputs.extend([inf_kpts, nan_xy])

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "reject_db.npz")
            analyzer = HandPoseAnalyzer(custom_keypoints_db_path=db_path)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", RuntimeWarning)
                for bad in bad_inputs:
                    with self.assertRaises(ValueError):
                        analyzer.extract_normalized_features(bad)
                    with self.assertRaises(ValueError):
                        analyzer.get_finger_states(bad)
                    with self.assertRaises(ValueError):
                        analyzer.save_custom_sample(bad, "A")
                runtime_warns = [w for w in caught if issubclass(w.category, RuntimeWarning)]
                self.assertEqual(runtime_warns, [])
            self.assertFalse(os.path.exists(db_path))

    def test_is_valid_hand_skeleton_rejects_collinear_and_degenerate_bbox_allows_tilted(self) -> None:
        valid = self._make_open_palm_keypoints()
        # Inverted and zero-area bounding boxes must be rejected
        self.assertFalse(self.analyzer.is_valid_hand_skeleton((450, 420, 200, 140), valid))
        self.assertFalse(self.analyzer.is_valid_hand_skeleton((300, 300, 300, 300), valid))
        self.assertFalse(self.analyzer.is_valid_hand_skeleton((np.nan, 0, 100, 100), valid))

        # Strictly 1D collinear (21, 3) skeleton must be rejected
        collinear = np.zeros((21, 3), dtype=np.float32)
        collinear[:, 0] = 100.0 + np.arange(21) * 10.0
        collinear[:, 1] = 100.0 + np.arange(21) * 10.0
        collinear[:, 2] = 0.95
        self.assertFalse(self.analyzer.is_valid_hand_skeleton((90, 90, 320, 320), collinear))
        res_col = self.analyzer.analyze((90, 90, 320, 320), collinear, det_conf=0.95)
        self.assertEqual(res_col.asl_label, "NOTHING")
        self.assertEqual(res_col.control_gesture, "NONE")

        # Genuine tilted hand (narrowed palm angle ~12 deg) must still pass
        tilted = valid.copy()
        tilted[:, 0] = 300.0 + (valid[:, 0] - 300.0) * 0.25
        self.assertTrue(self.analyzer.is_valid_hand_skeleton((260, 140, 350, 420), tilted))

    def test_save_current_keypoint_sample_handles_uncreatable_db_parent_dir(self) -> None:
        from src.ui.app_window import SignAndGestureApp

        with tempfile.TemporaryDirectory() as tmpdir:
            blocker_file = os.path.join(tmpdir, "not_a_dir")
            with open(blocker_file, "wb") as f:
                f.write(b"blocker")
            uncreatable_db = os.path.join(blocker_file, "sub", "db.npz")

            analyzer = HandPoseAnalyzer(custom_keypoints_db_path=uncreatable_db)
            win = SignAndGestureApp.__new__(SignAndGestureApp)
            win.last_analyses = [types.SimpleNamespace(keypoints=self._make_open_palm_keypoints())]
            win.combo_calib_letter = types.SimpleNamespace(currentText=lambda: "A")
            win.detector = types.SimpleNamespace(analyzer=analyzer)

            with mock.patch("src.ui.app_window.QMessageBox.warning") as mock_warn, mock.patch(
                "src.ui.app_window.QMessageBox.information"
            ) as mock_info:
                win._save_current_keypoint_sample()

            mock_warn.assert_called_once()
            mock_info.assert_not_called()
            self.assertFalse(os.path.exists(uncreatable_db))
            self.assertIsNone(analyzer.sample_features)

    def test_collect_pose_data_handles_oserror_on_atomic_save(self) -> None:
        import io
        from contextlib import redirect_stdout
        import scripts.collect_pose_data as collect_script

        kpts = self._make_open_palm_keypoints()
        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        fake_cap = mock.Mock()
        fake_cap.isOpened.return_value = True
        fake_cap.read.return_value = (True, fake_frame)

        fake_det = mock.Mock()
        fake_det.detect.return_value = (
            fake_frame.copy(),
            [types.SimpleNamespace(keypoints=kpts)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = os.path.join(tmpdir, "models")
            os.makedirs(models_dir, exist_ok=True)
            keys = iter([ord("C"), 27])
            buf = io.StringIO()

            with mock.patch.object(collect_script, "PROJECT_ROOT", tmpdir), mock.patch.object(
                collect_script, "YoloPoseHandDetector", return_value=fake_det
            ), mock.patch.object(
                collect_script.cv2, "VideoCapture", return_value=fake_cap
            ), mock.patch.object(
                collect_script.cv2, "imshow"
            ), mock.patch.object(
                collect_script.cv2, "destroyAllWindows"
            ), mock.patch.object(
                collect_script.cv2, "waitKey", side_effect=lambda _: next(keys)
            ), mock.patch.object(
                collect_script.os, "replace", side_effect=PermissionError("Access denied")
            ), redirect_stdout(
                buf
            ):
                collect_script.main()

            out = buf.getvalue()
            self.assertIn("[LỖI]", out)
            self.assertNotIn("[HOÀN TẤT]", out)
            leftovers = [f for f in os.listdir(models_dir) if f.startswith(".tmp_asl_db_")]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()

