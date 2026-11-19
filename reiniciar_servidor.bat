@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Reiniciando SOLO el servidor de WitchArena (el tunel y su direccion se mantienen)...
taskkill /FI "WINDOWTITLE eq WitchArena - servidor*" /T /F >nul 2>nul
ping -n 3 127.0.0.1 >nul
start "WitchArena - servidor (no cerrar)" cmd /k "set PUBLIC_MODE=1&& cd /d backend && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers"
ping -n 8 127.0.0.1 >nul
if exist tunel\url.txt (
  set /p URL=<tunel\url.txt
  call echo Listo. La web sigue en: %%URL%%
) else (
  echo Listo.
)
pause
