@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Comment-Vision-Claw

chcp 65001 >nul 2>&1

rem Always run from the script directory
pushd "%~dp0"

rem Basic checks
python --version >nul 2>&1 || goto :python_missing
if not exist "app.py" goto :missing_files
if not exist "engine" goto :missing_files
python -c "import streamlit" >nul 2>&1 || goto :streamlit_missing
python -c "from engine.mediacrawler_scraper import check_mediacrawler_installed; raise SystemExit(0 if check_mediacrawler_installed() else 1)" >nul 2>&1 || goto :crawler_missing

echo [init] Cleaning previous data...
python -c "from engine.cleanup import clear_app_data; clear_app_data()" >nul 2>&1

echo [init] Stopping stale Streamlit process on port 8501...
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8501" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo [init] Starting web app...
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$url='http://localhost:8501'; for($i=0; $i -lt 120; $i++){ Start-Sleep 1; try{ $r=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3; if($r.StatusCode -eq 200){ Start-Process $url; break } }catch{} }"

python -m streamlit run app.py --server.headless=true --server.port=8501
if errorlevel 1 goto :streamlit_failed

goto :cleanup

:python_missing
echo ERROR: Python not found. Install Python 3.10+ and add it to PATH.
goto :fail

:missing_files
echo ERROR: Project files missing. Make sure this script is in the project root.
goto :fail

:streamlit_missing
echo ERROR: Streamlit is not installed. Run: pip install -r requirements.txt
goto :fail

:crawler_missing
echo ERROR: MediaCrawler is not installed. Please install it first.
goto :fail

:streamlit_failed
echo ERROR: Streamlit exited with an error. Check the console above for details.
goto :fail

:fail
pause

:cleanup
popd
endlocal
