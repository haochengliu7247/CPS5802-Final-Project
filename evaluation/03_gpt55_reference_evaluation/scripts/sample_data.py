import json
import random
from pathlib import Path

import pandas as pd


# Editable mapping section.
# These paths and columns are inferred from the current project structure.
RANDOM_SEED = 42
SAMPLES_PER_MODEL = 50

ORIGINAL_DATA_PATH = Path("model_outputs") / "reports" / "step21_five_model_common_passed_outputs_long.csv"
TEST_PROFILE_PATH = Path("Test.csv")
CHECKLIST_WORKBOOK_PATH = (
    Path("evaluation") / "checklist"
    / "Guideline-derived evaluation checklist"
    / "Guideline-derived evaluation checklist.xlsx"
)
CHECKLIST_SHEET_NAME = "Checklist Scorecard"

COLUMN_MAPPING = {
    "question_id_source": "person_index",
    "distillation_id": "distillation_id",
    "predicted_body_age": "predicted_body_age_years",
    "model_key": "model_key",
    "model_answer": "response_text",
    "model_label": "model_label_short",
}

MODEL_ID_MAP = {
    "teacher_qwen25_7b": "M1_teacher_Qwen2.5-7B",
    "teacher_llama31_8b": "M2_teacher_Llama3.1-8B",
    "student_qwen_from_qwen": "M3_student_Qwen2.5-0.5B_from_Qwen2.5-7B",
    "student_qwen_from_llama": "M4_student_Qwen2.5-0.5B_from_Llama3.1-8B",
    "student_qwen_from_both": "M5_student_Qwen2.5-0.5B_from_Qwen2.5-7B_plus_Llama3.1-8B",
}

MODEL_ORDER = list(MODEL_ID_MAP.values())


def project_root():
    return Path(__file__).resolve().parents[3]


def workflow_dir():
    return Path(__file__).resolve().parents[1]


def as_project_path(path):
    path = Path(path)
    return path if path.is_absolute() else project_root() / path


def clean_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def normalize_model_id(model_key):
    if model_key not in MODEL_ID_MAP:
        raise ValueError("Unknown model_key found: {}".format(model_key))
    return MODEL_ID_MAP[model_key]


def extract_professional_checklist():
    workbook_path = as_project_path(CHECKLIST_WORKBOOK_PATH)
    if not workbook_path.exists():
        raise FileNotFoundError(
            "Existing professional checklist workbook was not found: {}".format(workbook_path)
        )

    raw = pd.read_excel(workbook_path, sheet_name=CHECKLIST_SHEET_NAME, header=None)
    header_row_index = None
    for idx, row in raw.iterrows():
        values = [str(value).strip() for value in row.tolist() if pd.notna(value)]
        if {"Domain", "Criterion", "Evaluator check"}.issubset(set(values)):
            header_row_index = idx
            break
    if header_row_index is None:
        raise ValueError("Could not find the checklist scorecard header row in the existing workbook.")

    headers = [str(value).strip() if pd.notna(value) else "" for value in raw.iloc[header_row_index].tolist()]
    table = raw.iloc[header_row_index + 1 :].copy()
    table.columns = headers
    required_cols = ["Domain", "Criterion", "Evaluator check", "Primary source", "Weight", "Type"]
    table = table[[col for col in required_cols if col in table.columns]].dropna(how="all")
    table = table[table["Domain"].notna() & table["Criterion"].notna()]

    if table.empty:
        raise ValueError("The existing checklist table was found, but no checklist rows were extracted.")

    lines = [
        "Existing professional guideline-derived evaluation checklist from:",
        str(CHECKLIST_WORKBOOK_PATH),
        "Sheet: {}".format(CHECKLIST_SHEET_NAME),
        "",
        "Use these criteria as the reference. Do not replace them with a different rubric.",
        "",
    ]
    for _, row in table.iterrows():
        lines.append(
            "- Domain: {domain} | Criterion: {criterion} | Check: {check} | Source: {source} | Weight: {weight} | Type: {type}".format(
                domain=str(row.get("Domain", "")).strip(),
                criterion=str(row.get("Criterion", "")).strip(),
                check=str(row.get("Evaluator check", "")).strip(),
                source=str(row.get("Primary source", "")).strip(),
                weight=str(row.get("Weight", "")).strip(),
                type=str(row.get("Type", "")).strip(),
            )
        )
    return "\n".join(lines)


def build_user_question(profile_row, predicted_body_age):
    profile = {column: clean_value(value) for column, value in profile_row.to_dict().items()}
    profile["Predicted Body Age (years)"] = clean_value(predicted_body_age)
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
    return (
        "Generate educational, personalized lifestyle recommendations for the following synthetic health profile. "
        "Use the predicted body age only as a contextual risk signal, not as actual chronological age. "
        "Do not diagnose disease and do not give medication instructions.\n\n"
        "Synthetic profile JSON:\n{}".format(profile_json)
    )


def write_excel(df, path):
    try:
        df.to_excel(path, index=False)
    except ImportError as exc:
        raise ImportError("Excel export requires openpyxl. Install openpyxl or use the CSV output.") from exc


