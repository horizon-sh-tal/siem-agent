# SIEM Agent – Windows Service Installer
# Run as Administrator

param(
    [string]$InstallDir = "C:\SIEMAgent\windows"
)

$ErrorActionPreference = "Stop"

$ServiceName  = "SIEMAgentWindows"
$DisplayName  = "SIEM Agent – Windows Log Collector"
$PythonExe    = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "C:\Python39\python.exe" }
$MainScript   = "$InstallDir\agent\main.py"

Write-Host "==> SIEM Agent Windows Installer" -ForegroundColor Cyan

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Please run as Administrator" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Recurse -Force "agent\"      "$InstallDir\"
Copy-Item -Recurse -Force "keys\"       "$InstallDir\"
New-Item  -ItemType Directory -Force -Path "$InstallDir\logs" | Out-Null
Copy-Item -Force "config.json"  "$InstallDir\"
Copy-Item -Recurse -Force "..\common\" "$InstallDir\..\common\" -ErrorAction SilentlyContinue

Write-Host "==> Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Host "==> Installing NSSM..." -ForegroundColor Yellow
    choco install nssm -y
}

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    nssm stop   $ServiceName confirm 2>$null
    nssm remove $ServiceName confirm
}

nssm install $ServiceName $PythonExe $MainScript
nssm set $ServiceName AppDirectory  $InstallDir
nssm set $ServiceName DisplayName   $DisplayName
nssm set $ServiceName Description   "SIEM Agent – collects Windows Event Logs and ships them encrypted to Kafka"
nssm set $ServiceName Start         SERVICE_AUTO_START
nssm set $ServiceName AppExit       Default Restart
nssm set $ServiceName AppRestartDelay 10000
nssm set $ServiceName AppStdout     "$InstallDir\logs\service_stdout.log"
nssm set $ServiceName AppStderr     "$InstallDir\logs\service_stderr.log"
nssm set $ServiceName ObjectName    LocalSystem

icacls "$InstallDir\keys"        /inheritance:r /grant "SYSTEM:(OI)(CI)F" /T | Out-Null
icacls "$InstallDir\config.json" /inheritance:r /grant "SYSTEM:F"          | Out-Null

nssm start $ServiceName
Start-Sleep -Seconds 3
$status = nssm status $ServiceName

if ($status -eq "SERVICE_RUNNING") {
    Write-Host "==> SIEM Agent installed and running!" -ForegroundColor Green
} else {
    Write-Host "==> Service status: $status – check logs at $InstallDir\logs" -ForegroundColor Yellow
}
