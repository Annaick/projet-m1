<#
.SYNOPSIS
    Arrête l'API et l'interface. Ollama reste lancé (il est partagé avec d'autres usages).
#>
. "$PSScriptRoot\common.ps1"

Write-Step "Arrêt"
Stop-Port 8501 "Interface"
Stop-Port 8000 "API"
