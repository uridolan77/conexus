# Start-ConexusPC.ps1
# Starts the full Conexus dev stack on this PC.
#
#   conexus:            docker compose  (postgres + backend:8000 + frontend:3000)
#   conexus.adaptation: dotnet run      (API on http://localhost:5000)
#
# Usage:
#   .\scripts\Start-ConexusPC.ps1
#   .\scripts\Start-ConexusPC.ps1 -Build                                # rebuild docker images before starting
#   .\scripts\Start-ConexusPC.ps1 -NoAdapt                             # skip adaptation service
#   .\scripts\Start-ConexusPC.ps1 -NoBrowser                           # skip opening browser tab
#   .\scripts\Start-ConexusPC.ps1 -InternalAdapterApiKey "my-key"      # override internal adapter API key
#   .\scripts\Start-ConexusPC.ps1 -ConexusProjectApiKey  "cx_live_..." # pass project key to adaptation LLM client

param(
    [string]$ConexusDir            = (Split-Path $PSScriptRoot -Parent),
    [string]$AdaptationDir         = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "conexus.adaptation"),
    [switch]$Build,
    [switch]$NoAdapt,
    [switch]$NoBrowser,
    [string]$InternalAdapterApiKey = "localdev-internal-key-change-before-prod-123456",
    [string]$ConexusProjectApiKey  = ""
)

$ErrorActionPreference = "Stop"

function Write-Header([string]$Text) {
    Write-Host ""
    Write-Host "==> $Text" -ForegroundColor Cyan
}

# --- 1. docker compose up -----------------------------------------------------
Write-Header "Starting conexus (docker compose)"

if (-not (Test-Path "$ConexusDir\.env")) {
    Write-Host "WARNING: $ConexusDir\.env not found -- docker compose may fail." -ForegroundColor Yellow
    Write-Host "         Copy .env.example to .env and fill in ENCRYPTION_KEY at minimum."
}

Push-Location $ConexusDir
try {
    if ($Build) {
        docker compose up -d --build
    } else {
        docker compose up -d
    }
    if (-not $?) { throw "docker compose up failed" }
} finally {
    Pop-Location
}

Write-Host "  conexus backend  -> http://localhost:8000" -ForegroundColor Green
Write-Host "  conexus frontend -> http://localhost:3000" -ForegroundColor Green

# --- 2. Database migrations (via docker exec) ---------------------------------
Write-Header "Running database migrations"

Push-Location $ConexusDir
try {
    docker compose exec -T backend python -m alembic upgrade head
    if (-not $?) {
        Write-Host "WARNING: migration step reported failure." -ForegroundColor Yellow
        Write-Host "         The backend container may still be starting up -- re-run once healthy." -ForegroundColor Yellow
    }
} catch {
    Write-Host "WARNING: docker exec failed: $_" -ForegroundColor Yellow
    Write-Host "         Re-run once the backend container is healthy." -ForegroundColor Yellow
} finally {
    Pop-Location
}

# --- 3. conexus.adaptation (new window) ---------------------------------------
if (-not $NoAdapt) {
    Write-Header "Starting conexus.adaptation (dotnet run on :5000)"

    if (-not (Test-Path $AdaptationDir)) {
        Write-Host "WARNING: AdaptationDir not found: $AdaptationDir" -ForegroundColor Yellow
        Write-Host "         Pass -AdaptationDir <path> or -NoAdapt to suppress this." -ForegroundColor Yellow
    } else {
        $AdaptationApi = Join-Path $AdaptationDir "src\Conexus.Adaptation.Api"

        $envLines = @(
            "`$env:Conexus__BaseUrl            = 'http://localhost:8000'",
            "`$env:GatewayRegistration__Mode    = 'http'",
            "`$env:GatewayRegistration__BaseUrl = 'http://localhost:8000'",
            "`$env:GatewayRegistration__ApiKey  = '$InternalAdapterApiKey'"
        )
        if ($ConexusProjectApiKey) {
            $envLines += "`$env:Conexus__ApiKey = '$ConexusProjectApiKey'"
        }
        $envSetup = $envLines -join "; "

        $cmd = "& { `$host.UI.RawUI.WindowTitle = 'conexus.adaptation'; $envSetup; Set-Location '$AdaptationDir'; dotnet run --project '$AdaptationApi' --urls http://0.0.0.0:5000 }"
        Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $cmd

        Write-Host "  conexus.adaptation -> http://localhost:5000" -ForegroundColor Green
        Write-Host "  (running in a separate window -- close it to stop the service)" -ForegroundColor Gray
    }
}

# --- 4. Open browser ----------------------------------------------------------
if (-not $NoBrowser) {
    Start-Process "http://localhost:3000"
}

# --- Done ---------------------------------------------------------------------
Write-Host ""
Write-Host "Stack is up." -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor DarkGray
Write-Host "  docker compose -f `"$ConexusDir\docker-compose.yml`" logs -f  # stream logs" -ForegroundColor DarkGray
Write-Host "  docker compose -f `"$ConexusDir\docker-compose.yml`" down      # stop conexus" -ForegroundColor DarkGray
Write-Host "  # Close the 'conexus.adaptation' window to stop the .NET service" -ForegroundColor DarkGray
Write-Host ""
