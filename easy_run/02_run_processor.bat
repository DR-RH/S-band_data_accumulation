@echo off
setlocal

cd /d "%~dp0..\processor"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] processor\.venv was not found.
  echo Run setup for the processor environment first.
  pause
  exit /b 1
)

if not exist "input\unprocessed" (
  mkdir "input\unprocessed"
)

echo Running S-band processor...
echo Input folder: processor\input\unprocessed
echo DB server: http://127.0.0.1:8000
echo.

".venv\Scripts\python.exe" run 

echo.
echo Done. Open the viewer and press Search.
pause

