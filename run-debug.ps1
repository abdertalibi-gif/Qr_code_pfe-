#requires -Version 5.1
<#
.SYNOPSIS
    Lance l'app Flutter en mode debug sur le telephone Android branche en USB.

.DESCRIPTION
    1. Demarre le backend Django s'il n'ecoute pas deja sur le port 8000.
    2. Verifie que le telephone est visible par adb (USB).
    3. Cree le tunnel adb reverse (le telephone joint 127.0.0.1:8000 sur le PC).
    4. Lance flutter run en debug sur le telephone.

.EXAMPLE
    .\run-debug.ps1
    .\run-debug.ps1 -Device R8YY608FJ8M
#>
param(
    [string]$Device =  "R8YY608FJ8M",
    [int]   $BackendPort = 8000
)

$ErrorActionPreference = "Stop"

$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$mobile  = Join-Path $root "mobile"
$backend = Join-Path $root "backend"

$adb = "C:\Users\Abde\AppData\Local\Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { $adb = "adb" }

$flutter = "flutter"
if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
    $flutter = "C:\flutter\bin\flutter.bat"
}

function Test-LocalPort {
    param([int]$Port)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect("127.0.0.1", $Port)
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

Write-Host "[1/4] Backend Django (port $BackendPort)" -ForegroundColor Cyan
if (Test-LocalPort -Port $BackendPort) {
    Write-Host "      deja actif, rien a faire" -ForegroundColor DarkGray
} else {
    $python = Join-Path $backend "venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        Write-Host "      ERREUR: venv introuvable ($python)" -ForegroundColor Red
        exit 1
    }
    Start-Process -FilePath $python `
        -ArgumentList "manage.py", "runserver", "0.0.0.0:$BackendPort", "--noreload" `
        -WorkingDirectory $backend
    for ($i = 0; $i -lt 30 -and -not (Test-LocalPort -Port $BackendPort); $i++) {
        Start-Sleep -Milliseconds 500
    }
    if (Test-LocalPort -Port $BackendPort) {
        Write-Host "      demarre (fenetre separee)" -ForegroundColor Green
    } else {
        Write-Host "      ERREUR: backend injoignable sur le port $BackendPort" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[2/4] Telephone USB" -ForegroundColor Cyan
& $adb start-server | Out-Null
$connected = $false
for ($i = 0; $i -lt 20; $i++) {
    if (& $adb devices | Select-String -Pattern "^$Device\s+device$") {
        $connected = $true
        break
    }
    Start-Sleep -Milliseconds 500
}

if (-not $connected) {
    Write-Host "      ERREUR: $Device non detecte." -ForegroundColor Red
    Write-Host "      -> branche le cable, deverrouille l'ecran," -ForegroundColor Yellow
    Write-Host "         puis accepte 'Autoriser le debogage USB'." -ForegroundColor Yellow
    Write-Host "      Etat adb actuel:" -ForegroundColor Yellow
    & $adb devices
    exit 1
}

& $adb shell svc power stayon usb | Out-Null
Write-Host "      connecte ($Device)" -ForegroundColor Green

Write-Host "[3/4] Tunnel USB -> backend (adb reverse)" -ForegroundColor Cyan
& $adb reverse "tcp:$BackendPort" "tcp:$BackendPort" | Out-Null
if (& $adb reverse --list | Select-String -Pattern "tcp:$BackendPort") {
    Write-Host "      ok : tcp:$BackendPort -> tcp:$BackendPort" -ForegroundColor Green
} else {
    Write-Host "      ERREUR: adb reverse a echoue (essaie de rebrancher le cable)" -ForegroundColor Red
    exit 1
}

Write-Host "[4/4] flutter run --debug sur $Device" -ForegroundColor Cyan
$env:FLUTTER_PREBUILT_ENGINE_VERSION = (Get-Content "C:\flutter\bin\internal\engine.version").Trim()

Push-Location $mobile
try {
    & $flutter run -d $Device --dart-define=DEV_HOST=127.0.0.1
} finally {
    Pop-Location
}
