# Build sidecar + Tauri desktop installers.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

& (Join-Path $Root "scripts\stop-desktop-processes.ps1")
& (Join-Path $Root "scripts\ensure-sidecar-binary.ps1")
& (Join-Path $Root "scripts\sync-desktop-ui.ps1")
& (Join-Path $Root "scripts\prepare-desktop-icons.ps1")
& (Join-Path $Root "scripts\build-sidecar.ps1")
Push-Location (Join-Path $Root "apps\desktop")
try {
    npm run build
} finally {
    Pop-Location
}

Write-Host "Installers:"
Write-Host "  apps\desktop\src-tauri\target\release\bundle\nsis\Persona AI_*_x64-setup.exe"
Write-Host "  apps\desktop\src-tauri\target\release\bundle\msi\Persona AI_*_x64_en-US.msi"
