@echo off
title LJR.devOS Bot
echo.
echo ============================================================
echo  LJR.devOS — Pre-flight checks
echo ============================================================
echo.

cd /d "%~dp0"

:: Check .env exists
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo.
    echo Fix: Copy .env.example to .env and fill in your credentials.
    echo.
    pause
    exit /b 1
)

:: Check TELEGRAM_TOKEN is filled in
findstr /r "^TELEGRAM_TOKEN=.\+" .env >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] TELEGRAM_TOKEN is empty in .env
    echo.
    echo Fix:
    echo   1. Message @BotFather on Telegram
    echo   2. Send /revoke to revoke the old token
    echo   3. Send /newbot or /mybots to get a new token
    echo   4. Paste it into .env as: TELEGRAM_TOKEN=your_token_here
    echo.
    pause
    exit /b 1
)

:: Check google-credentials.json exists
if not exist "google-credentials.json" (
    echo [WARNING] google-credentials.json not found in current folder.
    echo.
    echo Fix:
    echo   Option A: Copy from Tempo repo:
    echo             copy ..\tempo\careeros\google-credentials.json .
    echo   Option B: Download from Google Cloud Console:
    echo             console.cloud.google.com ^> IAM ^> Service Accounts
    echo             ^> careeros-bot ^> Keys ^> Add Key ^> JSON
    echo.
    echo Sheets features will be unavailable. Continuing anyway...
    echo.
    goto :start_bot
)

:: Seed Google Sheets data on first launch only
:: seed_data.py skips import if PROFILE tab already has >= 40 rows
echo [SEED] Checking if Sheets need initial data...
python scripts/seed_data.py
echo.

:start_bot
echo [OK] Pre-flight passed. Starting bot...
echo.

python -m core.telegram_bot

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Bot crashed with exit code %ERRORLEVEL%
    echo Check the error above. Common fixes:
    echo   - pip install -r requirements.txt
    echo   - Check TELEGRAM_TOKEN in .env
    echo   - Check GROQ_API_KEY in .env
    echo.
    pause
)
