@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0infra\start-local.ps1" %*
set "launcher_exit=%errorlevel%"
if not "%launcher_exit%"=="0" (
  echo.
  echo Khong khoi dong duoc. Xem thong bao loi o tren.
  pause
)
exit /b %launcher_exit%
