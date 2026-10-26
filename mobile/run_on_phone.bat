@echo off
setlocal
REM Run the Flutter app on a USB-connected Android phone.
REM Backend must be running on the PC at http://127.0.0.1:8010
REM The USB tunnel maps phone localhost:8000 -> PC localhost:8010.

set "PATH=C:\Program Files\Git\cmd;%PATH%"
set "ADB=%LOCALAPPDATA%\Android\sdk\platform-tools\adb.exe"
set "FLUTTER=C:\flutter\bin\flutter.bat"

if not exist "%ADB%" (
  echo [ERREUR] adb introuvable : %ADB%
  exit /b 1
)
if not exist "%FLUTTER%" (
  echo [ERREUR] Flutter introuvable : %FLUTTER%
  exit /b 1
)

set "DEVICE="
for /f "skip=1 tokens=1,2" %%a in ('"%ADB%" devices') do (
  if "%%b"=="device" set "DEVICE=%%a"
)

if "%DEVICE%"=="" (
  echo [ERREUR] Aucun telephone Android detecte.
  echo Active le debogage USB et accepte l'autorisation sur le telephone.
  exit /b 1
)

echo Telephone detecte : %DEVICE%
echo Configuration du tunnel USB 8000 -^> 8010...
"%ADB%" reverse tcp:8000 tcp:8010
if errorlevel 1 (
  echo [ERREUR] Impossible de configurer adb reverse.
  exit /b 1
)

cd /d "%~dp0"
echo Lancement de l'application...
"%FLUTTER%" run -d %DEVICE% --dart-define=DEV_HOST=127.0.0.1

endlocal
