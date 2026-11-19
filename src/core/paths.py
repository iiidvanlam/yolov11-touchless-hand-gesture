import os
from pathlib import Path


PROJECT_ROOT: str = str(Path(__file__).resolve().parents[2])

DEFAULT_YOLO_MODEL_PATH: str = os.path.join(PROJECT_ROOT, "models", "yolo11n_hand_pose_best.pt")
DEFAULT_GESTURE_TASK_PATH: str = os.path.join(PROJECT_ROOT, "models", "gesture_recognizer.task")
DEFAULT_ASL_DB_PATH: str = os.path.join(PROJECT_ROOT, "models", "asl_keypoints_db.npz")
DEFAULT_SCREENSHOTS_DIR: str = os.path.join(PROJECT_ROOT, "screenshots")


def resolve_project_path(path: str) -> str:
    """Resolve a relative path against PROJECT_ROOT while preserving absolute paths."""
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)
