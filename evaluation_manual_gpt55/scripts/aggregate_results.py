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


def normalize_bool(value):
    return str(value).strip().upper() == "TRUE"


def top_issues(series, n=5):
    clean = series.fillna("").astype(str).str.strip()
    clean = clean[clean != ""]
    clean = clean[clean.str.lower() != "none"]
    if clean.empty:
        return "none"
    counts = clean.value_counts().head(n)
    return "; ".join("{} ({})".format(issue, count) for issue, count in counts.items())


def load_and_merge():
    wf_dir = workflow_dir()
    sampled_path = wf_dir / "sampled_data" / "sampled_250_rows.csv"
    results_path = wf_dir / "results" / "gpt55_results_filled.csv"
    if not sampled_path.exists():
        raise FileNotFoundError("Sampled data not found. Run sample_data.py first: {}".format(sampled_path))
    if not results_path.exists():
        raise FileNotFoundError("Filled results not found: {}".format(results_path))

    sampled = pd.read_csv(sampled_path, dtype={"eval_id": str})
    results = pd.read_csv(results_path, dtype={"eval_id": str})
    results.columns = [str(column).strip() for column in results.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in results.columns]
    if missing:
        raise ValueError("Filled results missing required columns: {}".format(missing))

    for column in SCORE_COLUMNS:
        results[column] = pd.to_numeric(results[column], errors="raise").astype(int)
    results["overall_pass_bool"] = results["overall_pass"].map(normalize_bool)

    metadata_columns = [
        "eval_id",
        "question_id",
        "model_id",
        "person_index",
        "distillation_id",
        "predicted_body_age_years",
        "original_model_key",
        "model_label_short",
        "sampling_mode",
    ]
    metadata_columns = [column for column in metadata_columns if column in sampled.columns]
    merged = sampled[metadata_columns].merge(results, on="eval_id", how="left", validate="one_to_one")
    return merged


def summarize_overall(merged):
    row = {
        "total_rows": int(len(merged)),
        "overall_pass_rate_percent": float(merged["overall_pass_bool"].mean() * 100),
        "most_common_main_issue_values": top_issues(merged["main_issue"]),
    }
    for column in SCORE_COLUMNS:
        row["average_" + column] = float(merged[column].mean())
    return pd.DataFrame([row])


def summarize_by_model(merged):
    rows = []
    for model_id, group in merged.groupby("model_id", sort=False):
        row = {
            "model_id": model_id,
            "number_of_evaluated_rows": int(len(group)),
            "pass_rate_percent": float(group["overall_pass_bool"].mean() * 100),
            "most_common_main_issue_values": top_issues(group["main_issue"]),
        }
        if "model_label_short" in group.columns:
            row["model_label_short"] = group["model_label_short"].iloc[0]
        for column in SCORE_COLUMNS:
            row["average_" + column] = float(group[column].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    wf_dir = workflow_dir()
    results_dir = wf_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    merged = load_and_merge()
    merged.to_csv(results_dir / "aggregated_results_by_model.csv", index=False, encoding="utf-8-sig")

    summary_overall = summarize_overall(merged)
    summary_by_model = summarize_by_model(merged)
    summary_overall.to_csv(results_dir / "summary_overall.csv", index=False, encoding="utf-8-sig")
    summary_by_model.to_csv(results_dir / "summary_by_model.csv", index=False, encoding="utf-8-sig")

    print("Saved:", results_dir / "aggregated_results_by_model.csv")
    print("Saved:", results_dir / "summary_overall.csv")
    print("Saved:", results_dir / "summary_by_model.csv")
    print(summary_by_model.to_string(index=False))


if __name__ == "__main__":
    main()
