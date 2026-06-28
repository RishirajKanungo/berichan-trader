@echo off
REM ===================================================================
REM  Berichan Trader - click-to-run launcher (run from source)
REM
REM  Use this if Windows Smart App Control blocks the .exe. Just
REM  double-click this file. The FIRST run sets things up automatically
REM  (a few minutes); after that it opens quickly.
REM ===================================================================
setlocal
cd /d "%~dp0"
title Berichan Trader

REM --- 1. Find Python -------------------------------------------------
set "PY="
where py >nul 2>&1 && set "PY=py"
if not defined PY ( where python >nul 2>&1 && set "PY=python" )

if not defined PY (
    echo.
    echo  Python is required but was not found on this PC.
    echo  Opening the Python download page in your browser...
    echo.
    echo  IMPORTANT: during install, tick "Add Python to PATH",
    echo  then run this launcher again.
    echo.
    start "" https://www.python.org/downloads/
    pause
    exit /b 1
)

REM --- 2. First-run setup: isolated environment + dependencies --------
if not exist ".venv\Scripts\pythonw.exe" (
    echo.
    echo  First-time setup - installing the app. This can take a few
    echo  minutes and only happens once. Please wait...
    echo.
    %PY% -m venv .venv
    if errorlevel 1 ( echo Failed to create environment. & pause & exit /b 1 )
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 ( echo Failed to install dependencies. & pause & exit /b 1 )
    echo.
    echo  Setup complete!
)

REM --- 3. Launch the app (no console window) --------------------------
start "" ".venv\Scripts\pythonw.exe" -m berichan.gui
exit /b 0
