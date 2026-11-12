@echo off
cd /d "%~dp0"

rem Instala o pynput sozinho na primeira vez (se ainda nao tiver)
python -c "import pynput" 2>nul
if errorlevel 1 (
    echo Instalando o pynput, aguarde...
    python -m pip install pynput
)

rem Abre o app sem deixar a janela preta aberta
start "" pythonw CODIGO.py
exit
