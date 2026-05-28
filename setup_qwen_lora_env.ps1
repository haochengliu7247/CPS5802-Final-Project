param(
    [string]$LoraRoot = "E:\CPS5802_Qwen_LoRA",
    [string]$VenvPath = "",
    [string]$PythonVersion = "3.12",
    [string]$PythonExe = "",
    [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu121"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$LoraRoot = [System.IO.Path]::GetFullPath($LoraRoot)
if ([string]::IsNullOrWhiteSpace($VenvPath)) {
    $VenvPath = Join-Path $LoraRoot ".venv_qwen_lora"
}
$VenvPath = [System.IO.Path]::GetFullPath($VenvPath)

New-Item -ItemType Directory -Force -Path $LoraRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $LoraRoot "pip_cache") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $LoraRoot "tmp") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $LoraRoot "huggingface_cache") | Out-Null

$env:QWEN_LORA_ROOT = $LoraRoot
$env:HF_HOME = Join-Path $LoraRoot "huggingface_cache"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $env:HF_HOME "hub"
$env:TRANSFORMERS_CACHE = Join-Path $env:HF_HOME "transformers"
$env:HF_DATASETS_CACHE = Join-Path $env:HF_HOME "datasets"
$env:PIP_CACHE_DIR = Join-Path $LoraRoot "pip_cache"
$env:TEMP = Join-Path $LoraRoot "tmp"
$env:TMP = Join-Path $LoraRoot "tmp"
$env:TOKENIZERS_PARALLELISM = "false"

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonExe = "py"
    }
    elseif (Test-Path -LiteralPath "D:\ANACONDA\python.exe") {
        $PythonExe = "D:\ANACONDA\python.exe"
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonExe = (Get-Command python).Source
    }
    else {
        throw "No usable Python was found. Install Python 3.10/3.11/3.12 or rerun with -PythonExe pointing to python.exe."
    }
}

Write-Host "Creating virtual environment: $VenvPath"
if ($PythonExe -eq "py") {
    & py "-$PythonVersion" -m venv $VenvPath
}
else {
    & $PythonExe -m venv $VenvPath
}
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create venv with $PythonExe. Check that it points to a real Python 3.10/3.11/3.12 executable."
}

$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
if (!(Test-Path -LiteralPath $PythonExe)) {
    throw "Virtual environment Python was not created: $PythonExe"
}

Write-Host "Upgrading pip tooling"
& $PythonExe -m pip install --upgrade pip setuptools wheel

Write-Host "Installing PyTorch CUDA build from $TorchIndexUrl"
& $PythonExe -m pip install torch torchvision torchaudio --index-url $TorchIndexUrl

Write-Host "Installing Qwen LoRA training dependencies"
& $PythonExe -m pip install -r requirements-qwen-lora.txt

Write-Host "Verifying training environment"
& $PythonExe -c "import torch, transformers, datasets, peft, accelerate; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('cuda', torch.version.cuda); print('gpu', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only'); print('transformers', transformers.__version__); print('peft', peft.__version__)"

Write-Host ""
Write-Host "LoRA root: $LoraRoot"
Write-Host "HF cache: $env:HF_HOME"
Write-Host "Pip cache: $env:PIP_CACHE_DIR"
Write-Host "Done. Activate with:"
Write-Host "  $VenvPath\Scripts\Activate.ps1"
