@echo off
rem F-1 local fast lane — the same three checks CI runs. Install the
rem pre-push hook once with:
rem   git config core.hooksPath .githooks
rem Bypass a slow full suite locally with: git push --no-verify
setlocal
cd /d %~dp0..
echo [verify] 1/3 backend suite (corpus-touching tests self-skip if data/ absent)
.venv-orderflow\Scripts\python.exe -m pytest unidesk\tests -q || goto :fail
echo [verify] 2/3 governance checks
.venv-orderflow\Scripts\python.exe unidesk\run_checks.py || goto :fail
echo [verify] 3/3 frontend build (tsc -b + vite)
cd unidesk_terminal && call npm run build || goto :fail
echo [verify] OK
exit /b 0
:fail
echo [verify] FAILED
exit /b 1
