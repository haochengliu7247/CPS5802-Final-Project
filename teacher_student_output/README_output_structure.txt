Teacher and Student Output Directory Guide

Generated: 2026-05-24

Purpose

This folder is an organized delivery copy for displaying, checking, and judging the five LLM outputs. The original files remain under model_outputs/; this folder is a clearer presentation copy.

Overall structure

teacher-student output folder
- teacher output/
  - distillation/
    - teacher_Qwen2.5-7B_output/
    - teacher_Llama_3.1_8B_output/
- student output/
  - shared_filtered_input/
  - run_status_and_logs/
  - student_Qwen2.5-0.5B_from_Qwen2.5-7B_output/
  - student_Qwen2.5-0.5B_from_Llama_3.1_8B_output/
  - student_Qwen2.5-0.5B_from_Qwen2.5-7B_plus_Llama_3.1_8B_output/

Teacher output

teacher output/distillation/teacher_Qwen2.5-7B_output/ contains the complete Qwen2.5-7B teacher distillation output:

- qwen25_7b_distillation_dataset_full.csv
- qwen25_7b_distillation_dataset_full.jsonl
- qwen25_7b_distillation_dataset_full_metadata.json

teacher output/distillation/teacher_Llama_3.1_8B_output/ contains the complete Llama 3.1 8B teacher distillation output:

- llama31_8b_distillation_dataset_full.csv
- llama31_8b_distillation_dataset_full.jsonl
- llama31_8b_distillation_dataset_full_metadata.json

Student output

student output/shared_filtered_input/ contains the common filtered input used by all three students:

- common_passed_input.jsonl
- common_passed_person_index.csv

The students were run on the common-passed filtered input where both Qwen teacher and Llama teacher had quality_status == passed. The expected aligned row count is 2933.

Student folders:

- student_Qwen2.5-0.5B_from_Qwen2.5-7B_output/
- student_Qwen2.5-0.5B_from_Llama_3.1_8B_output/
- student_Qwen2.5-0.5B_from_Qwen2.5-7B_plus_Llama_3.1_8B_output/

Each folder contains:

- student_sample_outputs.csv
- student_eval_scores.csv
- student_eval_summary.csv
- inference_progress.log

run_status_and_logs/ contains A5000 inference status and transfer notes:

- controller_status.json
- latest_progress.json
- TRANSFER_GUIDE_EN.md

Current verification summary

- common_passed_input.jsonl: 2933 rows.
- student_from_qwen: 2933 rows, empty student_response = 0.
- student_from_llama: 2933 rows, empty student_response = 0.
- student_from_both: 2933 rows, empty student_response = 0.
- student_eval_scores.csv has 5866 rows because each person_index has two score records.

Suggested downstream use

1. Read teacher responses from the two teacher distillation CSV files.
2. Read student responses from the three student_sample_outputs.csv files.
3. Use common_passed_person_index.csv or common_passed_input.jsonl to ensure that all five models are compared on the same person_index set.
