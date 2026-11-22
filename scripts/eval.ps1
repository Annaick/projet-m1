<#
.SYNOPSIS
    Lance le banc d'évaluation (eval\run_eval.py).

.DESCRIPTION
    Qdrant en mode local n'accepte qu'un processus à la fois : l'API est arrêtée pendant l'évaluation,
    puis relancée à la fin si elle tournait. Les arguments sont transmis au script Python.

.EXAMPLE
    .\scripts\eval.ps1 --retrieval-only
    .\scripts\eval.ps1 --configs rag --limit 5
#>
. "$PSScriptRoot\common.ps1"
Set-Location $Root

if (-not (Test-Path $Python)) { Write-Fail "Lancez d'abord : .\install.cmd"; exit 1 }
if (-not (Start-Ollama)) { Write-Fail "Ollama ne répond pas."; exit 1 }

$apiWasRunning = [bool](Get-PortProcessId 8000)
if ($apiWasRunning) {
    Write-Step "Arrêt de l'API pendant l'évaluation"
    Stop-Port 8000 "API"
    Start-Sleep -Seconds 2
}

Write-Step "Évaluation"
& $Python eval\run_eval.py @args
$code = $LASTEXITCODE

if ($apiWasRunning) {
    Write-Step "Redémarrage de l'application"
    & "$PSScriptRoot\start.ps1" -NoBrowser
}
exit $code
