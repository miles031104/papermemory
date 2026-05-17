param(
    [switch]$SkipQdrant
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvExamplePath = Join-Path $RepoRoot ".env.example"
$EnvPath = Join-Path $RepoRoot ".env"

function Test-CommandExists {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$DefaultValue
    )

    if (-not (Test-Path -LiteralPath $EnvPath)) {
        return $DefaultValue
    }

    $pattern = "^\s*$([regex]::Escape($Key))=(.*)$"
    foreach ($line in Get-Content -LiteralPath $EnvPath) {
        if ($line -match $pattern) {
            return $Matches[1].Trim().Trim("'").Trim('"')
        }
    }

    return $DefaultValue
}

function Test-DockerUsable {
    if (-not (Test-CommandExists "docker")) {
        return $false
    }

    & docker info *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Path -LiteralPath $EnvPath)) {
    Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
    Write-Host "Created .env from .env.example"
}

$mode = (Get-EnvValue "PAPERMEMORY_QDRANT_MODE" "server").ToLowerInvariant()

if (-not $SkipQdrant) {
    if ($mode -eq "server") {
        if (-not (Test-DockerUsable)) {
            throw "PAPERMEMORY_QDRANT_MODE=server requires Docker. Start Docker Desktop or rerun setup with -VectorMode local."
        }

        Write-Host "Starting Qdrant with Docker Compose..."
        Push-Location $RepoRoot
        try {
            & docker compose up -d qdrant
            if ($LASTEXITCODE -ne 0) {
                throw "docker compose failed to start Qdrant."
            }
        }
        finally {
            Pop-Location
        }
    }
    elseif ($mode -eq "local") {
        Write-Host "Qdrant local mode is configured; Docker is not required."
    }
    else {
        throw "Unsupported PAPERMEMORY_QDRANT_MODE '$mode'. Use 'server' or 'local'."
    }
}

Write-Host ""
Write-Host "Run the API in this terminal:"
Write-Host "  cd apps\api"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn app.main:app --reload --port 8000"
Write-Host ""
Write-Host "Run the web app in a second terminal:"
Write-Host "  cd apps\web"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "Open the web app at http://localhost:3000 or http://127.0.0.1:3000"
Write-Host "API CORS defaults allow both local web origins."
