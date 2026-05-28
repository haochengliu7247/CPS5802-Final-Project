# Training Data Filtering Checklist

This folder collects the checklist used to filter teacher distillation data before LoRA student training.

## Summary

The same filtering checklist is used for the Qwen2.5-7B teacher data and the Llama 3.1 8B teacher data.

The single-teacher student datasets keep only rows where:

- `quality_status == "passed"`

The teacher generation scripts assign `quality_status = "passed"` only when all required headings are present and no forbidden safety pattern is detected.

The multi-teacher merge applies a stricter explicit filter:

- `quality_status == "passed"`
- `teacher_response` is not empty
- `missing_headings` is empty
- `forbidden_hits` is empty

## Required Headings

Each teacher response must include all of these headings:

1. `Brief Profile Summary`
2. `Main Risk Signals`
3. `Personalized Recommendations`
4. `Why These Recommendations Match This User`
5. `Medical Disclaimer`

## Forbidden Safety Patterns

Rows are rejected or marked `review_needed` if the response contains unsafe wording such as:

- `actual age`
- `chronological age`
- `diagnosed`
- `you have diabetes/hypertension/heart disease/kidney disease`
- `medication adjustment`
- `nicotine replacement`
- `prescribe`
- dosage wording like `take 10 mg`

## Source Files

- `generate_qwen_distillation_dataset.py`
- `generate_qwen_distillation_dataset_resumable.py`
- `generate_llama31_distillation_dataset.py`
- `generate_llama31_distillation_dataset_resumable.py`
- `prepare_qwen25_lora_dataset.py`
- `backup/MultiTeacher_Qwen_Llama_QwenStudent_Minimal_RunPackage_20260522_235120/scripts/merge_multiteacher_distillation_dataset.py`

## Confirmed Counts

- Qwen2.5-7B teacher: 3000 total rows, 2938 passed rows.
- Llama 3.1 8B teacher: 3000 total rows, 2995 passed rows.
- Multi-teacher merged dataset: 5933 passed rows.

