@echo off
REM Manas Desk launcher — starts the API (:8000) and the desk UI (:5174).
REM Double-click this, then open http://localhost:5174
cd /d "%~dp0"
start "manas-api" cmd /k python run_manas_api.py
cd manas_os\desk
start "manas-desk" cmd /k npm run dev
cd ..\..
echo Both servers starting. Open http://localhost:5174
timeout /t 5 >nul
start http://localhost:5174
