@echo off
title LJR.devOS Bot
echo Starting LJR.devOS...

cd /d "%~dp0"

if not exist ".env" (
    echo ERROR: .env file not found. Copy .env and fill credentials.
    pause
    exit /b 1
)

if not exist "google-credentials.json" (
    echo WARNING: google-credentials.json not found. Sheets features will fail.
)

python -m core.telegram_bot

if %ERRORLEVEL% NEQ 0 (
    echo Bot crashed with error %ERRORLEVEL%
    pause
)
