<#
.SYNOPSIS
    Démarre Ollama, l'API et l'interface, puis ouvre le navigateur.

.DESCRIPTION
    Au premier démarrage (base vide), le corpus de démonstration est chargé automatiquement.
    Les journaux sont écrits dans storage\logs\. Arrêt : .\stop.cmd

.PARAMETER NoCorpus
    Ne charge pas le corpus de démonstration, même si la base est vide.

.PARAMETER ResetCorpus
    Vide la base de connaissances et recharge le corpus de démonstration.

.PARAMETER NoBrowser
    N'ouvre pas le navigateur.
#>
param(
    [switch]$NoCorpus,
    [switch]$ResetCorpus,
    [switch]$NoBrowser
)

. "$PSScriptRoot\common.ps1"
Set-Location $Root

if (-not (Test-Path $Python)) {
    Write-Fail "Le projet n'est pas installé. Lancez d'abord : .\install.cmd"
    exit 1
}
if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Start-AppProcess($name, $port, $arguments, $readyUrl, [int]$timeout) {
    if (Get-PortProcessId $port) {
        Write-Ok "$name déjà lancé (port $port)"
        return $true
    }
    $log = Join-Path $LogDir "$($name.ToLower()).log"
    $err = Join-Path $LogDir "$($name.ToLower()).err.log"
    Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $Root -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError $err | Out-Null
    if (Wait-Url $readyUrl $timeout) {
        Write-Ok "$name lancé"
        return $true
    }
    Write-Fail "$name ne démarre pas. Journal : $err"
    Get-Content $err -Tail 15 -ErrorAction SilentlyContinue
    return $false
}

Write-Step "Ollama"
if (Start-Ollama) { Write-Ok "Ollama répond" } else {
    Write-Fail "Ollama ne répond pas. Lancez l'application Ollama (ou relancez .\install.cmd)."
    exit 1
}

Write-Step "API (FastAPI)"
$apiArgs = "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"
if (-not (Start-AppProcess "API" 8000 $apiArgs "$ApiUrl/health" 60)) { exit 1 }
$health = Invoke-RestMethod "$ApiUrl/health"
if ($health.ollama.missing) {
    Write-Warn "Modèle(s) manquant(s) : $($health.ollama.missing -join ', '). Lancez .\install.cmd"
}

Write-Step "Base de connaissances"
$summary = Invoke-RestMethod "$ApiUrl/knowledge/summary"
if ($ResetCorpus) {
    & $Python data\load_corpus.py --reset
} elseif ($summary.sources -eq 0 -and -not $NoCorpus) {
    Write-Host "    Base vide : chargement du corpus de démonstration (environ 30 s)…"
    & $Python data\load_corpus.py
} else {
    Write-Ok "$($summary.sources) sources, $($summary.chunks) fragments indexés"
}

Write-Step "Interface (Streamlit)"
$uiArgs = "-m streamlit run frontend\app.py --server.headless true --server.port 8501 --server.address 127.0.0.1"
if (-not (Start-AppProcess "Interface" 8501 $uiArgs $UiUrl 60)) { exit 1 }

Write-Host ""
Write-Host "Application prête : $UiUrl" -ForegroundColor Green
Write-Host "Documentation de l'API : $ApiUrl/docs"
Write-Host "Journaux : $LogDir"
Write-Host "Pour arrêter : .\stop.cmd"
if (-not $NoBrowser) { Start-Process $UiUrl }
