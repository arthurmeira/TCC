@echo off
chcp 65001 >nul
cd /d "%~dp0"
title TCC - Gerar historico de demonstracao
echo Este processo executa as 12 consultas de exemplo 730 vezes no total.
echo Pode levar alguns minutos. Os dados das tabelas nao serao alterados.
echo As novas medicoes serao somadas ao historico existente.
echo.
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python nao encontrado. Consulte README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -X utf8 -m scripts.generate_workload
if errorlevel 1 (
  echo.
  echo Nao foi possivel concluir. Confira o erro acima e o servico PostgreSQL.
  pause
  exit /b 1
)
echo.
echo Pronto. Para capturar logs individuais, use Coletar exemplos reais na nova interface.
pause
