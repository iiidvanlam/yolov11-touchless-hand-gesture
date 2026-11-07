@echo off
chcp 65001 >nul
echo ====================================================================
echo  HUAN LUYEN TIEP YOLOv11-POSE (21 KEYPOINTS) TREN GPU RTX 4050
echo ====================================================================
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\train_yolov11_pose_gpu.py" --model models/yolo11n_hand_pose_best.pt --dataset "%~dp0data\hand_pose_local.yaml" --epochs 20 --fraction 0.25 --batch 4 --imgsz 512 --freeze 0 --workers 0
pause
