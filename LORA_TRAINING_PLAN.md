# Qwen2.5-0.5B LoRA Student Training Plan

## Goal

Train a local student recommendation model with supervised instruction-response distillation.
Large training files are kept under:

```text
E:\CPS5802_Qwen_LoRA
```

The downloaded base model is stored locally at:

```text
E:\CPS5802_Qwen_LoRA\base_models\Qwen2.5-0.5B-Instruct
```

- Teacher data: `Qwen2.5-7B-Instruct` generated recommendation rows.
- Student base model: `Qwen/Qwen2.5-0.5B-Instruct`.
- Training method: LoRA SFT.
- Final artifact: `Qwen2.5-0.5B-Instruct + final_adapter`.

## Data

Source:

```text
model_outputs/distillation/qwen25_7b_distillation_dataset_full.csv
```

Use only:

```text
quality_status == "passed"
```

Current usable data:

- 2938 passed samples.
- Roughly 3.0M to 3.35M total tokens per epoch.
- Split produced by `prepare_qwen25_lora_dataset.py`:
  - 85% train
  - 10% validation
  - 5% test

## Recommended Hardware Profile

For the user's i9-13900 / 64GB RAM / RTX A5000 24GB:

- Use fp16 or bf16 auto-detected by PyTorch.
- Use max sequence length 2048.
- Use packed training.
- Start with batch size 24.
- If VRAM remains below roughly 20GB, try batch size 32.

Expected training time:

- Smoke test: minutes.
- Main LoRA run, r=32, 3 epochs: roughly 30 to 75 minutes.
- Optional 5-epoch run: roughly 50 to 120 minutes.

## One-Time Environment Setup

```powershell
.\setup_qwen_lora_env.ps1
```

This creates:

```text
E:\CPS5802_Qwen_LoRA\.venv_qwen_lora/
```

## Main Training Run

```powershell
.\run_train_qwen25_05b_lora_a5000.ps1
```

Outputs:

```text
E:\CPS5802_Qwen_LoRA\student_qwen25_05b_lora/
  data/
    train.jsonl
    validation.jsonl
    test.jsonl
    dataset_metadata.json
  checkpoints/
  final_adapter/
    adapter_config.json
    adapter_model.safetensors
    tokenizer files
    training_config.json
  eval/
    student_sample_outputs.csv
    student_eval_scores.csv
    student_eval_summary.csv
```

## Manual Commands

Prepare data:

```powershell
.\.venv_qwen_lora\Scripts\python.exe prepare_qwen25_lora_dataset.py
```

Train:

```powershell
.\.venv_qwen_lora\Scripts\python.exe train_qwen25_05b_lora.py --epochs 3 --per-device-train-batch-size 24 --lora-r 32 --packing
```

Evaluate:

```powershell
.\.venv_qwen_lora\Scripts\python.exe evaluate_student_lora.py --limit 100
```

Run one inference:

```powershell
.\.venv_qwen_lora\Scripts\python.exe run_student_inference.py --sample-index 0
```

## Tuning Notes

If GPU memory is underused on RTX A5000:

1. Increase `--per-device-train-batch-size` from 24 to 32.
2. If still underused, try `--lora-r 64 --lora-alpha 128`.
3. Keep `--max-seq-length 2048` unless validation shows truncation.

If training runs out of memory:

1. Lower batch size to 16.
2. Keep packing enabled.
3. Keep gradient checkpointing enabled.

## Reporting Language

Use this wording in the report:

> We used Qwen2.5-7B-Instruct as the teacher model to generate instruction-response distillation data, then fine-tuned Qwen2.5-0.5B-Instruct with LoRA as a lightweight student recommendation model.
