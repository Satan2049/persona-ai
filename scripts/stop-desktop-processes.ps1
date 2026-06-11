# Stop Persona AI processes that lock Tauri/PyInstaller output files.
$ErrorActionPreference = "SilentlyContinue"

$names = @("persona-ai-desktop", "persona-backend")
$stopped = 0

foreach ($name in $names) {
    Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "Stopping $($_.ProcessName) (PID $($_.Id))"
        Stop-Process -Id $_.Id -Force
        $stopped++
    }
}

if ($stopped -eq 0) {
    Write-Host "No running Persona AI processes found."
} else {
    Start-Sleep -Seconds 1
    Write-Host "Stopped $stopped process(es). Safe to rebuild."
}
