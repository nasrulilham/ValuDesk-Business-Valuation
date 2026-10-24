@echo off
setlocal
cd /d "%~dp0"
set "VALUDESK_PORT=8001"
set "PYTHON=python"
where py >nul 2>nul
if %errorlevel%==0 set "PYTHON=py -3"
if not exist .venv\Scripts\python.exe (
    echo Creating Python environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :failed
)
echo Installing required packages...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :failed
echo.
echo ================================================
echo  VALUDESK 2.8.1 - CLASSIC LIGHT PREVIEW
echo  Open http://localhost:8001
echo  Port 8001 avoids an older instance on 8000.
echo ================================================
echo.
.venv\Scripts\python.exe server.py
pause
exit /b 0
:failed
echo Failed to start. Check Python and internet connection.
pause
exit /b 1
