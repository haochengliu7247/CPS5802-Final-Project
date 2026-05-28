param(
    [string]$LoraRoot = "E:\CPS5802_Qwen_LoRA",
    [int]$Epochs = 3,
    [int]$TrainBatchSize = 24,
    [int]$EvalBatchSize = 24,
    [int]$MaxSeqLength = 2048,
    [int]$LoraRank = 32,
    [int]$LoraAlpha = 64,
    [double]$LearningRate = 1.5e-4,
    [int]$EvalLimit = 100
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

New-Item -ItemType Directory -Force -Path $LoraRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $LoraRoot "logs") | Out-Null
$BaseModelPath = Join-Path $LoraRoot "base_models\Qwen2.5-0.5B-Instruct"
if (!(Test-Path -LiteralPath $BaseModelPath)) {
    $BaseModelPath = "Qwen/Qwen2.5-0.5B-Instruct"
}

$PythonExe = Join-Path $LoraRoot ".venv_qwen_lora\Scripts\python.exe"
if (!(Test-Path -LiteralPath $PythonExe)) {
    throw "Training venv not found. Run .\setup_qwen_lora_env.ps1 first."
}

$env:QWEN_LORA_ROOT = $LoraRoot
$env:HF_HOME = Join-Path $LoraRoot "huggingface_cache"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $env:HF_HOME "hub"
$env:TRANSFORMERS_CACHE = Join-Path $env:HF_HOME "transformers"
$env:HF_DATASETS_CACHE = Join-Path $env:HF_HOME "datasets"
$env:PIP_CACHE_DIR = Join-Path $LoraRoot "pip_cache"
$env:TEMP = Join-Path $LoraRoot "tmp"
$env:TMP = Join-Path $LoraRoot "tmp"
$env:TOKENIZERS_PARALLELISM = "false"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$TranscriptPath = Join-Path $LoraRoot "logs\train_qwen25_05b_lora_$Stamp.transcript.log"
$StatusPath = Join-Path $LoraRoot "logs\latest_training_status.json"

Start-Transcript -Path $TranscriptPath -Force | Out-Null
try {
    $initialStatus = [ordered]@{
        status = "running"
        started_at = (Get-Date).ToString("s")
        lora_root = $LoraRoot
        project_root = $ProjectRoot
        base_model_path = $BaseModelPath
        transcript = $TranscriptPath
        epochs = $Epochs
        train_batch_size = $TrainBatchSize
        eval_batch_size = $EvalBatchSize
        max_seq_length = $MaxSeqLength
        lora_rank = $LoraRank
        lora_alpha = $LoraAlpha
        learning_rate = $LearningRate
    }
    $initialStatus | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatusPath -Encoding UTF8

    Write-Host "LoRA root: $LoraRoot"
    Write-Host "Project root: $ProjectRoot"
    Write-Host "Base model path: $BaseModelPath"
    Write-Host "Transcript: $TranscriptPath"
    Write-Host "Starting training at $(Get-Date -Format s)"

& $PythonExe prepare_qwen25_lora_dataset.py `
    --source-csv "model_outputs\distillation\qwen25_7b_distillation_dataset_full.csv" `
    --output-dir (Join-Path $LoraRoot "student_qwen25_05b_lora\data") `
    --seed 5802
if ($LASTEXITCODE -ne 0) {
    throw "Dataset preparation failed with exit code $LASTEXITCODE"
}

& $PythonExe train_qwen25_05b_lora.py `
    --model-name $BaseModelPath `
    --data-dir (Join-Path $LoraRoot "student_qwen25_05b_lora\data") `
    --output-dir (Join-Path $LoraRoot "student_qwen25_05b_lora\checkpoints") `
    --final-adapter-dir (Join-Path $LoraRoot "student_qwen25_05b_lora\final_adapter") `
    --max-seq-length $MaxSeqLength `
    --epochs $Epochs `
    --per-device-train-batch-size $TrainBatchSize `
    --per-device-eval-batch-size $EvalBatchSize `
    --gradient-accumulation-steps 1 `
    --learning-rate $LearningRate `
    --lora-r $LoraRank `
    --lora-alpha $LoraAlpha `
    --lora-dropout 0.05 `
    --target-modules qwen `
    --dtype auto `
    --packing `
    --gradient-checkpointing `
    --optim adamw_torch_fused `
    --dataloader-num-workers 4
if ($LASTEXITCODE -ne 0) {
    throw "LoRA training failed with exit code $LASTEXITCODE"
}

& $PythonExe evaluate_student_lora.py `
    --model-name $BaseModelPath `
    --adapter-dir (Join-Path $LoraRoot "student_qwen25_05b_lora\final_adapter") `
    --test-jsonl (Join-Path $LoraRoot "student_qwen25_05b_lora\data\test.jsonl") `
    --eval-dir (Join-Path $LoraRoot "student_qwen25_05b_lora\eval") `
    --limit $EvalLimit `
    --dtype fp16
if ($LASTEXITCODE -ne 0) {
    throw "Student evaluation failed with exit code $LASTEXITCODE"
}

    $finalStatus = [ordered]@{
        status = "completed"
        started_at = $initialStatus.started_at
        ended_at = (Get-Date).ToString("s")
        lora_root = $LoraRoot
        final_adapter = (Join-Path $LoraRoot "student_qwen25_05b_lora\final_adapter")
        eval_dir = (Join-Path $LoraRoot "student_qwen25_05b_lora\eval")
        transcript = $TranscriptPath
    }
    $finalStatus | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
    Write-Host "Training completed at $(Get-Date -Format s)"
    Write-Host "Final adapter: $($finalStatus.final_adapter)"
    Write-Host "Eval dir: $($finalStatus.eval_dir)"
}
catch {
    $failedStatus = [ordered]@{
        status = "failed"
        ended_at = (Get-Date).ToString("s")
        lora_root = $LoraRoot
        transcript = $TranscriptPath
        error = $_.Exception.Message
    }
    $failedStatus | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
    throw
}
finally {
    Stop-Transcript | Out-Null
}
