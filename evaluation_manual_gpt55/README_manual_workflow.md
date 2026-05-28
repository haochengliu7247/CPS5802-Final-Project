# Manual GPT-5.5 Reference Judge Workflow

This folder supports a manual ChatGPT / GPT-5.5 reference-judge workflow. It does not call the OpenAI API, does not require `OPENAI_API_KEY`, and does not use any external API.

The workflow uses the existing professional medical checklist in this project:

`checklist/Guideline-derived evaluation checklist/Guideline-derived evaluation checklist.xlsx`

Model identities are kept in local CSV/XLSX files for aggregation, but they are hidden from the GPT-5.5 batch prompts.

## Step 1

Run:

```powershell
python evaluation_manual_gpt55/scripts/sample_data.py
```

This creates:

- `evaluation_manual_gpt55/sampled_data/sampled_250_rows.csv`
- `evaluation_manual_gpt55/sampled_data/sampled_250_rows.xlsx`
- `evaluation_manual_gpt55/sampled_data/sampling_report.txt`

## Step 2

Run:

```powershell
python evaluation_manual_gpt55/scripts/make_batch_prompts.py
```

This creates:

- `evaluation_manual_gpt55/prompts/batch_prompts/batch_001.md`
- `evaluation_manual_gpt55/prompts/batch_prompts/batch_002.md`
- ...
- `evaluation_manual_gpt55/prompts/all_batches_combined.md`
- `evaluation_manual_gpt55/result_templates/gpt55_results_template.csv`
- `evaluation_manual_gpt55/result_templates/gpt55_results_template.xlsx`

## Step 3

Open:

`evaluation_manual_gpt55/prompts/batch_prompts/batch_001.md`

## Step 4

Copy the full batch prompt into ChatGPT / GPT-5.5.

## Step 5

Copy GPT-5.5 TSV output into Excel.

Use the template:

`evaluation_manual_gpt55/result_templates/gpt55_results_template.xlsx`

or:

`evaluation_manual_gpt55/result_templates/gpt55_results_template.csv`

## Step 6

Repeat for all batch files.

With the default batch size of 10 rows, 250 evaluation rows produce 25 batch files.

## Step 7

Save the filled results as:

`evaluation_manual_gpt55/results/gpt55_results_filled.csv`

Alternative: if ChatGPT / GPT-5.5 returns space-separated text or wraps long reasons across lines, paste all raw batch outputs into:

`evaluation_manual_gpt55/results/gpt55_raw_outputs.txt`

Then run:

```powershell
python evaluation_manual_gpt55/scripts/parse_raw_gpt55_txt.py
```

This will create:

`evaluation_manual_gpt55/results/gpt55_results_filled.csv`

## Step 8

Run:

```powershell
python evaluation_manual_gpt55/scripts/validate_filled_results.py
```

The validator checks that all 250 `eval_id` values are present, no duplicates exist, score columns are integers from 1 to 5, and `overall_pass` uses `TRUE` or `FALSE`.

## Step 9

Run:

```powershell
python evaluation_manual_gpt55/scripts/aggregate_results.py
```

## Step 10

Use these files for the paper/project:

- `evaluation_manual_gpt55/results/summary_by_model.csv`
- `evaluation_manual_gpt55/results/summary_overall.csv`
- `evaluation_manual_gpt55/results/aggregated_results_by_model.csv`

## Privacy Note

Before pasting into ChatGPT, make sure patient identifiers, PHI, confidential institution identifiers, and sensitive metadata are removed. The project data used here is synthetic, but this check is still part of good evaluation hygiene.

## Methodology Note

The selected validation set contains 50 samples per model across five models. When possible, the same 50 medical questions are used across all models to ensure fair comparison. GPT-5.5 is used manually through the ChatGPT interface as a small-scale reference judge. Model identities are hidden during judging to reduce bias. The professional medical checklist is provided as the reference evaluation criterion. Results are pasted into Excel/CSV and aggregated by model.
