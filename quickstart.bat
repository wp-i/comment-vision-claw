@echo off
title Comment-Vision-Claw Installer

echo ========================================
echo   Comment-Vision-Claw Installer
echo ========================================
echo.
echo   This script will install:
echo   - Comment-Vision-Claw project
echo   - MediaCrawler
echo   - All dependencies
echo.
echo   Install location:
echo   - Project: %~dp0comment-vision-claw
echo   - MediaCrawler: %~dp0MediaCrawler
echo.
echo ========================================
echo.
echo Press any key to start installation...
pause >nul

set PROJECT_DIR=%~dp0comment-vision-claw
set MEDIACRAWLER_DIR=%~dp0MediaCrawler

if exist "%PROJECT_DIR%\main.py" (
    echo.
    echo ERROR: Project already exists: %PROJECT_DIR%
    echo Please delete it first if you want to reinstall.
    echo.
    pause
    exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

git --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Git not found. Please install Git.
    echo Download: https://git-scm.com/downloads
    echo.
    pause
    exit /b 1
)

echo.
echo [1/5] Cloning project...
git clone https://github.com/wp-i/comment-vision-claw.git "%PROJECT_DIR%"
if errorlevel 1 (
    echo ERROR: Clone failed. Check your network connection.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"

echo [2/5] Installing dependencies...
pip install -r requirements.txt -q

echo [3/5] Installing MediaCrawler...
if exist "%MEDIACRAWLER_DIR%\main.py" (
    echo MediaCrawler already exists, skipping.
) else (
    git clone https://github.com/NanmiCoder/MediaCrawler.git "%MEDIACRAWLER_DIR%"
    cd /d "%MEDIACRAWLER_DIR%"
    pip install -r requirements.txt -q
    cd /d "%PROJECT_DIR%"
)

echo [4/5] Installing Playwright browser...
playwright install chromium >nul 2>&1

echo [5/5] Done!
echo.
echo ========================================
echo   Installation Complete!
echo   Project: %PROJECT_DIR%
echo   MediaCrawler: %MEDIACRAWLER_DIR%
echo.
echo   To start:
echo   1. Double-click start.bat
echo   2. Or run: streamlit run app.py
echo ========================================
echo.
pause
