@echo off
REM Abre Triaje Varicela sin ventana de consola (usa pythonw del entorno virtual).
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo No se encontro el entorno virtual. Primero ejecuta:
    echo     powershell -ExecutionPolicy Bypass -File instalar.ps1
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m app
