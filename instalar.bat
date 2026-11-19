@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ============================================
echo   WitchArena - instalacion local (Windows)
echo ============================================
echo.

if not exist backend\app\main.py (
  echo [0/4] Descomprimiendo el proyecto ...
  powershell -NoProfile -Command "Expand-Archive -Force -LiteralPath '%~dp0proyecto.zip' -DestinationPath '%~dp0'" || goto :fail
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No encuentro Python. Instala Python 3.10 o superior desde python.org
  echo         y marca "Add python.exe to PATH" durante la instalacion.
  pause & exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo [ERROR] Necesitas Python 3.10 o superior. Tienes:
  python --version
  pause & exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No encuentro Node.js/npm. Instala Node.js LTS desde nodejs.org
  pause & exit /b 1
)

echo [1/4] Creando entorno virtual de Python en backend\.venv ...
if not exist backend\.venv python -m venv backend\.venv || goto :fail
call backend\.venv\Scripts\activate.bat || goto :fail

echo [2/4] Instalando dependencias de Python ...
python -m pip install --upgrade pip >nul
pip install -r backend\requirements.txt || goto :fail

echo [3/4] Frontend ...
if exist frontend\dist\assets\app.js (
  echo       Ya viene compilado, no hace falta npm.
) else (
  pushd frontend
  call npm install || (popd & goto :fail)
  call npm run build || (popd & goto :fail)
  popd
)

echo [4/4] Preparando base de datos y usuarios de prueba ...
pushd backend
python tools\create_test_users.py || (popd & goto :fail)
python -m pytest -q tests 2>nul
popd

echo.
echo Instalacion terminada. Las contrasenas de prueba estan en backend\test_users.txt
echo Ahora ejecuta iniciar.bat
pause
exit /b 0

:fail
echo.
echo [ERROR] Algo ha fallado. Copia el texto de arriba y pasaselo a Claude.
pause
exit /b 1
