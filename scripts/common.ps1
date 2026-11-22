# Fonctions partagées par les scripts (chargé avec : . "$PSScriptRoot\common.ps1")
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$LogDir = Join-Path $Root "storage\logs"
$ApiUrl = "http://127.0.0.1:8000"
$UiUrl = "http://127.0.0.1:8501"
$OllamaUrl = "http://127.0.0.1:11434"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

function Write-Step($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Write-Ok($text) { Write-Host "    OK  $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "    !   $text" -ForegroundColor Yellow }
function Write-Fail($text) { Write-Host "    X   $text" -ForegroundColor Red }

function Test-Url($url, [int]$timeoutSec = 3) {
    try {
        Invoke-RestMethod -Uri $url -TimeoutSec $timeoutSec -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-Url($url, [int]$seconds = 60) {
    for ($i = 0; $i -lt $seconds; $i++) {
        if (Test-Url $url) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Get-OllamaExe {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $default = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $default) { return $default }
    return $null
}

function Start-Ollama {
    if (Test-Url "$OllamaUrl/api/version") { return $true }
    $exe = Get-OllamaExe
    if (-not $exe) { return $false }
    $app = Join-Path (Split-Path $exe) "ollama app.exe"
    if (Test-Path $app) {
        Start-Process -FilePath $app | Out-Null
    } else {
        Start-Process -FilePath $exe -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    }
    return (Wait-Url "$OllamaUrl/api/version" 30)
}

function Get-PortProcessId([int]$port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) { return $conn.OwningProcess }
    return $null
}

function Stop-Port([int]$port, $name) {
    $procId = Get-PortProcessId $port
    if ($procId) {
        Stop-Process -Id $procId -Force -Confirm:$false -ErrorAction SilentlyContinue
        Write-Ok "$name arrêté (port $port)"
    } else {
        Write-Ok "$name n'était pas lancé"
    }
}

function Get-EnvValue($key) {
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) { return $null }
    $line = Get-Content $envFile | Where-Object { $_ -match "^\s*$key\s*=" } | Select-Object -First 1
    if ($line) { return ($line -split "=", 2)[1].Trim() }
    return $null
}

function Set-EnvValue($key, $value) {
    $envFile = Join-Path $Root ".env"
    $lines = @(Get-Content $envFile)
    $found = $false
    $lines = $lines | ForEach-Object {
        if ($_ -match "^\s*#?\s*$key\s*=") { $found = $true; "$key=$value" } else { $_ }
    }
    if (-not $found) { $lines += "$key=$value" }
    # UTF-8 sans BOM (un BOM fausserait la lecture de la première variable par Python)
    [System.IO.File]::WriteAllLines($envFile, [string[]]$lines)
}
