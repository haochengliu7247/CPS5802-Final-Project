param(
    [Parameter(Mandatory=$true)]
    [string]$SourceAdapterDir,
    [string]$LoraRoot = "E:\CPS5802_Qwen_LoRA",
    [switch]$AlsoCopyEval
)

$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $SourceAdapterDir)) {
    throw "Source adapter directory not found: $SourceAdapterDir"
}

$DestinationRoot = Join-Path $LoraRoot "student_qwen25_05b_lora"
$DestinationAdapter = Join-Path $DestinationRoot "final_adapter"
$BackupRoot = Join-Path $DestinationRoot "adapter_backups"

New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null

if (Test-Path -LiteralPath $DestinationAdapter) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backup = Join-Path $BackupRoot "final_adapter_$stamp"
    Move-Item -LiteralPath $DestinationAdapter -Destination $backup
    Write-Host "Backed up existing adapter to: $backup"
}

Copy-Item -LiteralPath $SourceAdapterDir -Destination $DestinationAdapter -Recurse -Force
Write-Host "Installed trained LoRA adapter to: $DestinationAdapter"

if ($AlsoCopyEval) {
    $SourceRoot = Split-Path -Parent $SourceAdapterDir
    $SourceEval = Join-Path $SourceRoot "eval"
    if (Test-Path -LiteralPath $SourceEval) {
        $DestinationEval = Join-Path $DestinationRoot "eval"
        if (Test-Path -LiteralPath $DestinationEval) {
            $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
            Move-Item -LiteralPath $DestinationEval -Destination (Join-Path $BackupRoot "eval_$stamp")
        }
        Copy-Item -LiteralPath $SourceEval -Destination $DestinationEval -Recurse -Force
        Write-Host "Copied evaluation outputs to: $DestinationEval"
    }
}

Write-Host ""
Write-Host "Quick inference command:"
Write-Host "  `$env:QWEN_LORA_ROOT='$LoraRoot'; $LoraRoot\.venv_qwen_lora\Scripts\python.exe run_student_inference.py --adapter-dir '$DestinationAdapter'"
