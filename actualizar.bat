@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Actualizando WitchArena...
powershell -NoProfile -Command "Expand-Archive -Force -LiteralPath '%~dp0actualizacion.zip' -DestinationPath '%~dp0'" || goto :fail
call backend\.venv\Scripts\activate.bat || goto :fail
pushd backend
python -m pytest -q tests || (popd & goto :fail)
popd
echo.
echo Actualizacion terminada. Ahora ejecuta iniciar.bat
pause
exit /b 0
:fail
echo [ERROR] Algo ha fallado. Pasale este texto a Claude.
pause
exit /b 1
