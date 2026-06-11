# Start the Persona AI backend in development mode.
$ErrorActionPreference = "Stop"
$Backend = Join-Path (Split-Path -Parent $PSScriptRoot) "apps\backend"
Push-Location $Backend
try {
    if (Test-Path ".venv\Scripts\activate.ps1") {
        & ".venv\Scripts\activate.ps1"
    }
    if (Test-Path ".venv\Scripts\python.exe") {
        & ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    } else {
        python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    }
} finally {
    Pop-Location
}
