@echo off
title DEVA - Game Dev Voice Assistant
cd /d C:\Projects\TheDavidProject 2>nul || cd /d C:\Projects\Clawdbot

echo ============================================
echo   DEVA - Developer Expert Virtual Assistant
echo ============================================
echo.

:: Activate venv
call venv\Scripts\activate.bat

:: Launch DEVA
echo Starting DEVA...
echo Say "quit" or press Ctrl+C to exit.
echo.
python voice/deva_voice.py

pause
