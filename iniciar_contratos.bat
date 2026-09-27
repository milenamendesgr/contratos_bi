@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo Execute instalar.bat antes de iniciar o projeto.
    pause
    exit /b 1
)
echo Contratos disponivel em http://localhost:8516
".venv\Scripts\python.exe" -m streamlit run main.py
if errorlevel 1 pause
