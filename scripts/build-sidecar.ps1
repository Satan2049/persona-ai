# Build the Persona AI Python sidecar with PyInstaller.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "apps\backend"
$Spec = Join-Path $Root "apps\desktop\sidecar\persona-backend.spec"
$Dist = Join-Path $Root "apps\desktop\sidecar\dist"
$Binaries = Join-Path $Root "apps\desktop\src-tauri\binaries"
$TauriDir = Join-Path $Root "apps\desktop\src-tauri"

$Triple = (rustc --print host-tuple).Trim()
if (-not $Triple) {
    throw "Could not determine Rust host triple (rustc --print host-tuple)."
}
$SidecarBundled = Join-Path $Binaries "persona-backend-$Triple.exe"

$iconIco = Join-Path $Root "apps\desktop\src-tauri\icons\icon.ico"
if (-not (Test-Path $iconIco)) {
    Write-Host "icon.ico missing; generating icons first..."
    & (Join-Path $Root "scripts\prepare-desktop-icons.ps1")
}

Push-Location $Backend
try {
    & (Join-Path $Root "scripts\stop-desktop-processes.ps1")

    if (Test-Path ".venv\Scripts\python.exe") {
        $Python = ".venv\Scripts\python.exe"
    } else {
        $Python = "python"
    }

    & $Python -m pip install -r requirements-dev.txt
    & $Python -m PyInstaller $Spec --clean --noconfirm --distpath $Dist --workpath (Join-Path $Root "apps\desktop\sidecar\build")

    $Built = Join-Path $Dist "persona-backend.exe"
    if (-not (Test-Path $Built)) {
        throw "PyInstaller output missing: $Built"
    }

    New-Item -ItemType Directory -Force -Path $Binaries | Out-Null
    Copy-Item $Built $SidecarBundled -Force
    Write-Host "Sidecar ready:" $SidecarBundled

    foreach ($Profile in @("debug", "release")) {
        $TargetDir = Join-Path $TauriDir "target\$Profile"
        if (Test-Path $TargetDir) {
            Copy-Item $Built (Join-Path $TargetDir "persona-backend.exe") -Force
            Write-Host ('Copied sidecar -> target\' + $Profile + '\persona-backend.exe')
        }
    }
} finally {
    Pop-Location
}
