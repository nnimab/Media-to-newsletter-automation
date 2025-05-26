@echo off
echo 正在啟動電子報文章生成工具...
echo.

REM 檢查虛擬環境是否存在
if not exist "venv\Scripts\activate.bat" (
    echo 錯誤：找不到虛擬環境，請先運行 setup.bat 創建環境
    pause
    exit /b 1
)

REM 激活虛擬環境並運行主程式
call venv\Scripts\activate.bat
echo 虛擬環境已激活
echo 正在啟動 GUI 介面...
echo.

python main_gui.py

REM 如果程式異常退出，暫停以查看錯誤訊息
if errorlevel 1 (
    echo.
    echo 程式執行時發生錯誤，請檢查上方的錯誤訊息
    pause
) 