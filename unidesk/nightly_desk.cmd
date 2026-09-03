@echo off
rem UniDesk nightly desk refresh (B2-7) — registered as scheduled task
rem "UniDesk-NightlyRefresh" (weekdays ~19:30 local). Absolute venv
rem interpreter: bare `python` fails under Task Scheduler's environment
rem (the likely cause of the manas task's exit 1). All output goes to a
rem dated log via run_scheduled_refresh.py; last result lands in
rem unidesk\last_run.json for /api/health and the UI banner.
cd /d C:\Users\satta\Downloads\koreanguy
C:\Users\satta\Downloads\koreanguy\.venv-orderflow\Scripts\python.exe C:\Users\satta\Downloads\koreanguy\unidesk\run_scheduled_refresh.py
exit /b %ERRORLEVEL%
