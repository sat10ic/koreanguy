@echo off
setlocal
rem ManasOS self-hosting supervisor: keeps the tool alive at http://localhost:8000.
rem The PID marker prevents a second supervisor loop from replacing the first one.
for %%I in ("%~dp0..") do set "REPO=%%~fI"
set "MANAS_DIR=%~dp0"
set "LOCK_FILE=%~dp0data\start_tool.pid"

if not exist "%~dp0data" mkdir "%~dp0data"
for /f %%P in ('powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID)).ParentProcessId"') do set "SUPERVISOR_PID=%%P"
if not defined SUPERVISOR_PID (
    echo [ManasOS] Could not determine the supervisor PID; refusing an unlocked launch.
    exit /b 1
)

rem Atomically create the PID marker. A live PID means another supervisor owns it;
rem a dead PID is stale and is replaced. FileMode.CreateNew closes the startup race.
powershell.exe -NoProfile -Command "$lock='%LOCK_FILE%'; $owner=0; if (Test-Path -LiteralPath $lock) { $raw=[string](Get-Content -LiteralPath $lock -Raw -ErrorAction SilentlyContinue); $raw=$raw.Trim(); if ([int]::TryParse($raw,[ref]$owner) -and (Get-Process -Id $owner -ErrorAction SilentlyContinue)) { exit 2 }; Remove-Item -LiteralPath $lock -Force -ErrorAction Stop }; try { $stream=[IO.File]::Open($lock,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None); $bytes=[Text.Encoding]::ASCII.GetBytes('%SUPERVISOR_PID%' + [Environment]::NewLine); $stream.Write($bytes,0,$bytes.Length); $stream.Dispose(); exit 0 } catch { if ($stream) { $stream.Dispose() }; $raceOwner=0; $raceRaw=[string](Get-Content -LiteralPath $lock -Raw -ErrorAction SilentlyContinue); if ([int]::TryParse($raceRaw.Trim(),[ref]$raceOwner) -and (Get-Process -Id $raceOwner -ErrorAction SilentlyContinue)) { exit 2 }; exit 1 }"
if errorlevel 2 (
    echo [ManasOS] Another supervisor loop is alive; launch skipped.
    exit /b 0
)
if errorlevel 1 (
    echo [ManasOS] Could not acquire "%LOCK_FILE%"; launch aborted.
    exit /b 1
)

cd /d "%REPO%"
if errorlevel 1 goto prepare_failed

:loop
rem Purge every Python bytecode cache below manas_os before each server launch.
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; Get-ChildItem -LiteralPath '%MANAS_DIR%' -Directory -Filter '__pycache__' -Recurse -Force | Remove-Item -Recurse -Force"
if errorlevel 1 goto prepare_failed

rem Replace only listeners on the API/Vite ports; unrelated ports are untouched.
rem Get-NetTCPConnection is preferred; netstat is the compatibility fallback.
powershell.exe -NoProfile -Command "$ports=8000,5174; function Get-ListenerPids { if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) { return @($ports | ForEach-Object { Get-NetTCPConnection -State Listen -LocalPort $_ -ErrorAction SilentlyContinue } | Select-Object -ExpandProperty OwningProcess -Unique) }; if (-not (Get-Command netstat.exe -ErrorAction SilentlyContinue)) { throw 'Neither Get-NetTCPConnection nor netstat.exe is available' }; $ids=@(); foreach ($line in (netstat.exe -ano -p tcp)) { if ($line -match '^\s*TCP\s+\S+:(8000|5174)\s+\S+\s+LISTENING\s+(\d+)\s*$') { $ids += [int]$Matches[2] } }; return @($ids | Sort-Object -Unique) }; $ownerPids=@(Get-ListenerPids); foreach ($ownerPid in $ownerPids) { if ($ownerPid -gt 0) { Write-Host ('[ManasOS] Stopping listener PID {0}' -f $ownerPid); Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue } }; Start-Sleep -Milliseconds 300; $remaining=@(Get-ListenerPids); if ($remaining.Count) { Write-Error 'A listener remains on port 8000 or 5174'; exit 1 }"
if errorlevel 1 goto prepare_failed

python -m uvicorn manas_os.api.app:app --host 127.0.0.1 --port 8000 >> manas_os\data\server.log 2>&1
rem Crashed or stopped: wait five seconds, then prepare and relaunch latest code.
timeout /t 5 /nobreak >nul
goto loop

:prepare_failed
echo [ManasOS] Pre-launch cleanup failed; server was not started.
del /q "%LOCK_FILE%" >nul 2>&1
exit /b 1
