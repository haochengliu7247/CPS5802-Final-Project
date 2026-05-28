param(
    [string]$LoraRoot = "E:\CPS5802_Qwen_LoRA",
    [int]$IntervalSeconds = 30
)

$ErrorActionPreference = "SilentlyContinue"
$LogDir = Join-Path $LoraRoot "logs"
$StatusPath = Join-Path $LogDir "latest_training_status.json"

while ($true) {
    Clear-Host
    Write-Host "Qwen2.5-0.5B LoRA training monitor"
    Write-Host ("Time: {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
    Write-Host ("LoRA root: {0}" -f $LoraRoot)
    Write-Host ""

    if (Test-Path -LiteralPath $StatusPath) {
        $status = Get-Content -Raw -LiteralPath $StatusPath | ConvertFrom-Json
        Write-Host ("Status: {0}" -f $status.status)
        if ($status.started_at) { Write-Host ("Started: {0}" -f $status.started_at) }
        if ($status.ended_at) { Write-Host ("Ended: {0}" -f $status.ended_at) }
        if ($status.final_adapter) { Write-Host ("Final adapter: {0}" -f $status.final_adapter) }
        if ($status.error) { Write-Host ("Error: {0}" -f $status.error) }
        if ($status.transcript) { Write-Host ("Transcript: {0}" -f $status.transcript) }
    } else {
        Write-Host "Status: no status file yet"
    }

    Write-Host ""
    Write-Host "GPU:"
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits
    } else {
        Write-Host "nvidia-smi not found"
    }

    Write-Host ""
    Write-Host "Training Python processes:"
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match "train_qwen25_05b_lora|evaluate_student_lora|run_train_qwen25_05b_lora" } |
        Select-Object ProcessId,Name,CommandLine |
        Format-Table -AutoSize

    Write-Host ""
    Write-Host "Latest training log lines:"
    $latestLog = Get-ChildItem -LiteralPath $LogDir -Filter "*.transcript.log" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($latestLog) {
        Get-Content -LiteralPath $latestLog.FullName -Tail 35
    } else {
        Write-Host "No transcript log found yet."
    }

    Write-Host ""
    Write-Host ("Refreshes every {0} seconds. Press Ctrl+C to stop monitoring only." -f $IntervalSeconds)
    Start-Sleep -Seconds $IntervalSeconds
}
