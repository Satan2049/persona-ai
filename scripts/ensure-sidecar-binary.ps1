# Ensure persona-backend.exe sits next to the desktop exe (Tauri sidecar lookup).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Triple = (rustc --print host-tuple).Trim()
$Bundled = Join-Path $Root "apps\desktop\src-tauri\binaries\persona-backend-$Triple.exe"
$TauriDir = Join-Path $Root "apps\desktop\src-tauri"

if (-not (Test-Path $Bundled)) {
    Write-Host "Sidecar missing at $Bundled - building..."
    & (Join-Path $Root "scripts\build-sidecar.ps1")
    return
}

foreach ($Profile in @("debug", "release")) {
    $TargetDir = Join-Path $TauriDir "target\$Profile"
    if (-not (Test-Path $TargetDir)) {
        continue
    }
    $Dest = Join-Path $TargetDir "persona-backend.exe"
    Copy-Item $Bundled $Dest -Force
    Write-Host ('Sidecar synced -> target\' + $Profile + '\persona-backend.exe')
}
