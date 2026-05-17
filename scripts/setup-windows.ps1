param(
    [ValidateSet("auto", "docker", "local")]
    [string]$VectorMode = "auto",
    [switch]$InstallDocker
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvExamplePath = Join-Path $RepoRoot ".env.example"
$EnvPath = Join-Path $RepoRoot ".env"
$ApiDir = Join-Path $RepoRoot "apps\api"
$WebDir = Join-Path $RepoRoot "apps\web"
$VenvDir = Join-Path $ApiDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

function Test-CommandExists {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-DockerUsable {
    if (-not (Test-CommandExists "docker")) {
        return $false
    }

    & docker info *> $null
    return $LASTEXITCODE -eq 0
}

function Ensure-EnvFile {
    if (Test-Path -LiteralPath $EnvPath) {
        return
    }

    Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
    Write-Host "Created .env from .env.example"
}

function Set-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $line = "$Key=$Value"
    $lines = @()
    if (Test-Path -LiteralPath $EnvPath) {
        $lines = @(Get-Content -LiteralPath $EnvPath)
    }

    $updated = $false
    $pattern = "^\s*$([regex]::Escape($Key))="
    $nextLines = @(foreach ($existingLine in $lines) {
        if ($existingLine -match $pattern) {
            $updated = $true
            $line
        }
        else {
            $existingLine
        }
    })

    if (-not $updated) {
        $nextLines += $line
    }

    Set-Content -LiteralPath $EnvPath -Value $nextLines -Encoding utf8
}

function Install-DockerDesktop {
    if (Test-CommandExists "docker") {
        Write-Host "Docker is installed, but the daemon is not reachable."
        Write-Host "Start Docker Desktop, then rerun scripts\setup-windows.ps1 or scripts\start-windows.ps1."
        exit 0
    }

    if (-not (Test-CommandExists "winget")) {
        throw "Docker is unavailable and winget is not installed. Install Docker Desktop manually or rerun with -VectorMode local."
    }

    Write-Host "Installing Docker Desktop with winget..."
    & winget install --id Docker.DockerDesktop -e --source winget
    if ($LASTEXITCODE -ne 0) {
        throw "winget failed to install Docker Desktop."
    }

    Write-Host "Docker Desktop was installed. Start Docker Desktop, wait until it is running, then rerun setup or start."
    exit 0
}

function Resolve-VectorMode {
    $dockerUsable = Test-DockerUsable

    if ($VectorMode -eq "local") {
        return "local"
    }

    if ($VectorMode -eq "docker") {
        if ($dockerUsable) {
            return "docker"
        }
        if ($InstallDocker) {
            Install-DockerDesktop
        }
        throw "Docker mode was requested, but Docker is not usable. Start Docker Desktop, use -InstallDocker, or rerun with -VectorMode local."
    }

    if ($dockerUsable) {
        return "docker"
    }

    if ($InstallDocker) {
        Install-DockerDesktop
    }

    $answer = Read-Host "Docker is not usable. Install Docker Desktop with winget now? [y/N]"
    if ($answer -match "^(y|yes)$") {
        Install-DockerDesktop
    }

    return "local"
}

function Require-Tooling {
    if (-not (Test-CommandExists "python")) {
        throw "Python 3.11+ was not found on PATH."
    }
    if (-not (Test-CommandExists "npm")) {
        throw "npm was not found on PATH. Install Node.js 20+ and rerun setup."
    }
}

function Configure-Qdrant {
    param([Parameter(Mandatory = $true)][ValidateSet("docker", "local")][string]$Mode)

    if ($Mode -eq "docker") {
        Set-EnvValue "PAPERMEMORY_QDRANT_MODE" "server"
        Set-EnvValue "PAPERMEMORY_QDRANT_URL" "http://localhost:6333"
        Set-EnvValue "PAPERMEMORY_QDRANT_LOCAL_PATH" "storage/qdrant_local"
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
    else {
        Set-EnvValue "PAPERMEMORY_QDRANT_MODE" "local"
        Set-EnvValue "PAPERMEMORY_QDRANT_LOCAL_PATH" "storage/qdrant_local"
        Write-Host "Configured Qdrant local mode. Docker will not be required for the vector store."
    }
}

function Install-ApiDependencies {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Host "Creating API virtual environment..."
        & python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create API virtual environment."
        }
    }

    Write-Host "Installing API dependencies..."
    Push-Location $ApiDir
    try {
        & $VenvPython -m pip install -e ".[dev]"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install API dependencies."
        }
    }
    finally {
        Pop-Location
    }
}

function Install-WebDependencies {
    Write-Host "Installing web dependencies..."
    Push-Location $RepoRoot
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install web dependencies."
        }
    }
    finally {
        Pop-Location
    }
}

Require-Tooling
Ensure-EnvFile
$selectedMode = Resolve-VectorMode
Configure-Qdrant -Mode $selectedMode
Install-ApiDependencies
Install-WebDependencies

Write-Host ""
Write-Host "Setup complete."
Write-Host "Start PaperMemory with:"
Write-Host "  .\scripts\start-windows.ps1"
Write-Host ""
Write-Host "Manual commands:"
Write-Host "  cd apps\api; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000"
Write-Host "  cd apps\web; npm run dev"
