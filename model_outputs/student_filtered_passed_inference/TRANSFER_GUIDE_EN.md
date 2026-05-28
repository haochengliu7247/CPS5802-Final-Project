# Three-Student Inference Result Transfer Guide

Generated: 2026-05-24 05:05
Result folder: `student_filtered_passed_inference_A5000_transfer_20260524_050536`

## Folder Contents

`student_filtered_passed_inference/` is the complete inference result folder. It can be copied directly under the project's `model_outputs/` directory.

`student_filtered_passed_inference_A5000_results.zip` is a compressed copy of the same result set, intended for transfer.

## Result Contents

The `student_filtered_passed_inference` folder should contain:

- `common_passed_input.jsonl`
- `common_passed_person_index.csv`
- `latest_progress.json`
- `controller_status.json`
- `student_from_qwen/`
- `student_from_llama/`
- `student_from_both/`

Each student folder contains:

- `student_sample_outputs.csv`
- `student_eval_scores.csv`
- `student_eval_summary.csv`
- `inference_progress.log`

## How To Move Results Back To The Local Project

Option A: copy `student_filtered_passed_inference/` directly into the local project's `model_outputs/` directory.

Expected destination:

```text
model_outputs/student_filtered_passed_inference/
```

Option B: extract `student_filtered_passed_inference_A5000_results.zip` in the project root and confirm that the final path is `model_outputs/student_filtered_passed_inference/`.

## Verification

Run this from the project root:

```powershell
python run_student_inference.py --help
```

## Important Notes

- This run does not force all 3000 rows.
- It uses the common-passed filtered input where both Qwen teacher and Llama teacher passed quality checks.
- The final aligned row count is 2933.
- The three students use the same `common_passed_input.jsonl`, so the outputs can be compared directly.
- This transfer package contains inference results. For result analysis only, the base model and LoRA adapter do not need to be transferred.
- The three student outputs were verified on the A5000 machine: each `student_sample_outputs.csv` has 2933 rows and no empty `student_response` values.
