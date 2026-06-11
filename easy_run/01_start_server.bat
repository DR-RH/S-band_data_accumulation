@echo off
setlocal

cd /d "%~dp0..\server"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] server\.venv was not found.
  echo Run setup for the server environment first.
  pause
  exit /b 1
)

echo Starting S-band DB server...
echo URL: http://127.0.0.1:8000
echo Keep this window open while using the viewer.
echo.

".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

pause

