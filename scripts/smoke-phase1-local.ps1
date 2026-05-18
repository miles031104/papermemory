[CmdletBinding()]
param(
    [switch]$VerbosePytest
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ApiRoot = Join-Path $RepoRoot "apps\api"
$VenvPython = Join-Path $ApiRoot ".venv\Scripts\python.exe"
$Python = "python"
$PytestArgs = @(
    "-p",
    "no:cacheprovider",
    "tests/test_phase1_local_pdf_to_evidence.py",
    "tests/test_phase1b_library_scoped_retrieval.py",
    "tests/test_phase1c_library_scoped_chat.py"
)

if (Test-Path $VenvPython) {
    $Python = $VenvPython
}

if (-not $VerbosePytest) {
    $PytestArgs += "-q"
}

$EnvOverrides = @{
    PAPERMEMORY_QDRANT_MODE = "local"
    PAPERMEMORY_VISRAG_BACKEND = "stub"
    PAPERMEMORY_QDRANT_VECTOR_SIZE = "8"
    PAPERMEMORY_QDRANT_LOCAL_PATH = "storage/qdrant_local_smoke"
}
$OriginalEnv = @{}

foreach ($Name in $EnvOverrides.Keys) {
    $OriginalEnv[$Name] = [Environment]::GetEnvironmentVariable($Name, "Process")
    [Environment]::SetEnvironmentVariable($Name, $EnvOverrides[$Name], "Process")
}

Write-Host "Running Phase 1 local PDF-to-scoped-evidence-to-chat smoke..."
Write-Host "API root: $ApiRoot"
Write-Host "Python: $Python"
Write-Host "Qdrant mode: $env:PAPERMEMORY_QDRANT_MODE"
Write-Host "VisRAG backend: $env:PAPERMEMORY_VISRAG_BACKEND"

try {
    Push-Location $ApiRoot
    try {
        & $Python -m pytest @PytestArgs
    }
    finally {
        Pop-Location
    }
}
finally {
    foreach ($Name in $EnvOverrides.Keys) {
        [Environment]::SetEnvironmentVariable($Name, $OriginalEnv[$Name], "Process")
    }
}
