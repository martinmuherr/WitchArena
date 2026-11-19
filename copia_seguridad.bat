@echo off
chcp 65001 >nul
cd /d "%~dp0"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmm"') do set STAMP=%%i
set "DEST=%~dp0..\HS_WitchArena_copia_%STAMP%"
echo Copiando WitchArena a:
echo   %DEST%
echo (sin el entorno de Python .venv, que se recrea con instalar.bat)
robocopy "%~dp0." "%DEST%" /E /XD .venv node_modules __pycache__ .pytest_cache /R:1 /W:1 /NFL /NDL /NP
if %ERRORLEVEL% GEQ 8 (
  echo [ERROR] La copia ha fallado.
  pause & exit /b 1
)
echo.
echo Copia terminada. Para volver a esta version: cierra el servidor, copia el contenido de
echo esa carpeta encima de HS_WitchArena y ejecuta reiniciar_servidor.bat
pause
