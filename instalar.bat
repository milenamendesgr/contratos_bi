@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
if not errorlevel 1 goto dependencias
py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv .venv
    goto verificar
)
python -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
if errorlevel 1 (
    echo Instale Python 3.10 ou superior com a opcao Add Python to PATH.
    pause
    exit /b 1
)
python -m venv .venv
:verificar
if not exist ".venv\Scripts\python.exe" (
    echo Nao foi possivel criar o ambiente Python.
    pause
    exit /b 1
)
:dependencias
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Falha na instalacao das dependencias.
    pause
    exit /b 1
)
echo Instalacao concluida. Execute iniciar_contratos.bat.
pause
