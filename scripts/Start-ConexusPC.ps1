# Start-Conexus.ps1
# Starts the full Conexus stack:
#   - conexus           docker compose (postgres + backend:8000 + frontend:3000)
#   - conexus.adaptation dotnet run (API on http://localhost:5000)
#
# Usage:
#   .\scripts\Start-Conexus.ps1            # start both
#   .\scripts\Start-Conexus.ps1 -NoAdapt  # start conexus only (skip adaptation)

param(
    [switch]$NoAdapt
)

$ErrorActionPreference = "Stop"

$ConexusDir    = "C:\Dev\conexus"
$AdaptationSln = "C:\Dev\conexus.adaptation"
$AdaptationApi = "C:\Dev\conexus.adaptation\src\Conexus.Adaptation.Api"

function Write-Header([string]$Text) {
    Write-Host ""
    Write-Host "==> $Text" -ForegroundColor Cyan
}

# 1. conexus - docker compose up (detached)
Write-Header "Starting conexus (docker compose)"

if (-not (Test-Path "$ConexusDir\.env")) {
    Write-Host "WARNING: $ConexusDir\.env not found - docker compose may fail." -ForegroundColor Yellow
    Write-Host "         Copy .env.example to .env and fill in ENCRYPTION_KEY at minimum."
}

Push-Location $ConexusDir
try {
    docker compose up -d --build
    if (-not $?) { throw "docker compose up failed" }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "  conexus backend  -> http://localhost:8000" -ForegroundColor Green
Write-Host "  conexus frontend -> http://localhost:3000" -ForegroundColor Green

# Run pending Alembic migrations against the live DB
Write-Header "Running database migrations"
Push-Location "$ConexusDir\backend"
try {
    $env:DATABASE_URL = "postgresql+asyncpg://conexus:conexus@localhost:5432/conexus"
    alembic upgrade head
    if (-not $?) { Write-Host "WARNING: alembic upgrade failed - check schema manually." -ForegroundColor Yellow }
} catch {
    Write-Host "WARNING: alembic not found or migration failed: $_" -ForegroundColor Yellow
} finally {
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    Pop-Location
}

# 2. conexus.adaptation - dotnet run in a new window
if (-not $NoAdapt) {
    Write-Header "Starting conexus.adaptation (dotnet run on :5000)"

    $cmd = "& { `$host.UI.RawUI.WindowTitle = 'conexus.adaptation'; Set-Location '$AdaptationSln'; dotnet run --project '$AdaptationApi' --urls http://0.0.0.0:5000 }"

    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $cmd

    Write-Host ""
    Write-Host "  conexus.adaptation -> http://localhost:5000" -ForegroundColor Green
    Write-Host "  (running in a separate window - close it to stop the service)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Stack is up." -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor DarkGray
Write-Host "  docker compose -f $ConexusDir\docker-compose.yml logs -f  # stream logs" -ForegroundColor DarkGray
Write-Host "  docker compose -f $ConexusDir\docker-compose.yml down      # stop conexus" -ForegroundColor DarkGray
Write-Host "  # Close the 'conexus.adaptation' window to stop the .NET service" -ForegroundColor DarkGray
Write-Host ""
