# Download Rhubarb Lip Sync into tools/rhubarb/ (Windows).
# Usage: powershell -File scripts/ensure-rhubarb.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root "tools"
$Dest = Join-Path $Tools "rhubarb"
$Exe = Join-Path $Dest "rhubarb.exe"
$Version = "1.14.0"
$Url = "https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v$Version/Rhubarb-Lip-Sync-$Version-Windows.zip"

if (Test-Path $Exe) {
    Write-Host "Rhubarb already present: $Exe"
    & $Exe --version
    exit 0
}

New-Item -ItemType Directory -Force -Path $Tools | Out-Null
$Zip = Join-Path $Tools "rhubarb-win.zip"
$Extract = Join-Path $Tools "rhubarb-extract"

Write-Host "Downloading Rhubarb $Version ..."
Invoke-WebRequest -Uri $Url -OutFile $Zip -UseBasicParsing

if (Test-Path $Extract) { Remove-Item $Extract -Recurse -Force }
Expand-Archive -Path $Zip -DestinationPath $Extract -Force

$Found = Get-ChildItem $Extract -Recurse -Filter "rhubarb.exe" | Select-Object -First 1
if (-not $Found) {
    throw "rhubarb.exe not found in downloaded archive"
}

if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item -Path (Join-Path $Found.Directory.FullName "*") -Destination $Dest -Recurse -Force

Remove-Item $Zip -Force -ErrorAction SilentlyContinue
Remove-Item $Extract -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Installed: $Exe"
& $Exe --version
