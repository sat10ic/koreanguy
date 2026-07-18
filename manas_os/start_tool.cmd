@echo off
rem ManasOS self-hosting supervisor: keeps the tool alive at http://localhost:8000
cd /d C:\Users\satta\Downloads\koreanguy
set PYTHONPATH=C:\Users\satta\Downloads\koreanguy
:loop
python -m uvicorn manas_os.api.app:app --host 127.0.0.1 --port 8000 >> manas_os\data\server.log 2>&1
rem crashed or was stopped -- wait 5s and relaunch with latest code
timeout /t 5 /nobreak >nul
goto loop

