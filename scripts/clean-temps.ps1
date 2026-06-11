# Remove generated build artifacts and caches from the repo.
#
# Usage:
#   .\scripts\clean-temps.ps1              # build outputs (default)
#   .\scripts\clean-temps.ps1 -Runtime     # also generated audio / RAG index
#   .\scripts\clean-temps.ps1 -Deep        # also node_modules/
#
# Never removes: .venv, .env, piper_models/, piper/, source code.
param(
    [switch]$Runtime,
    [switch]$Deep
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Remove-RelPath {
    param([string]$Rel)
    $full = Join-Path $Root $Rel
    if (-not (Test-Path -LiteralPath $full)) { return $false }
    Remove-Item -LiteralPath $full -Recurse -Force
    Write-Host "Removed $Rel"
    return $true
}

function Clear-DirKeepGitkeep {
    param([string]$Rel)
    $full = Join-Path $Root $Rel
    if (-not (Test-Path -LiteralPath $full)) { return $false }
    Get-ChildItem -LiteralPath $full -Force | Where-Object { $_.Name -ne ".gitkeep" } |
        Remove-Item -Recurse -Force
    if (-not (Test-Path (Join-Path $full ".gitkeep"))) {
        New-Item -ItemType File -Path (Join-Path $full ".gitkeep") -Force | Out-Null
    }
    Write-Host "Cleared $Rel (kept .gitkeep)"
    return $true
}

$removed = 0

# --- Desktop / Tauri / PyInstaller ---
$buildDirs = @(
    "apps\desktop\sidecar\build",
    "apps\desktop\sidecar\dist",
    "apps\desktop\src-tauri\target",
    "apps\desktop\src-tauri\gen"
)
foreach ($rel in $buildDirs) {
    if (Remove-RelPath $rel) { $removed++ }
}

# Sidecar binaries (keep .gitkeep)
$binDir = Join-Path $Root "apps\desktop\src-tauri\binaries"
if (Test-Path $binDir) {
    Get-ChildItem $binDir -File | Remove-Item -Force
    if (-not (Test-Path (Join-Path $binDir ".gitkeep"))) {
        New-Item -ItemType File -Path (Join-Path $binDir ".gitkeep") -Force | Out-Null
    }
    Write-Host "Cleared apps\desktop\src-tauri\binaries\*.exe"
    $removed++
}

# --- Python caches ---
$cacheDirs = @(
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache"
)
foreach ($rel in $cacheDirs) {
    if (Remove-RelPath $rel) { $removed++ }
}

Get-ChildItem -Path $Root -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
        $rel = $_.FullName.Substring($Root.Length).TrimStart("\")
        Write-Host "Removed $rel"
        $removed++
    }

Get-ChildItem -Path $Root -Recurse -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
        $removed++
    }

# --- Release staging ---
if (Remove-RelPath "dist\release") { $removed++ }

# --- Optional runtime artifacts ---
if ($Runtime) {
    foreach ($rel in @("audio", "apps\backend\audio", "data\rag_index")) {
        if (Clear-DirKeepGitkeep $rel) { $removed++ }
    }
}

# --- Deep clean ---
if ($Deep) {
    foreach ($rel in @("node_modules", "apps\desktop\node_modules")) {
        if (Remove-RelPath $rel) { $removed++ }
    }
}

if ($removed -eq 0) {
    Write-Host "Nothing to clean."
} else {
    Write-Host "Done. ($removed area(s) cleaned)"
}

Write-Host "Kept: apps/backend/.venv, .env, piper_models/, piper/, source."
