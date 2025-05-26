@echo off
echo 電子報文章生成工具 - 環境設置腳本
echo =====================================
echo.

REM 檢查 Python 是否已安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo 錯誤：未找到 Python，請先安裝 Python 3.8 或更高版本
    echo 下載地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 檢測到 Python 版本：
python --version
echo.

REM 檢查虛擬環境是否已存在
if exist "venv" (
    echo 虛擬環境已存在，是否要重新創建？ (y/N)
    set /p choice=
    if /i "%choice%"=="y" (
        echo 正在刪除舊的虛擬環境...
        rmdir /s /q venv
    ) else (
        echo 使用現有虛擬環境
        goto install_deps
    )
)

echo 正在創建虛擬環境...
python -m venv venv
if errorlevel 1 (
    echo 錯誤：創建虛擬環境失敗
    pause
    exit /b 1
)

:install_deps
echo 正在激活虛擬環境...
call venv\Scripts\activate.bat

echo 正在安裝依賴庫...
pip install -r requirements.txt
if errorlevel 1 (
    echo 錯誤：安裝依賴失敗
    pause
    exit /b 1
)

echo.
echo =====================================
echo 設置完成！
echo.
echo 使用方法：
echo 1. 雙擊 start.bat 啟動程式
echo 2. 或手動執行：
echo    - call venv\Scripts\activate.bat
echo    - python main_gui.py
echo.
echo 首次使用請記得在設定中配置 API 金鑰和路徑
echo =====================================
pause 