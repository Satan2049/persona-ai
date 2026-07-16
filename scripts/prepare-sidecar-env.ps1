# Snapshot apps/backend/.env into the sidecar bundle (runtime.env + build id).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $Root "apps\backend\.env"
$Example = Join-Path $Root "apps\backend\.env.example"
$OutDir = Join-Path $Root "apps\desktop\sidecar\build-env"
$Out = Join-Path $OutDir "runtime.env"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if (Test-Path $Source) {
    Copy-Item -Path $Source -Destination $Out -Force
    Write-Host "Sidecar env source: apps\backend\.env"
} elseif (Test-Path $Example) {
    Copy-Item -Path $Example -Destination $Out -Force
    Write-Warning "apps\backend\.env missing - bundling .env.example instead."
} else {
    throw "No env file found for sidecar bundle (apps\backend\.env)."
}

$BuildId = Get-Date -Format "yyyyMMdd-HHmmss"
$Content = Get-Content $Out -Raw
if ($Content -notmatch "(?m)^PERSONA_BUILD_ID=") {
    Add-Content -Path $Out -Value "PERSONA_BUILD_ID=$BuildId"
} else {
    $Content = [regex]::Replace($Content, "(?m)^PERSONA_BUILD_ID=.*", "PERSONA_BUILD_ID=$BuildId")
    Set-Content -Path $Out -Value $Content.TrimEnd() -NoNewline
    Add-Content -Path $Out -Value ""
}

Write-Host ('Prepared sidecar runtime.env (PERSONA_BUILD_ID=' + $BuildId + ')')
