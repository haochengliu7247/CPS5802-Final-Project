param(
    [int]$TotalRows = 3000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$OutputPrefix = "qwen25_7b_distillation_dataset_full"
$LogDir = Join-Path $ProjectRoot "model_outputs\distillation\full_run_logs"
$LatestStatusPath = Join-Path $LogDir "latest_status.json"
$CsvPath = Join-Path $ProjectRoot "model_outputs\distillation\$OutputPrefix.csv"

function Get-CsvRowCount {
    param([string]$Path)
    if (!(Test-Path -LiteralPath $Path)) {
        return 0
    }
    try {
        return (Import-Csv -LiteralPath $Path).Count
    } catch {
        Start-Sleep -Milliseconds 300
        return (Import-Csv -LiteralPath $Path).Count
    }
}

function Format-Duration {
    param([TimeSpan]$Span)
    if ($Span.TotalSeconds -lt 0 -or [double]::IsNaN($Span.TotalSeconds)) {
        return "unknown"
    }
    if ($Span.TotalDays -ge 1) {
        return "{0}d {1}h {2}m" -f [int]$Span.TotalDays, $Span.Hours, $Span.Minutes
    }
    if ($Span.TotalHours -ge 1) {
        return "{0}h {1}m" -f [int]$Span.TotalHours, $Span.Minutes
    }
    return "{0}m {1}s" -f [int]$Span.TotalMinutes, $Span.Seconds
}

$status = $null
if (Test-Path -LiteralPath $LatestStatusPath) {
    $status = Get-Content -Raw -LiteralPath $LatestStatusPath | ConvertFrom-Json
}

$rowCount = Get-CsvRowCount -Path $CsvPath
$percent = if ($TotalRows -gt 0) { [Math]::Min(100.0, ([double]$rowCount / [double]$TotalRows) * 100.0) } else { 0.0 }
$barWidth = 40
$filled = [Math]::Floor(($percent / 100) * $barWidth)
$empty = $barWidth - $filled
$bar = ("#" * $filled) + ("-" * $empty)

$startedAt = $null
if ($status -and $status.started_at) {
    try { $startedAt = [datetime]::Parse($status.started_at) } catch { $startedAt = $null }
}
$elapsed = if ($startedAt) { (Get-Date) - $startedAt } else { [TimeSpan]::Zero }
$rowsPerHour = if ($elapsed.TotalHours -gt 0) { $rowCount / $elapsed.TotalHours } else { 0 }
$remainingRows = [Math]::Max($TotalRows - $rowCount, 0)
$eta = if ($rowsPerHour -gt 0) {
    [TimeSpan]::FromHours($remainingRows / $rowsPerHour)
} else {
    [TimeSpan]::Zero
}

$processes = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*generate_qwen_distillation_dataset_resumable.py*" } |
    Select-Object ProcessId, CommandLine

$running = [bool]$processes
$statusText = if ($rowCount -ge $TotalRows) { "completed" } elseif ($status -and $status.status) { $status.status } elseif ($running) { "running" } else { "unknown" }

Write-Host ""
Write-Host "Qwen2.5-7B full distillation progress"
Write-Host ("[{0}] {1}/{2} rows ({3:N2}%)" -f $bar, $rowCount, $TotalRows, $percent)
Write-Host ("Status: {0}" -f $statusText)
Write-Host ("Running process: {0}" -f ($(if ($running) { "YES" } else { "NO" })))
if ($running) {
    Write-Host ("Python PID: {0}" -f (($processes | Select-Object -First 1).ProcessId))
}
Write-Host ("Elapsed: {0}" -f (Format-Duration $elapsed))
Write-Host ("Speed: {0:N2} rows/hour" -f $rowsPerHour)
if ($rowsPerHour -gt 0 -and $rowCount -lt $TotalRows) {
    Write-Host ("Estimated remaining at current speed: {0}" -f (Format-Duration $eta))
}
if ($status -and $status.deadline_at) {
    Write-Host ("10-hour stop time: {0}" -f $status.deadline_at)
}
Write-Host ("CSV: {0}" -f $CsvPath)
if ($status -and $status.stdout_log -and (Test-Path -LiteralPath $status.stdout_log)) {
    Write-Host ("Stdout log: {0}" -f $status.stdout_log)
}
if ($status -and $status.stderr_log -and (Test-Path -LiteralPath $status.stderr_log)) {
    Write-Host ("Stderr log: {0}" -f $status.stderr_log)
}

Write-Progress `
    -Activity "Qwen2.5-7B full distillation" `
    -Status ("{0}/{1} rows ({2:N2}%)" -f $rowCount, $TotalRows, $percent) `
    -PercentComplete ([Math]::Min(100, [int]$percent))
