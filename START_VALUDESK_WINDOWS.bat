@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
where py >nul 2>nul
if %errorlevel%==0 set "PYTHON=py -3"
if not exist .venv\Scripts\python.exe (
    echo [1/3] Creating isolated Python environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :failed
)
echo [2/3] Installing required libraries (internet needed on first launch)...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :failed
echo [3/3] Running ValuDesk. Open http://localhost:8000 in your browser.
.venv\Scripts\python.exe server.py
pause
exit /b 0
:failed
echo Installation failed. Check Python 3.10+ and internet connection.
pause
exit /b 1
