param(
    [ValidateSet("build", "preview", "check")]
    [string]$Command = "build",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Build-Site {
    py -X utf8 web\metadata.py init
    if ($LASTEXITCODE -ne 0) { throw "Échec de l'initialisation des métadonnées." }
    py -X utf8 web\metadata.py validate
    if ($LASTEXITCODE -ne 0) { throw "Métadonnées invalides." }
    py -X utf8 web\build.py
    if ($LASTEXITCODE -ne 0) { throw "Échec de la génération du site." }
}

Build-Site

if ($Command -eq "check") {
    $Characters = Get-Content -Raw web\public\data\characters.json | ConvertFrom-Json
    $Archives = Get-ChildItem Final -Filter *.zip -File
    if ($Characters.Count -ne $Archives.Count) {
        throw "Le catalogue contient $($Characters.Count) personnages pour $($Archives.Count) archives."
    }
    Write-Host "Vérification terminée : $($Characters.Count) personnages." -ForegroundColor Green
}

if ($Command -eq "preview") {
    Write-Host "Site local : http://127.0.0.1:$Port" -ForegroundColor Cyan
    py -m http.server $Port --directory web\public
}
