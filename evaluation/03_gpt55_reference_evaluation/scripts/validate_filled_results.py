from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "eval_id",
    "checklist_coverage",
    "medical_correctness",
    "safety_risk",
    "hallucination",
    "policy_compliance",
    "completeness",
    "reasoning_quality",
    "overall_pass",
    "main_issue",
    "brief_reason",
]

SCORE_COLUMNS = [
    "checklist_coverage",
    "medical_correctness",
    "safety_risk",
    "hallucination",
    "policy_compliance",
    "completeness",
    "reasoning_quality",
]


def workflow_dir():
    return Path(__file__).resolve().parents[1]


def normalize_columns(df):
    df = df.copy()
    df.columns = [str(column).strip() for column in df.columns]
    return df


def main():
    wf_dir = workflow_dir()
    sampled_path = wf_dir / "sampled_data" / "sampled_250_rows.csv"
    results_path = wf_dir / "results" / "gpt55_results_filled.csv"

    if not sampled_path.exists():
        raise FileNotFoundError("Sampled data not found. Run sample_data.py first: {}".format(sampled_path))
    if not results_path.exists():
        raise FileNotFoundError(
            "Filled results not found. Save your manually pasted GPT-5.5 results as: {}".format(results_path)
        )

    sampled = pd.read_csv(sampled_path, dtype={"eval_id": str})
    results = normalize_columns(pd.read_csv(results_path, dtype={"eval_id": str}))

    errors = []
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in results.columns]
    if missing_columns:
        errors.append("Missing required columns: {}".format(missing_columns))

    if "eval_id" in results.columns:
        expected_ids = set(sampled["eval_id"].astype(str))
        actual_ids = set(results["eval_id"].dropna().astype(str))
        missing_ids = sorted(expected_ids.difference(actual_ids))
        extra_ids = sorted(actual_ids.difference(expected_ids))
        duplicate_ids = sorted(results.loc[results["eval_id"].duplicated(), "eval_id"].dropna().astype(str).unique())
        if missing_ids:
            errors.append("Missing eval_id values: {}".format(missing_ids[:50]))
        if extra_ids:
            errors.append("Unexpected eval_id values: {}".format(extra_ids[:50]))
        if duplicate_ids:
            errors.append("Duplicate eval_id values: {}".format(duplicate_ids[:50]))

    for column in SCORE_COLUMNS:
        if column not in results.columns:
            continue
        numeric = pd.to_numeric(results[column], errors="coerce")
        invalid_mask = numeric.isna() | (numeric % 1 != 0) | (numeric < 1) | (numeric > 5)
        if invalid_mask.any():
            bad = results.loc[invalid_mask, ["eval_id", column]].head(20)
            errors.append("Invalid 1-5 integer scores in {}: {}".format(column, bad.to_dict("records")))

    if "overall_pass" in results.columns:
        normalized = results["overall_pass"].astype(str).str.strip().str.upper()
        invalid = ~normalized.isin(["TRUE", "FALSE"])
        if invalid.any():
            bad = results.loc[invalid, ["eval_id", "overall_pass"]].head(20)
            errors.append("Invalid overall_pass values; use TRUE/FALSE: {}".format(bad.to_dict("records")))

    if errors:
        print("Validation failed.")
        for index, error in enumerate(errors, start=1):
            print("{}. {}".format(index, error))
        raise SystemExit(1)

    print("Validation passed.")
    print("All {} expected eval_id values are present exactly once.".format(len(sampled)))
    print("All score columns contain integers from 1 to 5.")
    print("overall_pass contains only TRUE/FALSE.")


if __name__ == "__main__":
    main()
