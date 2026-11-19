@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist tunel\cloudflared.exe (
  echo Falta tunel\cloudflared.exe. Ejecuta primero descargar_cloudflared.bat
  pause & exit /b 1
)
if not exist backend\.venv\Scripts\activate.bat (
  echo Primero ejecuta instalar.bat
  pause & exit /b 1
)
echo ============================================
echo   WitchArena - publicar en internet (tunel)
echo ============================================
echo Cierra antes la ventana de iniciar.bat si la tienes abierta.
echo.
echo [1/3] Arrancando el servidor en modo publico ...
start "WitchArena - servidor (no cerrar)" cmd /k "set PUBLIC_MODE=1&& cd /d backend && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers"
ping -n 8 127.0.0.1 >nul

echo [2/3] Abriendo el tunel de Cloudflare ...
if exist tunel\tunel.log del tunel\tunel.log
if exist tunel\url.txt del tunel\url.txt
start "WitchArena - tunel (no cerrar)" cmd /k "tunel\cloudflared.exe tunnel --no-autoupdate --url http://127.0.0.1:8000 --logfile tunel\tunel.log"

echo [3/3] Esperando la direccion publica ...
set /a TRIES=0
:wait
ping -n 3 127.0.0.1 >nul
powershell -NoProfile -Command "$m = Select-String -Path 'tunel\tunel.log' -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1; if ($m) { $m.Matches[0].Value | Out-File -Encoding ascii 'tunel\url.txt'; exit 0 } else { exit 1 }"
if not errorlevel 1 goto :done
set /a TRIES+=1
if %TRIES% lss 30 goto :wait
echo [ERROR] No aparece la direccion del tunel. Mira la ventana "WitchArena - tunel".
pause & exit /b 1

:done
echo.
echo ============================================
set /p URL=<tunel\url.txt
echo   WitchArena esta publicada en:
echo   %URL%
echo ============================================
echo La direccion cambia cada vez que se reinicia el tunel.
echo Para pararlo, cierra las ventanas "WitchArena - servidor" y "WitchArena - tunel".
pause
