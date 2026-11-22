<#
.SYNOPSIS
    Installe et configure le projet (à lancer une fois après le clone, ou après une mise à jour).

.DESCRIPTION
    1. Vérifie Python (3.11 ou plus récent)
    2. Vérifie Ollama et propose de l'installer avec winget
    3. Crée l'environnement virtuel .venv et installe les dépendances
    4. Crée le fichier .env à partir de .env.example
    5. Télécharge les modèles (gemma3:4b ≈ 3,3 Go, embeddinggemma ≈ 620 Mo)
    6. Teste le modèle d'embeddings et passe en mode processeur si la carte graphique pose problème
    7. Lance les tests

.PARAMETER CpuOnly
    Force l'exécution des modèles sur le processeur (OLLAMA_NUM_GPU=0).

.PARAMETER SkipModels
    Ne télécharge pas les modèles Ollama.

.EXAMPLE
    .\install.cmd
    powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -CpuOnly
#>
param(
    [switch]$CpuOnly,
    [switch]$SkipModels
)

. "$PSScriptRoot\common.ps1"
Set-Location $Root
Write-Host "Installation de l'Assistant documentaire RAG" -ForegroundColor White
Write-Host "Dossier : $Root"

# --- 1. Python ------------------------------------------------------------------
Write-Step "Python"
$pythonCmd = $null
foreach ($candidate in @(@("py", "-3"), @("python"))) {
    $exe = $candidate[0]
    $prefix = @($candidate | Select-Object -Skip 1)
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
    try {
        $version = & $exe @prefix -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
    } catch { continue }
    if ($version -and [version]$version -ge [version]"3.11") {
        $pythonCmd = $candidate
        Write-Ok "Python $version ($($candidate -join ' '))"
        break
    }
}
if (-not $pythonCmd) {
    Write-Fail "Python 3.11 ou plus récent est introuvable."
    Write-Host "    Installez-le depuis https://www.python.org/downloads/ (cochez « Add python.exe to PATH »)"
    Write-Host "    ou : winget install Python.Python.3.12"
    exit 1
}

# --- 2. Ollama ------------------------------------------------------------------
Write-Step "Ollama"
if (-not (Get-OllamaExe)) {
    Write-Warn "Ollama n'est pas installé."
    $answer = Read-Host "    L'installer maintenant avec winget ? (O/n)"
    if ($answer -eq "" -or $answer -match "^[oOyY]") {
        winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    }
    if (-not (Get-OllamaExe)) {
        Write-Fail "Ollama est requis : https://ollama.com/download puis relancez ce script."
        exit 1
    }
}
if (Start-Ollama) {
    $version = (Invoke-RestMethod "$OllamaUrl/api/version").version
    Write-Ok "Ollama $version lancé"
} else {
    Write-Fail "Ollama est installé mais ne répond pas sur $OllamaUrl. Lancez l'application Ollama puis relancez ce script."
    exit 1
}

# --- 3. Environnement Python -------------------------------------------------------
Write-Step "Environnement Python (.venv)"
if (-not (Test-Path $Python)) {
    $exe = $pythonCmd[0]
    $prefix = @($pythonCmd | Select-Object -Skip 1)
    & $exe @prefix -m venv $Venv
    Write-Ok "Environnement créé"
} else {
    Write-Ok "Environnement existant réutilisé"
}
& $Python -m pip install --quiet --upgrade pip
& $Python -m pip install --quiet -r backend\requirements.txt -r frontend\requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Fail "Échec de l'installation des dépendances"; exit 1 }
Write-Ok "Dépendances installées"

# --- 4. Configuration ----------------------------------------------------------------
Write-Step "Configuration (.env)"
if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
    Write-Ok ".env créé à partir de .env.example"
} else {
    Write-Ok ".env existant conservé"
}
if ($CpuOnly) {
    Set-EnvValue "OLLAMA_NUM_GPU" "0"
    Write-Ok "Mode processeur forcé (OLLAMA_NUM_GPU=0)"
}

# --- 5. Modèles -------------------------------------------------------------------------
$ollama = Get-OllamaExe
$llm = Get-EnvValue "LLM_MODEL"; if (-not $llm) { $llm = "gemma3:4b" }
$embedding = Get-EnvValue "EMBEDDING_MODEL"; if (-not $embedding) { $embedding = "embeddinggemma" }
if (-not $SkipModels) {
    Write-Step "Modèles Ollama ($llm, $embedding)"
    Write-Host "    Premier téléchargement : environ 4 Go, cela peut être long."
    foreach ($model in @($embedding, $llm)) {
        & $ollama pull $model
        if ($LASTEXITCODE -ne 0) { Write-Fail "Téléchargement de $model impossible"; exit 1 }
        Write-Ok "$model disponible"
    }
}

# --- 6. Test du modèle d'embeddings (et repli sur le processeur) -------------------------------
Write-Step "Test des modèles"
function Test-Embedding($numGpu) {
    $body = @{ model = $embedding; input = @("test"); keep_alive = 0 }
    if ($null -ne $numGpu) { $body.options = @{ num_gpu = $numGpu } }
    try {
        Invoke-RestMethod -Method Post -Uri "$OllamaUrl/api/embed" -Body ($body | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 180 | Out-Null
        return $true
    } catch { return $false }
}
$numGpu = Get-EnvValue "OLLAMA_NUM_GPU"
if ($numGpu -ne "0" -and -not (Test-Embedding $null)) {
    Write-Warn "Le modèle ne se charge pas sur la carte graphique : passage en mode processeur."
    Set-EnvValue "OLLAMA_NUM_GPU" "0"
    $numGpu = "0"
}
if (Test-Embedding $(if ($numGpu -eq "0") { 0 } else { $null })) {
    if ($numGpu -eq "0") { Write-Ok "Embeddings OK (processeur)" } else { Write-Ok "Embeddings OK" }
} else {
    Write-Fail "Le modèle d'embeddings ne répond pas. Consultez le journal d'Ollama : $env:LOCALAPPDATA\Ollama\server.log"
    exit 1
}

# --- 7. Tests -----------------------------------------------------------------------------
Write-Step "Tests automatiques"
Push-Location backend
& $Python -m pytest -q -p no:warnings
$testsOk = $LASTEXITCODE -eq 0
Pop-Location
if ($testsOk) { Write-Ok "Tests réussis" } else { Write-Warn "Des tests échouent (voir ci-dessus)" }

Write-Host ""
Write-Host "Installation terminée. Pour démarrer : .\start.cmd" -ForegroundColor Green
