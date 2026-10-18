@echo off
title PDF Split & Merge Studio
cd /d "%~dp0"
echo ===================================================
echo   Lancement de PDF Split & Merge Studio (Hors-ligne)
echo ===================================================
echo.
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Une erreur est survenue lors du lancement.
    pause
)
