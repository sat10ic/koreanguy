@echo off
rem Diagnostic wrapper: run the supervisor with all output captured, in a
rem console this cmd owns (children die when a borrowed console closes).
call "%~dp0start_tool.cmd" > "%~dp0data\logs\start_tool_run.log" 2>&1
echo exited %ERRORLEVEL% >> "%~dp0data\logs\start_tool_run.log"
