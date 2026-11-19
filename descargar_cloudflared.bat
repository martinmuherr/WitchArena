@echo off
chcp 65001 >nul
cd /d "%~dp0"
set CF_VERSION=2026.11.1
echo Descargando cloudflared %CF_VERSION% (Cloudflare Tunnel, version portable sin instalar)
echo Origen: https://github.com/cloudflare/cloudflared/releases/tag/%CF_VERSION%
if not exist tunel mkdir tunel
curl.exe -L --fail --progress-bar -o tunel\cloudflared.exe https://github.com/cloudflare/cloudflared/releases/download/%CF_VERSION%/cloudflared-windows-amd64.exe || goto :fail
for %%A in (tunel\cloudflared.exe) do echo Tamano: %%~zA bytes
certutil -hashfile tunel\cloudflared.exe SHA256
tunel\cloudflared.exe --version || goto :fail
echo.
echo Descarga correcta. Ahora puedes ejecutar publicar.bat
pause
exit /b 0
:fail
echo [ERROR] No se pudo descargar o ejecutar cloudflared. Pasale este texto a Claude.
pause
exit /b 1
