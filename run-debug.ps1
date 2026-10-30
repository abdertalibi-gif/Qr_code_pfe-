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
    [string]$Device = "R8YY608FJ8M",
    [int]   $BackendPort = 8000,
    [int]   $WaitSeconds = 120
)

$ErrorActionPreference = "Stop"

$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$mobile  = Join-Path $root "mobile"
$backend = Join-Path $root "backend"

$adb = "C:\Users\Abde\AppData\Local\Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { $adb = "adb" }

$flutter = $null
$cmd = Get-Command flutter -ErrorAction SilentlyContinue
if ($cmd) { $flutter = $cmd.Source }

if (-not $flutter) {
    foreach ($candidate in @(
        "C:\flutter\bin\flutter.bat",
        "C:\src\flutter\bin\flutter.bat",
        "C:\flutter_old\bin\flutter.bat"
    )) {
        if (Test-Path $candidate) { $flutter = $candidate; break }
    }
}

if (-not $flutter) {
    Write-Host "ERREUR: SDK Flutter introuvable." -ForegroundColor Red
    Write-Host "Installe Flutter ou ajoute C:\src\flutter\bin au PATH." -ForegroundColor Yellow
    exit 1
}

$flutterRoot = Split-Path -Parent (Split-Path -Parent $flutter)
$engineFile = Join-Path $flutterRoot "bin\internal\engine.version"
if (Test-Path $engineFile) {
    $env:FLUTTER_PREBUILT_ENGINE_VERSION = (Get-Content $engineFile -Raw).Trim()
}
Write-Host "[0/4] Flutter: $flutter" -ForegroundColor DarkGray

# Un disque plein fait echouer la compilation Dart/Gradle avec des messages
# peu explicites ("Espace insuffisant sur le disque", errno 112).
$freeGb = (Get-PSDrive C).Free / 1GB
if ($freeGb -lt 2) {
    Write-Host ("      ATTENTION: seulement {0:N2} GB libres sur C:." -f $freeGb) -ForegroundColor Red
    Write-Host "      Le build va probablement echouer." -ForegroundColor Red
    Write-Host "      Libere de l'espace (mobile\build, .gradle\caches) puis relance." -ForegroundColor Yellow
} else {
    Write-Host ("      espace disque: {0:N2} GB libres" -f $freeGb) -ForegroundColor DarkGray
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

function Get-DeviceState {
    param([string]$Serial)
    $line = & $adb devices | Select-String -Pattern "^$Serial\s+(\S+)"
    if ($line) { return $line.Matches[0].Groups[1].Value }
    return $null
}

$state = $null
$deadline = (Get-Date).AddSeconds($WaitSeconds)
$restarted = $false
while ((Get-Date) -lt $deadline) {
    $state = Get-DeviceState -Serial $Device
    if ($state -eq "device") { break }

    if ($state -eq "unauthorized") {
        Write-Host "      detecte mais non autorise : accepte la popup sur le telephone" -ForegroundColor Yellow
    } elseif (-not $restarted) {
        # Premier passage sans appareil : on purge le serveur adb une fois.
        & $adb kill-server | Out-Null
        Start-Sleep -Seconds 1
        & $adb start-server | Out-Null
        $restarted = $true
    }
    Start-Sleep -Milliseconds 750
}

if ($state -ne "device") {
    Write-Host "      ERREUR: $Device absent apres $WaitSeconds s." -ForegroundColor Red
    Write-Host "      -> cable direct sans hub, autre port USB, ecran deverrouille," -ForegroundColor Yellow
    Write-Host "         mode USB 'Transfert de fichiers', debogage USB autorise." -ForegroundColor Yellow
    & $adb devices
    exit 1
}

# Limite les deconnexions : ecran maintenu allume, appli exclue de la veille.
& $adb shell svc power stayon true | Out-Null
& $adb shell settings put system screen_off_timeout 1800000 | Out-Null
& $adb shell cmd deviceidle whitelist +com.pfeqr.attendance_app | Out-Null
& $adb shell settings put global app_standby_enabled 0 | Out-Null
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

Push-Location $mobile
try {
    & $flutter run -d $Device --dart-define=DEV_HOST=127.0.0.1
} finally {
    Pop-Location
}
