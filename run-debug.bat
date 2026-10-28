@echo off
REM Lance l'app Flutter en debug sur le telephone USB.
REM Double-clic possible, ou : run-debug.bat -Device R8YY608FJ8M
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-debug.ps1" %*
echo.
echo --- Session terminee (code %ERRORLEVEL%) ---
pause
