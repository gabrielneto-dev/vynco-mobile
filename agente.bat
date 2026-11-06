@echo off
rem Abre o menu do Agente de Conteudo. Pode ser executado com duplo clique ou de qualquer pasta.
title Agente de Conteudo - Loja de iPhones
chcp 65001 >nul
set PYTHONUTF8=1

rem Sempre roda a partir da pasta do projeto (onde este .bat esta).
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  Ambiente .venv nao encontrado nesta pasta.
    echo  Crie com:  python -m venv .venv  ^&^&  .venv\Scripts\python.exe -m pip install -e ".[dev]"
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m agente %*

rem Se der erro, mantem a janela aberta para ler a mensagem.
if errorlevel 1 (
    echo.
    pause
)
