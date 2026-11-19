@echo off
chcp 65001 >nul
cd /d "%~dp0backend"
if not exist .venv\Scripts\activate.bat (
  echo Primero ejecuta instalar.bat
  pause & exit /b 1
)
call .venv\Scripts\activate.bat
echo Arrancando WitchArena en http://127.0.0.1:8000  (cierra esta ventana para pararlo)
start "" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
