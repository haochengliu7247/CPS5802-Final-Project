param(
    [int]$IntervalSeconds = 30,
    [int]$TotalRows = 3000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$CheckScript = Join-Path $ProjectRoot "check_qwen_distillation_status.ps1"

while ($true) {
    Clear-Host
    Write-Host ("Last refresh: {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File $CheckScript -TotalRows $TotalRows

    $processes = Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -like "*generate_qwen_distillation_dataset_resumable.py*" }
    if (-not $processes) {
        Write-Host ""
        Write-Host "Distillation process is not running. Monitor stopped."
        break
    }

    Write-Host ""
    Write-Host ("Refreshing again in {0} seconds. Press Ctrl+C to stop watching only; it will not stop the distillation task." -f $IntervalSeconds)
    Start-Sleep -Seconds $IntervalSeconds
}
