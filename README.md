# CPS5802 Machine Learning Innovations Final Project

This repository contains a completed final project for synthetic human age prediction,
personalized lifestyle recommendation generation, and teacher-student LLM distillation
analysis.

## Project Status

The project is complete and organized for GitHub upload. The main notebook covers
Steps 1-30, from dataset exploration and regression modeling through Qwen/Llama
teacher outputs, Qwen2.5-0.5B LoRA student experiments, multi-teacher comparison,
MedGemma judge evaluation, rule-based hard safety checks, a manual GPT-5.5
small-sample reference judge workflow, targeted human review, and the final
triangulated safety/quality comparison.

Main entry point:

```text
human-age-prediction-synthetic-dataset-eda-predict-recommendation-final_project.ipynb
```

## Main Contents

```text
Train.csv / Test.csv                         Synthetic project data
*.py                                         Distillation, LoRA, evaluation, and report scripts
*.ps1                                        Windows PowerShell setup/training helpers
model_outputs/                               Predictions, figures, reports, adapters, and evaluations
model_outputs/rule_based_hard_safety_checks/ Deterministic hard-safety checker outputs
final judge data/                            MedGemma judge outputs for five models
checklist/                                   Evaluation and filtering checklist artifacts
evaluation_manual_gpt55/                     Manual GPT-5.5 reference-judge and human-review workflow
teacher_student_output/                      Organized teacher/student output copy
requirements.txt                             General project dependencies
requirements-qwen-lora.txt                   Original LoRA-focused dependency list
PROJECT_AUDIT_SUMMARY.md                     Five-pass project review summary
GITHUB_UPLOAD_NOTES.md                       Upload and large-file notes
```

## What Was Excluded From This GitHub Copy

The following local/runtime-only material was intentionally left out:

```text
.venv_qwen_lora/
pip_cache/
huggingface_cache/
base_models/
backup/
migration_backups/
tmp/
__pycache__/
*.before_*.ipynb
*.log
*.zip
```

These are local environments, downloaded model caches, backups, duplicate notebook
snapshots, or runtime logs. They are not required for a clean GitHub project.

## Final Evaluation Layers

The final project uses multiple complementary evaluation layers:

1. MedGemma 27B Q4 judge evaluation across the five teacher/student outputs.
2. Rule-based hard safety checks across the aligned 2933-response evaluation set.
3. Manual GPT-5.5 small-sample reference judge workflow with 250 blinded rows.
4. Targeted human review of 20 high-priority ambiguous or high-risk cases.
5. Final triangulated comparison that combines MedGemma, rule-based, GPT-5.5, and
   human-review signals.

The human review is a targeted difficult-case audit, not physician clinical
validation and not an estimate of full-dataset pass rate.

## Setup

Create a Python environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Open the main notebook:

```powershell
jupyter notebook human-age-prediction-synthetic-dataset-eda-predict-recommendation-final_project.ipynb
```

For safer GitHub upload, embedded PNG output data was removed from the copied
notebook. The saved result images remain under `model_outputs/figures/`.

For LoRA training on a CUDA machine, use the included PowerShell helpers and the
original LoRA dependency file:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_qwen_lora_env.ps1
powershell -ExecutionPolicy Bypass -File .\run_train_qwen25_05b_lora_a5000.ps1
```

To reproduce the rule-based hard safety layer:

```powershell
python evaluate_rule_based_hard_safety_checks.py
```

GPT-5.5 reference judge：

```powershell
python evaluation_manual_gpt55/scripts/sample_data.py
python evaluation_manual_gpt55/scripts/make_batch_prompts.py
python evaluation_manual_gpt55/scripts/validate_filled_results.py
python evaluation_manual_gpt55/scripts/aggregate_results.py
```

See `evaluation_manual_gpt55/README_manual_workflow.md` for the copy-paste judging
steps and result aggregation details.

## Notes

- The dataset is synthetic and the recommendation text is educational only.
- The rule-based, GPT-5.5, MedGemma, and human-review layers evaluate structured
  safety/quality signals, not clinical accuracy.
- The notebook can optionally use `OPENAI_API_KEY` if the environment variable is
  provided. No real API keys are included in this repository.
- The base Qwen model weights are not included. Download them from Hugging Face
  when reproducing training or inference.

