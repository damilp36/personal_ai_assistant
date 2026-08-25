@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel% equ 0 (
  set "PYTHON_COMMAND=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    start "" "https://www.python.org/downloads/windows/"
    echo Python is needed. Install Python, then open this file again.
    pause
    exit /b 1
  )
  set "PYTHON_COMMAND=python"
)

if not exist ".venv\Scripts\python.exe" (
  %PYTHON_COMMAND% -m venv .venv
  if errorlevel 1 (
    echo The private Python environment could not be created.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo The required packages could not be installed.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" desktop_launcher.py
if errorlevel 1 pause

