@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0.."

set "BASE_PY=py -3"
%BASE_PY% --version >nul 2>&1
if errorlevel 1 (
  set "BASE_PY=python"
  %BASE_PY% --version >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python was not found.
    echo Install Python 3.11 or make sure python/py is on PATH.
    pause
    exit /b 1
  )
)

echo Initial setup for S-band tools
echo Root: %ROOT%
echo Python:
%BASE_PY% --version
echo.

call :setup_env processor
if errorlevel 1 goto :failed

call :setup_env server
if errorlevel 1 goto :failed

call :setup_env downloader
if errorlevel 1 goto :failed

call :setup_env decoder_core
if errorlevel 1 goto :failed

echo.
echo [OK] Setup completed.
echo Next steps:
echo   1. Put TLM .txt files into the TLM input alias.
echo   2. Run 01_start_server.bat.
echo   3. Run 02_run_processor.bat.
echo   4. Open downloader\index.html or run 03_open_viewer.bat.
pause
exit /b 0

:setup_env
set "APP=%~1"
set "APP_DIR=%ROOT%\%APP%"
set "VENV_PY=%APP_DIR%\.venv\Scripts\python.exe"
set "REQ=%APP_DIR%\requirements.txt"

echo ------------------------------------------------------------
echo [%APP%]

if not exist "%APP_DIR%" (
  echo [ERROR] Folder not found: %APP_DIR%
  exit /b 1
)

if not exist "%REQ%" (
  echo [ERROR] requirements.txt not found: %REQ%
  exit /b 1
)

if not exist "%VENV_PY%" (
  echo Creating venv...
  pushd "%APP_DIR%" >nul
  %BASE_PY% -m venv .venv
  if errorlevel 1 (
    popd >nul
    echo [ERROR] Failed to create venv for %APP%.
    exit /b 1
  )
  popd >nul
) else (
  echo venv already exists.
)

echo Installing requirements...
"%VENV_PY%" -m pip install -r "%REQ%"
if errorlevel 1 (
  echo [ERROR] Failed to install requirements for %APP%.
  exit /b 1
)

echo [OK] %APP%
exit /b 0

:failed
echo.
echo [ERROR] Setup failed.
pause
exit /b 1

