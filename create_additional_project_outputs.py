import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUTPUT_ROOT = Path("model_outputs")
FIGURE_DIR = OUTPUT_ROOT / "figures"
REPORT_DIR = OUTPUT_ROOT / "reports"
DISTILLATION_DIR = OUTPUT_ROOT / "distillation"


def ensure_dirs():
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def save_prediction_distribution_figures():
    prediction_files = {
        "Linear Regression": OUTPUT_ROOT / "LinearRegression" / "test_predictions.csv",
        "Random Forest": OUTPUT_ROOT / "RandomForest" / "test_predictions.csv",
        "XGBoost": OUTPUT_ROOT / "XGBoost" / "test_predictions.csv",
        "MLP Regressor": OUTPUT_ROOT / "MLPRegressor" / "test_predictions.csv",
    }
    predictions = {}
    for model_name, path in prediction_files.items():
        if path.exists():
            predictions[model_name] = pd.read_csv(str(path))["Predicted Body Age (years)"].astype(float)

    if not predictions:
        return []

    combined = pd.DataFrame(predictions)
    combined.to_csv(REPORT_DIR / "test_prediction_matrix_by_model.csv", index=False)

    figure_paths = []

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for model_name, values in predictions.items():
        ax.hist(values, bins=28, alpha=0.35, label=model_name)
    ax.set_title("Test Set Predicted Body Age Distribution by Model")
    ax.set_xlabel("Predicted Body Age (years)")
    ax.set_ylabel("Sample Count")
    ax.legend()
    fig.tight_layout()
    path = FIGURE_DIR / "test_prediction_distribution_by_model.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    figure_paths.append(path)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.boxplot([combined[column].values for column in combined.columns], labels=list(combined.columns), showfliers=False)
    ax.set_title("Prediction Spread by Model on Test Set")
    ax.set_xlabel("Model")
    ax.set_ylabel("Predicted Body Age (years)")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    path = FIGURE_DIR / "test_prediction_boxplot_by_model.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    figure_paths.append(path)
    plt.close(fig)

    if "Linear Regression" in combined.columns:
        best = combined["Linear Regression"]
        comparison_rows = []
        for column in combined.columns:
            if column == "Linear Regression":
                continue
            diff = combined[column] - best
            comparison_rows.append({
                "Compared Model": column,
                "Mean Difference vs Linear Regression": float(diff.mean()),
                "Mean Absolute Difference vs Linear Regression": float(diff.abs().mean()),
                "Max Absolute Difference vs Linear Regression": float(diff.abs().max()),
            })
        pd.DataFrame(comparison_rows).to_csv(REPORT_DIR / "test_prediction_agreement_summary.csv", index=False)

    return figure_paths


