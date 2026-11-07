@echo off
chcp 65001 >nul
echo ====================================================================
echo  KHOI CHAY UNG DUNG NHAN DIEN NGON NGU KY HIEU VA DIEU KHIEN (YOLOv11-Pose)
echo ====================================================================
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
pause

