# Sync web UI into the Tauri frontend bundle (same files as http://127.0.0.1:8000).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Ui = Join-Path $Root "ui"
$Public = Join-Path $Root "apps\desktop\public"

if (-not (Test-Path $Ui)) {
    throw "UI folder not found: $Ui"
}

New-Item -ItemType Directory -Force -Path $Public | Out-Null
Get-ChildItem $Public -Force | Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $Ui "*") -Destination $Public -Recurse -Force
Write-Host "Synced ui -> apps/desktop/public"
