@echo off
setlocal enabledelayedexpansion

REM ATEval desktop automated launcher (Windows)
REM Automates virtual environment setup, package installation, frontend setup,
REM doctor diagnostics, and server launch.

echo ==========================================================
echo               ATEval Desktop Launcher
echo ==========================================================

cd /d "%~dp0"

REM 1. Detect Python 3.11+
set "PYTHON_CMD="

py -3.13 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py -3.13"
    goto :python_found
)

py -3.12 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py -3.12"
    goto :python_found
)

py -3.11 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py -3.11"
    goto :python_found
)

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py -3"
    goto :python_found
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python3"
    goto :python_found
)

echo [ERROR] Python 3.11 or newer was not found.
echo Please install Python 3.11+ from https://www.python.org/ and check "Add python.exe to PATH".
pause
exit /b 1

:python_found
echo [1/5] Using Python: !PYTHON_CMD!

REM 2. Check Node.js / npm
where npm >nul 2>nul
if !errorlevel! neq 0 (
    echo [WARNING] Node.js / npm not found. The packaged frontend will be used when available.
    echo Download from https://nodejs.org/ if frontend needs compilation.
)

REM 3. Virtual Environment Setup
set "VENV_DIR=.venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [2/5] Creating Python virtual environment in %VENV_DIR%...
    !PYTHON_CMD! -m venv "%VENV_DIR%"
) else (
    echo [2/5] Existing virtual environment found.
)

set "VENV_PYTHON=%~dp0%VENV_DIR%\Scripts\python.exe"

REM 4. Install Dependencies
echo [3/5] Installing dependencies...
"%VENV_PYTHON%" -m pip install --upgrade pip --quiet
"%VENV_PYTHON%" -m pip install -e ".[ui-server,writing-docs]" --quiet

REM 5. Build Frontend if missing
if not exist "frontend\dist\client\index.html" if not exist "ateval\static\index.html" (
    where npm >nul 2>nul
    if !errorlevel! equ 0 (
        echo [4/5] Building frontend workspace...
        cd frontend
        call npm ci
        call npm run build
        cd ..
    ) else (
        echo [WARNING] Frontend build directory missing and npm is unavailable.
    )
) else (
    echo [4/5] Frontend production build already exists.
)

REM 6. Run Doctor
echo [5/5] Running ATEval doctor diagnostics...
"%VENV_PYTHON%" -m ateval doctor

REM 7. Start API Server & Launch Browser
set "PORT=%ATEVAL_PORT%"
if "%PORT%"=="" set "PORT=8000"
set "ATEVAL_PORT=%PORT%"

echo.
echo ==========================================================
echo  Starting ATEval workspace at http://127.0.0.1:%PORT%
echo  Press Ctrl+C to terminate the server.
echo ==========================================================
echo.

start "" "http://127.0.0.1:%PORT%"
"%VENV_PYTHON%" -m ateval api
pause
