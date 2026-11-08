@echo off
chcp 65001 >nul
cd /d "%~dp0"
title TCC - Logs e otimizacao SQL
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python nao encontrado. Consulte README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -X utf8 -m src.webapp --port 8767 --open
if errorlevel 1 pause
