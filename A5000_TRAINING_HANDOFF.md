# A5000 Training Handoff: Qwen2.5-0.5B LoRA Student

## Current Project Status

This project has already completed the teacher-data stage.

- Teacher model used: `Qwen2.5-7B-Instruct`
- Teacher data file: `model_outputs/distillation/qwen25_7b_distillation_dataset_full.csv`
- Total teacher rows: `3000`
- Usable training rows: `2938` rows where `quality_status == "passed"`
- Rows excluded from training: `62 review_needed`
- Student base model: `Qwen/Qwen2.5-0.5B-Instruct`
- Training method: LoRA supervised fine-tuning / instruction-response distillation

The training scripts and data preparation scripts are already included in this project folder.

## What To Copy To The A5000 Machine

Copy the entire project folder to the A5000 machine, including:

```text
CPS5802-Machine Learning Innovations final project/
  model_outputs/distillation/qwen25_7b_distillation_dataset_full.csv
  requirements-qwen-lora.txt
  setup_qwen_lora_env.ps1
  prepare_qwen25_lora_dataset.py
  train_qwen25_05b_lora.py
  evaluate_student_lora.py
  run_student_inference.py
  run_train_qwen25_05b_lora_a5000.ps1
  monitor_qwen_lora_training.ps1
```

The A5000 machine only needs C/D drives. Use D drive by default:

```text
D:\CPS5802_Qwen_LoRA
```

This directory will hold the virtual environment, Hugging Face cache, base model, training checkpoints, final adapter, and evaluation outputs.

## Step 1: Verify GPU

Open PowerShell in the project folder and run:

```powershell
nvidia-smi
```

Expected GPU:

```text
RTX A5000 24GB
```

## Step 2: Create Training Environment

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_qwen_lora_env.ps1 -LoraRoot "D:\CPS5802_Qwen_LoRA"
```

This creates:

```text
D:\CPS5802_Qwen_LoRA\.venv_qwen_lora
D:\CPS5802_Qwen_LoRA\huggingface_cache
D:\CPS5802_Qwen_LoRA\pip_cache
D:\CPS5802_Qwen_LoRA\tmp
```

It installs:

- PyTorch CUDA build
- Transformers
- PEFT
- Datasets
- Accelerate
- TensorBoard
- other LoRA training dependencies

## Step 3: Download Qwen2.5-0.5B Base Model To D Drive

Run:

```powershell
$LoraRoot = "D:\CPS5802_Qwen_LoRA"
$env:HF_HOME = Join-Path $LoraRoot "huggingface_cache"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $env:HF_HOME "hub"
$env:TRANSFORMERS_CACHE = Join-Path $env:HF_HOME "transformers"
$env:HF_DATASETS_CACHE = Join-Path $env:HF_HOME "datasets"

& "$LoraRoot\.venv_qwen_lora\Scripts\hf.exe" download Qwen/Qwen2.5-0.5B-Instruct --local-dir "$LoraRoot\base_models\Qwen2.5-0.5B-Instruct"
```

If Hugging Face download is slow or rate-limited, set `HF_TOKEN` before running.

## Step 4: Start Full Training

Run this in PowerShell from the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_train_qwen25_05b_lora_a5000.ps1 -LoraRoot "D:\CPS5802_Qwen_LoRA" -Epochs 3 -TrainBatchSize 24 -EvalBatchSize 24 -MaxSeqLength 2048 -LoraRank 32 -LoraAlpha 64 -LearningRate 1.5e-4 -EvalLimit 100
```

Expected outputs:

```text
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\data
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\checkpoints
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\final_adapter
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\eval
D:\CPS5802_Qwen_LoRA\logs
```

Expected final adapter:

```text
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\final_adapter
```

## Step 5: Real-Time Training Progress Feedback

Open a second PowerShell window in the project folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\monitor_qwen_lora_training.ps1 -LoraRoot "D:\CPS5802_Qwen_LoRA" -IntervalSeconds 30
```

This monitor refreshes every 30 seconds and shows:

- GPU name
- GPU utilization
- GPU memory used / total
- temperature
- power draw
- training/evaluation Python process
- latest training log lines
- latest loss/eval output from transcript

The main training script also writes:

```text
D:\CPS5802_Qwen_LoRA\logs\latest_training_status.json
D:\CPS5802_Qwen_LoRA\logs\train_qwen25_05b_lora_*.transcript.log
```

If the user asks for progress, summarize:

- current status from `latest_training_status.json`
- latest loss lines from transcript
- current GPU memory/utilization from `nvidia-smi`
- whether `final_adapter` exists yet

## Step 6: After Training Finishes

Confirm these files exist:

```text
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\final_adapter\adapter_config.json
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\final_adapter\adapter_model.safetensors
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\final_adapter\training_config.json
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\eval\student_eval_summary.csv
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\eval\student_sample_outputs.csv
```

Run one local inference check:

```powershell
$LoraRoot = "D:\CPS5802_Qwen_LoRA"
$env:QWEN_LORA_ROOT = $LoraRoot
& "$LoraRoot\.venv_qwen_lora\Scripts\python.exe" run_student_inference.py `
  --model-name "$LoraRoot\base_models\Qwen2.5-0.5B-Instruct" `
  --adapter-dir "$LoraRoot\student_qwen25_05b_lora\final_adapter" `
  --sample-jsonl "$LoraRoot\student_qwen25_05b_lora\data\test.jsonl" `
  --sample-index 0 `
  --max-new-tokens 700 `
  --dtype fp16
```

## Step 7: What To Send Back

Send back this folder:

```text
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\final_adapter
```

Also send back evaluation outputs:

```text
D:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\eval
D:\CPS5802_Qwen_LoRA\logs\latest_training_status.json
D:\CPS5802_Qwen_LoRA\logs\train_qwen25_05b_lora_*.transcript.log
```

The base model does not need to be sent back if it already exists locally, but sending only `final_adapter` is not enough for standalone inference; inference requires:

```text
base model + LoRA adapter
```

## Step 8: How To Update The Main Machine With The Trained Adapter

On the main machine, place or unzip the returned `final_adapter` somewhere accessible, then run from the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_trained_lora_adapter.ps1 -SourceAdapterDir "PATH_TO_RETURNED\final_adapter" -LoraRoot "E:\CPS5802_Qwen_LoRA" -AlsoCopyEval
```

This will:

- back up any existing local `final_adapter`
- install the newly trained adapter to:

```text
E:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora\final_adapter
```

- optionally copy evaluation outputs

Then test inference:

```powershell
$env:QWEN_LORA_ROOT = "E:\CPS5802_Qwen_LoRA"
E:\CPS5802_Qwen_LoRA\.venv_qwen_lora\Scripts\python.exe run_student_inference.py --sample-index 0 --max-new-tokens 700
```

## Important Notes

- Do not train on `review_needed` rows.
- Keep `quality_status == "passed"` filtering.
- Do not describe `Predicted Body Age (years)` as chronological age or actual age.
- The current recommended run is LoRA `r=32`, `alpha=64`, `3 epochs`, `max_seq_length=2048`, batch size `24`.
- If A5000 VRAM is underused, rerun later with `-TrainBatchSize 32`.
- If CUDA out-of-memory occurs, rerun with `-TrainBatchSize 16`.