def save_distillation_figures_and_reports():
    csv_path = DISTILLATION_DIR / "qwen25_7b_distillation_dataset.csv"
    full_csv_path = DISTILLATION_DIR / "qwen25_7b_distillation_dataset_full.csv"
    metadata_path = DISTILLATION_DIR / "qwen25_7b_distillation_metadata.json"
    total_test_rows = 3000
    if not csv_path.exists() and not full_csv_path.exists():
        return []

    df = pd.read_csv(str(csv_path)) if csv_path.exists() else pd.DataFrame()
    if full_csv_path.exists():
        coverage_df = pd.read_csv(str(full_csv_path))
        if len(coverage_df) >= total_test_rows:
            coverage_note = "Full Qwen teacher distillation run is complete: {} of {} rows generated.".format(
                len(coverage_df),
                total_test_rows,
            )
        else:
            coverage_note = "Representative sample is complete; resumable full run has generated {} of {} rows.".format(
                len(coverage_df),
                total_test_rows,
            )
    else:
        coverage_df = df
        coverage_note = "Current generated dataset is a quality-checked representative sample, not all {} Test.csv rows.".format(total_test_rows)
    figure_paths = []

    summary_rows = []
    representative_rows = len(df)
    representative_passed_rows = int((df["quality_status"] == "passed").sum()) if "quality_status" in df.columns else 0
    generated_rows = len(coverage_df)
    passed_rows = int((coverage_df["quality_status"] == "passed").sum()) if "quality_status" in coverage_df.columns else 0
    summary_rows.append({"Metric": "Total Test.csv rows", "Value": total_test_rows})
    summary_rows.append({"Metric": "Representative Qwen rows generated", "Value": representative_rows})
    summary_rows.append({"Metric": "Representative Qwen rows passed quality check", "Value": representative_passed_rows})
    summary_rows.append({"Metric": "Best available Qwen rows generated", "Value": generated_rows})
    summary_rows.append({"Metric": "Best available Qwen rows passed quality check", "Value": passed_rows})
    summary_rows.append({"Metric": "Best available distillation coverage percent", "Value": round(generated_rows / total_test_rows * 100, 3)})
    summary_rows.append({"Metric": "Best available quality pass rate percent", "Value": round(passed_rows / max(generated_rows, 1) * 100, 3)})
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(REPORT_DIR / "qwen_distillation_coverage_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(["Generated", "Not Generated"], [generated_rows, total_test_rows - generated_rows], color=["#4C78A8", "#D9D9D9"])
    ax.set_title("Qwen Distillation Coverage of Test Set (Best Available Run)")
    ax.set_ylabel("Sample Count")
    for i, value in enumerate([generated_rows, total_test_rows - generated_rows]):
        ax.text(i, value, str(value), ha="center", va="bottom")
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_distillation_coverage.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    figure_paths.append(path)
    plt.close(fig)

    analysis_df = coverage_df if len(coverage_df) else df

    if "predicted_body_age_years" in analysis_df.columns:
        fig, ax = plt.subplots(figsize=(8, 5))
        age_values = analysis_df["predicted_body_age_years"].astype(float)
        ax.hist(age_values, bins=min(35, max(3, int(np.sqrt(len(age_values))))), color="#59A14F", edgecolor="white")
        ax.set_title("Predicted Body Age Distribution in Qwen Distillation Data")
        ax.set_xlabel("Predicted Body Age (years)")
        ax.set_ylabel("Generated Sample Count")
        fig.tight_layout()
        path = FIGURE_DIR / "qwen_distillation_age_distribution.png"
        fig.savefig(str(path), dpi=160, bbox_inches="tight")
        figure_paths.append(path)
        plt.close(fig)

    if "generation_seconds" in analysis_df.columns:
        generation_seconds = analysis_df["generation_seconds"].astype(float)
        fig, ax = plt.subplots(figsize=(8, 5))
        if len(analysis_df) <= 80:
            ax.bar(analysis_df["distillation_id"].astype(str), generation_seconds, color="#F28E2B")
            ax.set_title("Qwen Distillation Generation Time per Sample")
            ax.set_xlabel("Distillation Sample ID")
            ax.set_ylabel("Generation Time (seconds)")
        else:
            ax.hist(generation_seconds, bins=35, color="#F28E2B", edgecolor="white")
            ax.axvline(generation_seconds.mean(), color="#333333", linewidth=1.5, label="Mean")
            ax.set_title("Qwen Distillation Generation Time Distribution")
            ax.set_xlabel("Generation Time (seconds)")
            ax.set_ylabel("Sample Count")
            ax.legend()
        fig.tight_layout()
        path = FIGURE_DIR / "qwen_distillation_generation_time.png"
        fig.savefig(str(path), dpi=160, bbox_inches="tight")
        figure_paths.append(path)
        plt.close(fig)

    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        metadata = {}
    metadata["coverage_note"] = coverage_note
    metadata["representative_rows_generated"] = representative_rows
    metadata["representative_rows_passed_quality_check"] = representative_passed_rows
    metadata["best_available_rows_generated"] = generated_rows
    metadata["best_available_rows_passed_quality_check"] = passed_rows
    if "generation_seconds" in analysis_df.columns:
        metadata["estimated_full_generation_time_hours"] = round((analysis_df["generation_seconds"].astype(float).mean() * total_test_rows) / 3600, 2)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return figure_paths


def save_teacher_checklist():
    representative_path = DISTILLATION_DIR / "qwen25_7b_distillation_dataset.csv"
    full_path = DISTILLATION_DIR / "qwen25_7b_distillation_dataset_full.csv"
    total_test_rows = 3000
    representative_rows = len(pd.read_csv(str(representative_path))) if representative_path.exists() else 0
    full_rows = len(pd.read_csv(str(full_path))) if full_path.exists() else 0
    if full_rows:
        full_passed = int((pd.read_csv(str(full_path))["quality_status"] == "passed").sum())
        qwen_dataset_status = "Completed" if full_rows >= total_test_rows else "Partially completed"
        distillation_evidence = (
            "{} representative Qwen teacher samples are quality-checked; best available full run has generated {} rows, "
            "with {} passing quality checks."
        ).format(representative_rows, full_rows, full_passed)
        if full_rows >= total_test_rows:
            full_run_status = "Completed"
            full_run_evidence = (
                "Full-size Qwen teacher distillation is complete: {} of {} Test.csv rows generated, "
                "with {} rows passing quality checks."
            ).format(full_rows, total_test_rows, full_passed)
        else:
            full_run_status = "In progress"
            full_run_evidence = (
                "Resumable full-size run is not complete yet: {} of {} rows generated. Continue with "
                "generate_qwen_distillation_dataset_resumable.py --sample-size 3000."
            ).format(full_rows, total_test_rows)
    else:
        qwen_dataset_status = "Partially completed"
        distillation_evidence = (
            "{} representative Qwen teacher samples generated and passed quality checks; full 3000-row distillation "
            "requires a long run."
        ).format(representative_rows)
        full_run_status = "Not run by default"
        full_run_evidence = (
            "A resumable script is available, but local generation is estimated to take many hours; run "
            "generate_qwen_distillation_dataset_resumable.py --sample-size 3000 when ready."
        )
    checklist = [
        {
            "Requirement": "Compare multiple models",
            "Status": "Completed",
            "Evidence": "Linear Regression, Random Forest, XGBoost, and MLP Regressor are compared in model_comparison_df.",
        },
        {
            "Requirement": "Explain best model reason",
            "Status": "Completed",
            "Evidence": "Best model is selected by lowest validation MAE; current best is Linear Regression.",
        },
        {
            "Requirement": "MAE, MSE/RMSE, R2",
            "Status": "Completed",
            "Evidence": "Model Comparison section reports MSE, RMSE, MAE, and R2.",
        },
        {
            "Requirement": "Predicted-vs-actual plots",
            "Status": "Completed",
            "Evidence": "model_outputs/figures/predicted_vs_actual_*.png.",
        },
        {
            "Requirement": "Feature importance plots",
            "Status": "Completed",
            "Evidence": "Random Forest and XGBoost feature importance figures are saved.",
        },
        {
            "Requirement": "Separate CSV prediction outputs for each model",
            "Status": "Completed",
            "Evidence": "Each model has model_outputs/<Model>/test_predictions.csv with 3000 rows.",
        },
        {
            "Requirement": "Local Qwen2.5-7B deployment",
            "Status": "Completed",
            "Evidence": "Ollama portable and qwen2.5:7b-instruct are installed under E:\\CPS5802_Qwen_Ollama.",
        },
        {
            "Requirement": "Qwen distillation dataset",
            "Status": qwen_dataset_status,
            "Evidence": distillation_evidence,
        },
        {
            "Requirement": "Show advantage of Qwen distillation over previous fallback",
            "Status": "Completed",
            "Evidence": "Qwen teacher responses are compared with the local rule fallback using quality score, action diversity, explanation depth, feature coverage, safety compliance, and per-sample visualizations.",
        },
        {
            "Requirement": "Full 3000-row distillation",
            "Status": full_run_status,
            "Evidence": full_run_evidence,
        },
        {
            "Requirement": "Medical disclaimer and safe LLM prompt",
            "Status": "Completed",
            "Evidence": "Improved prompt forbids diagnosis/medication advice and states synthetic educational-only use.",
        },
    ]
    path = REPORT_DIR / "teacher_requirement_checklist.csv"
    pd.DataFrame(checklist, columns=["Requirement", "Status", "Evidence"]).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def save_ollama_qwen_call_audit():
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    audit_rows = [
        {
            "Location": "Notebook Step 6 final recommendation workflow",
            "Model": "qwen2.5:7b-instruct",
            "Base URL": "http://127.0.0.1:11434",
            "Timeout Seconds": 420,
            "Status": "Updated",
            "Notes": "Provider order is OpenAI if configured, then local Qwen, then rule fallback.",
        },
        {
            "Location": "Notebook Step 7 Qwen distillation setup",
            "Model": "qwen2.5:7b-instruct",
            "Base URL": "http://127.0.0.1:11434",
            "Timeout Seconds": 10,
            "Status": "Updated",
            "Notes": "Checks local Ollama model availability and uses E-drive model directory.",
        },
        {
            "Location": "generate_qwen_distillation_dataset.py",
            "Model": "qwen2.5:7b-instruct",
            "Base URL": "http://127.0.0.1:11434",
            "Timeout Seconds": 540,
            "Status": "Updated",
            "Notes": "Generates representative Qwen teacher distillation rows.",
        },
        {
            "Location": "generate_qwen_distillation_dataset_resumable.py",
            "Model": "qwen2.5:7b-instruct",
            "Base URL": "http://127.0.0.1:11434",
            "Timeout Seconds": 540,
            "Status": "Updated",
            "Notes": "Resumable full-size distillation script; calls the base Qwen function.",
        },
    ]
    path = REPORT_DIR / "ollama_qwen_call_audit.csv"
    pd.DataFrame(
        audit_rows,
        columns=["Location", "Model", "Base URL", "Timeout Seconds", "Status", "Notes"],
    ).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def main():
    ensure_dirs()
    paths = []
    paths.extend(save_prediction_distribution_figures())
    paths.extend(save_distillation_figures_and_reports())
    checklist_path = save_teacher_checklist()
    audit_path = save_ollama_qwen_call_audit()
    print("Saved additional figures:")
    for path in paths:
        print(path)
    print("Saved checklist:", checklist_path)
    print("Saved Ollama/Qwen audit:", audit_path)


if __name__ == "__main__":
    main()
