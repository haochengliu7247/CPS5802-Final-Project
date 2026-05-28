$ErrorActionPreference = "Stop"

# English note: see the surrounding code for this project workflow detail.
# English note: see the surrounding code for this project workflow detail.
# English note: see the surrounding code for this project workflow detail.

$ProjectRoot = $PSScriptRoot
$OllamaRoot = "E:\CPS5802_Qwen_Ollama"
$OllamaExe = Join-Path $OllamaRoot "ollama\ollama.exe"
$ModelDir = Join-Path $OllamaRoot "models"
$LogDir = Join-Path $ProjectRoot "model_outputs\distillation\full_run_logs"
$RunHours = 10
$OutputPrefix = "qwen25_7b_distillation_dataset_full"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$StdoutLog = Join-Path $LogDir "full_distillation_$Stamp.stdout.log"
$StderrLog = Join-Path $LogDir "full_distillation_$Stamp.stderr.log"
$StatusPath = Join-Path $LogDir "full_distillation_$Stamp.status.json"
$LatestStatusPath = Join-Path $LogDir "latest_status.json"

Set-Location -LiteralPath $ProjectRoot

$env:OLLAMA_MODEL = "qwen2.5:7b-instruct"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:OLLAMA_HOST = "127.0.0.1:11434"
$env:OLLAMA_MODELS = $ModelDir

if (!(Test-Path -LiteralPath $OllamaExe)) {
    throw "Ollama executable was not found: $OllamaExe"
}

$runningOllama = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $OllamaExe }
if (-not $runningOllama) {
    Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 8
}

$pythonCommand = Get-Command python -ErrorAction Stop
$args = @(
    "-u",
    "generate_qwen_distillation_dataset_resumable.py",
    "--sample-size", "3000",
    "--output-prefix", $OutputPrefix,
    "--max-retries", "1",
    "--flush-every", "1"
)

$startedAt = Get-Date
$deadline = $startedAt.AddHours($RunHours)

$process = Start-Process `
    -FilePath $pythonCommand.Source `
    -ArgumentList $args `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -WindowStyle Hidden `
    -PassThru

$initialStatus = [ordered]@{
    status = "running"
    python_pid = $process.Id
    model = $env:OLLAMA_MODEL
    output_prefix = $OutputPrefix
    started_at = $startedAt.ToString("s")
    deadline_at = $deadline.ToString("s")
    stdout_log = $StdoutLog
    stderr_log = $StderrLog
    status_file = $StatusPath
}
$initialStatus | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
$initialStatus | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $LatestStatusPath -Encoding UTF8

while (-not $process.HasExited -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 30
    $process.Refresh()
}

$endedAt = Get-Date
$finalState = "completed"
$exitCode = $null
if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
    $finalState = "stopped_after_10_hours"
} else {
    $exitCode = $process.ExitCode
    if ($exitCode -ne 0) {
        $finalState = "failed"
    }
}

$csvPath = Join-Path $ProjectRoot "model_outputs\distillation\$OutputPrefix.csv"
$rowsGenerated = 0
if (Test-Path -LiteralPath $csvPath) {
    try {
        $rowsGenerated = [Math]::Max((Import-Csv -LiteralPath $csvPath).Count, 0)
    } catch {
        $rowsGenerated = -1
    }
}

$finalStatus = [ordered]@{
    status = $finalState
    python_pid = $process.Id
    model = $env:OLLAMA_MODEL
    output_prefix = $OutputPrefix
    started_at = $startedAt.ToString("s")
    ended_at = $endedAt.ToString("s")
    deadline_at = $deadline.ToString("s")
    exit_code = $exitCode
    rows_generated = $rowsGenerated
    output_csv = $csvPath
    stdout_log = $StdoutLog
    stderr_log = $StderrLog
    status_file = $StatusPath
}
$finalStatus | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
$finalStatus | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $LatestStatusPath -Encoding UTF8
