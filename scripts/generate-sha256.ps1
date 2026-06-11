# Generate SHA256 checksums for release binaries and archives.
# Usage:
#   .\scripts\generate-sha256.ps1
#   .\scripts\generate-sha256.ps1 -ReleaseDir "dist\release" -OutputFile "SHA256.txt"
param(
    [string]$ReleaseDir = "",
    [string]$OutputFile = "SHA256.txt",
    [switch]$Recurse
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not $ReleaseDir) {
    $candidates = @(
        (Join-Path $Root "dist\release"),
        (Join-Path $Root "release"),
        (Join-Path $Root "apps\desktop\src-tauri\target\release\bundle")
    )
    foreach ($dir in $candidates) {
        if (Test-Path $dir) {
            $ReleaseDir = $dir
            break
        }
    }
    if (-not $ReleaseDir) {
        $ReleaseDir = Join-Path $Root "dist\release"
    }
}

$resolvedRelease = Resolve-Path -LiteralPath $ReleaseDir -ErrorAction SilentlyContinue
if (-not $resolvedRelease) {
    Write-Error "Release directory not found. Pass -ReleaseDir or create dist\release with your .exe / .zip assets."
}
$ReleaseRoot = $resolvedRelease.Path.TrimEnd("\", "/")

$extensions = @(".exe", ".zip", ".msi", ".msix", ".dmg", ".appimage", ".tar.gz", ".tgz", ".7z")
$files = Get-ChildItem -Path $ReleaseRoot -File -Recurse:$Recurse | Where-Object {
    $name = $_.Name.ToLowerInvariant()
    foreach ($ext in $extensions) {
        if ($name.EndsWith($ext)) { return $true }
    }
    return $false
} | Sort-Object FullName

if ($files.Count -eq 0) {
    Write-Warning "No release assets (*.exe, *.zip, *.msi, ...) found under $ReleaseRoot"
}

$lines = @(
    "# Persona AI - SHA256 checksums",
    "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')",
    "# Source directory: $ReleaseRoot",
    "#",
    "# Verify (PowerShell):",
    "#   Get-FileHash -Algorithm SHA256 -Path '.\Persona AI_0.1.0_x64-setup.exe'",
    "# Compare the hash with the line below.",
    "#",
    "# See docs/TRUST.md for full verification steps.",
    ""
)

foreach ($file in $files) {
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $from = (New-Object System.Uri ($ReleaseRoot.TrimEnd("\") + "\"))
    $to = New-Object System.Uri $file.FullName
    $relative = [System.Uri]::UnescapeDataString($from.MakeRelativeUri($to).ToString())
    if (-not $relative -or $relative -eq ".") { $relative = $file.Name }
    $relative = $relative -replace "\\", "/"
    $lines += "$hash  $relative"
}

if ($lines.Count -le 8) {
    $lines += "# (no release files found - add .exe / .zip assets and re-run this script)"
}

$outputPath = if ([System.IO.Path]::IsPathRooted($OutputFile)) { $OutputFile } else { Join-Path $Root $OutputFile }
$lines | Set-Content -Path $outputPath -Encoding UTF8
Write-Host "Wrote $($files.Count) checksum(s) to $outputPath"
