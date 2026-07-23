# Regenerate Tauri/PyInstaller icons and clear stale embed cache.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$TauriDir = Join-Path $Root "apps\desktop\src-tauri"
$Svg = Join-Path $Root "assets\icons\app-icon.svg"
$PngMaster = Join-Path $Root "assets\icons\app-icon-1024.png"
$FavPng = Join-Path $Root "assets\icons\favicon.png"

$IconSource = if (Test-Path $PngMaster) { $PngMaster } elseif (Test-Path $Svg) { $Svg } else { $null }
if (-not $IconSource) {
    Write-Error "Missing app-icon-1024.png or app-icon.svg under assets/icons/"
}

Push-Location (Join-Path $Root "apps\desktop")
try {
    npx tauri icon $IconSource
} finally {
    Pop-Location
}

# Web favicon: prefer PNG brand mark (not the minimal SVG)
$Ui = Join-Path $Root "ui"
if (Test-Path $FavPng) {
    Copy-Item $FavPng (Join-Path $Ui "favicon.png") -Force
} elseif (Test-Path $PngMaster) {
    Copy-Item $PngMaster (Join-Path $Ui "favicon.png") -Force
}
if (Test-Path $Svg) {
    Copy-Item $Svg (Join-Path $Ui "favicon.svg") -Force
}

foreach ($profile in @("release", "debug")) {
    $buildRoot = Join-Path $TauriDir "target\$profile\build"
    if (Test-Path $buildRoot) {
        Get-ChildItem $buildRoot -Directory -Filter "persona-ai-desktop-*" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
    }
}

Write-Host "Icons refreshed from $IconSource -> apps/desktop/src-tauri/icons/"
