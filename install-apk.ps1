#requires -Version 5.1
<#
.SYNOPSIS
    Installe et lance l'APK debug deja compile sur le telephone USB, avec
    plusieurs tentatives si le cable USB decroche.

.DESCRIPTION
    Ne reconstruit rien : utilise mobile\build\app\outputs\flutter-apk\app-debug.apk.
    Recree le tunnel adb reverse pour que l'app joigne le backend Django local.

.EXAMPLE
    .\install-apk.ps1
    .\install-apk.ps1 -WaitSeconds 300 -Retries 8
#>
param(
    [string]$Device = "R8YY608FJ8M",
    [int]   $BackendPort = 8000,
    [int]   $WaitSeconds = 180,
    [int]   $Retries = 6
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$apk  = Join-Path $root "mobile\build\app\outputs\flutter-apk\app-debug.apk"

$adb = "C:\Users\Abde\AppData\Local\Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { $adb = "adb" }

if (-not (Test-Path $apk)) {
    Write-Host "ERREUR: APK introuvable : $apk" -ForegroundColor Red
    Write-Host "Lance d'abord : .\run-debug.ps1 (ou flutter build apk --debug)" -ForegroundColor Yellow
    exit 1
}

function Get-DeviceState {
    param([string]$Serial)
    $line = & $adb devices | Select-String -Pattern "^$Serial\s+(\S+)"
    if ($line) { return $line.Matches[0].Groups[1].Value }
    return $null
}

function Wait-Device {
    param([int]$Seconds)
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        $state = Get-DeviceState -Serial $Device
        if ($state -eq "device") { return $true }
        if ($state -eq "unauthorized") {
            Write-Host "  telephone non autorise : accepte la popup sur l'ecran" -ForegroundColor Yellow
        }
        Start-Sleep -Milliseconds 750
    }
    return $false
}

Write-Host "[1/3] Attente du telephone ($Device)..." -ForegroundColor Cyan
& $adb start-server | Out-Null
if (-not (Wait-Device -Seconds $WaitSeconds)) {
    Write-Host "  ERREUR: telephone absent." -ForegroundColor Red
    Write-Host "  -> cable direct (sans hub), autre port USB, ecran deverrouille," -ForegroundColor Yellow
    Write-Host "     mode USB 'Transfert de fichiers', debogage USB autorise." -ForegroundColor Yellow
    exit 1
}
Write-Host "  connecte" -ForegroundColor Green

Write-Host "[2/3] Tunnel USB -> backend" -ForegroundColor Cyan
& $adb reverse "tcp:$BackendPort" "tcp:$BackendPort" | Out-Null
Write-Host "  tcp:$BackendPort ok" -ForegroundColor Green

Write-Host "[3/3] Installation de l'APK" -ForegroundColor Cyan
$installed = $false
for ($i = 1; $i -le $Retries; $i++) {
    Write-Host "  tentative $i/$Retries..." -ForegroundColor DarkGray
    $output = & $adb install -r $apk 2>&1
    if ($LASTEXITCODE -eq 0 -and ($output -match "Success")) {
        $installed = $true
        break
    }
    Write-Host "  echec : $($output | Select-Object -Last 1)" -ForegroundColor Yellow
    if (-not (Wait-Device -Seconds 60)) {
        Write-Host "  telephone toujours absent, nouvelle attente..." -ForegroundColor Yellow
        if (-not (Wait-Device -Seconds $WaitSeconds)) { break }
    }
}

if (-not $installed) {
    Write-Host "ERREUR: installation impossible (cable/USB instable)." -ForegroundColor Red
    exit 1
}

& $adb reverse "tcp:$BackendPort" "tcp:$BackendPort" | Out-Null
& $adb shell am start -n com.pfeqr.attendance_app/.MainActivity | Out-Null
Start-Sleep -Seconds 3

$pidApp = & $adb shell pidof com.pfeqr.attendance_app
if ($pidApp) {
    Write-Host "OK: application lancee (PID $pidApp)" -ForegroundColor Green
} else {
    Write-Host "APK installee, mais l'app ne repond pas encore (verifie l'ecran)." -ForegroundColor Yellow
}
