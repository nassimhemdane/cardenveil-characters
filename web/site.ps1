param(
    [ValidateSet("build", "preview", "check", "gm")]
    [string]$Command = "build",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Initialize-NodeRuntime {
    # Existing terminals can keep the PATH from before Node/Volta was installed.
    # Resolve Volta's selected runtime directly, including its matching npm.cmd.
    $VoltaCommand = Get-Command volta.exe -ErrorAction SilentlyContinue
    $VoltaCandidates = @(
        $(if ($VoltaCommand) { $VoltaCommand.Source }),
        $(if ($env:ProgramFiles) { Join-Path $env:ProgramFiles 'Volta\volta.exe' }),
        $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'Volta\bin\volta.exe' })
    )
    foreach ($VoltaPath in $VoltaCandidates) {
        if (-not $VoltaPath -or -not (Test-Path -LiteralPath $VoltaPath)) { continue }
        $ResolvedNode = & $VoltaPath which node 2>$null
        if ($LASTEXITCODE -eq 0 -and $ResolvedNode) {
            $RuntimeDirectory = Split-Path -Parent ([string]$ResolvedNode).Trim()
            $NpmPath = Join-Path $RuntimeDirectory 'npm.cmd'
            if (Test-Path -LiteralPath $NpmPath) {
                $env:Path = $RuntimeDirectory + ';' + $env:Path
                $script:SiteNpm = $NpmPath
                return
            }
        }
    }
    $NodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    $RuntimeCandidates = @(
        $(if ($NodeCommand) { Split-Path -Parent $NodeCommand.Source }),
        $(if ($env:ProgramFiles) { Join-Path $env:ProgramFiles 'nodejs' }),
        $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'Programs\nodejs' })
    )
    foreach ($RuntimeDirectory in $RuntimeCandidates) {
        if (-not $RuntimeDirectory) { continue }
        $NpmPath = Join-Path $RuntimeDirectory 'npm.cmd'
        if ((Test-Path -LiteralPath $NpmPath) -and (Test-Path -LiteralPath (Join-Path $RuntimeDirectory 'node.exe'))) {
            $env:Path = $RuntimeDirectory + ';' + $env:Path
            $script:SiteNpm = $NpmPath
            return
        }
    }
    throw 'Node.js et npm sont introuvables. Installez Node.js 22.12 ou plus recent, puis relancez web\site.cmd.'
}

function Build-AtelierPage {
    Initialize-NodeRuntime
    Push-Location (Join-Path $PSScriptRoot 'atelier-app')
    try {
        if (-not (Test-Path -LiteralPath 'node_modules')) {
            & $script:SiteNpm ci
            if ($LASTEXITCODE -ne 0) { throw 'Installation des dependances Atelier impossible.' }
        }
        & $script:SiteNpm run build
        if ($LASTEXITCODE -ne 0) { throw 'Build de la page Atelier impossible.' }
    } finally {
        Pop-Location
    }
}

if ($Command -eq "gm") {
    $GmPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $GmPython)) { $GmPython = "py" }
    & $GmPython -X utf8 web\build.py
    if ($LASTEXITCODE -ne 0) { throw "Échec du build du site." }
    Build-AtelierPage
    Write-Host "Agent MJ local : http://127.0.0.1:$Port/gm/" -ForegroundColor Cyan
    & $GmPython -m uvicorn cardenveil.server.app:create_app --factory --app-dir src --host 127.0.0.1 --port $Port
    exit $LASTEXITCODE
}

function Build-Site {
    py -X utf8 web\metadata.py init
    if ($LASTEXITCODE -ne 0) { throw "Échec de l'initialisation des métadonnées." }
    py -X utf8 web\metadata.py validate
    if ($LASTEXITCODE -ne 0) { throw "Métadonnées invalides." }
    py -X utf8 web\build.py
    if ($LASTEXITCODE -ne 0) { throw "Échec de la génération du site." }
    Build-AtelierPage
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