def main():
    root = project_root()
    wf_dir = workflow_dir()
    sampled_dir = wf_dir / "sampled_data"
    sampled_dir.mkdir(parents=True, exist_ok=True)

    data_path = as_project_path(ORIGINAL_DATA_PATH)
    profile_path = as_project_path(TEST_PROFILE_PATH)
    outputs = pd.read_csv(data_path)
    profiles = pd.read_csv(profile_path)
    checklist_text = extract_professional_checklist()

    required_columns = set(COLUMN_MAPPING.values())
    missing_columns = required_columns.difference(outputs.columns)
    if missing_columns:
        raise ValueError("Original data is missing columns: {}".format(sorted(missing_columns)))

    outputs = outputs.copy()
    outputs["model_id"] = outputs[COLUMN_MAPPING["model_key"]].map(MODEL_ID_MAP)
    if outputs["model_id"].isna().any():
        missing_models = sorted(outputs.loc[outputs["model_id"].isna(), COLUMN_MAPPING["model_key"]].unique())
        raise ValueError("Unmapped model keys: {}".format(missing_models))

    question_col = COLUMN_MAPPING["question_id_source"]
    model_counts = outputs.groupby(question_col)["model_id"].nunique()
    shared_question_values = sorted(model_counts[model_counts == len(MODEL_ID_MAP)].index.tolist())

    sampling_mode = "shared_question_id"
    fallback_reason = ""
    rng = random.Random(RANDOM_SEED)

    if len(shared_question_values) >= SAMPLES_PER_MODEL:
        selected_question_values = sorted(rng.sample(shared_question_values, SAMPLES_PER_MODEL))
        sampled = outputs[outputs[question_col].isin(selected_question_values)].copy()
        sampled["sample_order"] = sampled[question_col].map(
            {question: order for order, question in enumerate(selected_question_values, start=1)}
        )
    else:
        sampling_mode = "fallback_per_model"
        fallback_reason = (
            "Only {} shared question_id values existed across all five models; "
            "sampled separately by model instead.".format(len(shared_question_values))
        )
        pieces = []
        for model_id in MODEL_ORDER:
            model_df = outputs[outputs["model_id"] == model_id]
            if len(model_df) < SAMPLES_PER_MODEL:
                raise ValueError("Not enough rows for {}: found {}".format(model_id, len(model_df)))
            pieces.append(model_df.sample(n=SAMPLES_PER_MODEL, random_state=RANDOM_SEED).copy())
        sampled = pd.concat(pieces, ignore_index=True)
        sampled["sample_order"] = sampled.groupby("model_id").cumcount() + 1

    sampled["model_order"] = sampled["model_id"].map({model_id: idx for idx, model_id in enumerate(MODEL_ORDER)})
    sampled = sampled.sort_values(["sample_order", "model_order"]).reset_index(drop=True)

    rows = []
    for idx, row in sampled.iterrows():
        person_index = int(row[question_col])
        if person_index < 0 or person_index >= len(profiles):
            raise ValueError("person_index out of range for Test.csv: {}".format(person_index))
        profile_row = profiles.iloc[person_index]
        question_id = "Q{:04d}".format(person_index)
        eval_id = "E{:04d}".format(idx + 1)
        rows.append(
            {
                "eval_id": eval_id,
                "question_id": question_id,
                "model_id": row["model_id"],
                "user_question": build_user_question(profile_row, row[COLUMN_MAPPING["predicted_body_age"]]),
                "model_answer": row[COLUMN_MAPPING["model_answer"]],
                "professional_medical_checklist": checklist_text,
                "person_index": person_index,
                "distillation_id": row[COLUMN_MAPPING["distillation_id"]],
                "predicted_body_age_years": row[COLUMN_MAPPING["predicted_body_age"]],
                "original_model_key": row[COLUMN_MAPPING["model_key"]],
                "model_label_short": row[COLUMN_MAPPING["model_label"]],
                "source": str(ORIGINAL_DATA_PATH),
                "sampling_mode": sampling_mode,
            }
        )

    sampled_df = pd.DataFrame(rows)
    csv_path = sampled_dir / "sampled_250_rows.csv"
    xlsx_path = sampled_dir / "sampled_250_rows.xlsx"
    sampled_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    write_excel(sampled_df, xlsx_path)

    report_lines = [
        "Manual GPT-5.5 reference judge sampling report",
        "===============================================",
        "",
        "random_seed: {}".format(RANDOM_SEED),
        "samples_per_model: {}".format(SAMPLES_PER_MODEL),
        "sampling_mode: {}".format(sampling_mode),
        "fallback_reason: {}".format(fallback_reason or "N/A"),
        "original_data_path: {}".format(data_path.relative_to(root)),
        "test_profile_path: {}".format(profile_path.relative_to(root)),
        "checklist_workbook_path: {}".format(as_project_path(CHECKLIST_WORKBOOK_PATH).relative_to(root)),
        "shared_question_id_count_available: {}".format(len(shared_question_values)),
        "sampled_question_id_count: {}".format(sampled_df["question_id"].nunique()),
        "sampled_row_count: {}".format(len(sampled_df)),
        "",
        "Rows by model_id:",
        sampled_df["model_id"].value_counts().reindex(MODEL_ORDER).to_string(),
        "",
        "Model identities are retained only in local CSV/XLSX files for aggregation.",
        "The prompt-generation script hides model_id and teacher/student labels from GPT-5.5.",
    ]
    (sampled_dir / "sampling_report.txt").write_text("\n".join(report_lines), encoding="utf-8")

    print("Saved:", csv_path)
    print("Saved:", xlsx_path)
    print("Saved:", sampled_dir / "sampling_report.txt")
    print("Sampling mode:", sampling_mode)
    print("Rows:", len(sampled_df), "Shared questions:", sampled_df["question_id"].nunique())


if __name__ == "__main__":
    main()
