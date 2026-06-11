# Regenerate Tauri/PyInstaller icons from app-icon.svg and clear stale embed cache.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$TauriDir = Join-Path $Root "apps\desktop\src-tauri"
$Svg = Join-Path $Root "assets\icons\app-icon.svg"
$PngOut = Join-Path $Root "assets\icons\app-icon-1024.png"

if (-not (Test-Path $Svg)) {
    Write-Error "Missing $Svg"
}

Push-Location (Join-Path $Root "apps\desktop")
try {
    npx tauri icon "../../assets/icons/app-icon.svg"
} finally {
    Pop-Location
}

$masterPng = Join-Path $TauriDir "icons\icon.png"
if (Test-Path $masterPng) {
    Copy-Item $masterPng $PngOut -Force
}

foreach ($profile in @("release", "debug")) {
    $buildRoot = Join-Path $TauriDir "target\$profile\build"
    if (Test-Path $buildRoot) {
        Get-ChildItem $buildRoot -Directory -Filter "persona-ai-desktop-*" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
    }
}

Write-Host "Icons refreshed from app-icon.svg -> apps/desktop/src-tauri/icons/"
