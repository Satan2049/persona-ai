# Ensure Tauri bundle resource folder exists (required even for `tauri dev`).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$TauriResources = Join-Path $Root "apps\desktop\src-tauri\resources"

New-Item -ItemType Directory -Force -Path $TauriResources | Out-Null
Write-Host 'Desktop resource folder ready: apps\desktop\src-tauri\resources\'
