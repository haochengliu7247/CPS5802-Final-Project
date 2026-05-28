import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib import request

import numpy as np
import pandas as pd


MODEL_NAME = "qwen2.5:7b-instruct"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_URL = "{}/api/chat".format(OLLAMA_BASE_URL)
OUTPUT_DIR = Path("model_outputs") / "distillation"

# English note: see the surrounding code for this project workflow detail.
# English note: see the surrounding code for this project workflow detail.
# English note: see the surrounding code for this project workflow detail.
os.environ.setdefault("OLLAMA_MODEL", MODEL_NAME)
os.environ.setdefault("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
os.environ.setdefault("OLLAMA_HOST", OLLAMA_BASE_URL.replace("http://", "").replace("https://", ""))
if Path(r"E:\CPS5802_Qwen_Ollama\models").exists():
    os.environ.setdefault("OLLAMA_MODELS", r"E:\CPS5802_Qwen_Ollama\models")

REQUIRED_HEADINGS = [
    "Brief Profile Summary",
    "Main Risk Signals",
    "Personalized Recommendations",
    "Why These Recommendations Match This User",
    "Medical Disclaimer",
]

FORBIDDEN_PATTERNS = [
    r"\bactual age\b",
    r"\bchronological age\b",
    r"\bdiagnosed\b",
    r"\byou have (diabetes|hypertension|heart disease|kidney disease)\b",
    r"\bmedication adjustment",
    r"\bnicotine replacement\b",
    r"\bprescribe",
    r"\btake \d+\s*(mg|milligram)",
]


def is_missing(value):
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip().lower() in {"", "nan", "none", "null"}


def clean_json_value(value):
    if is_missing(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def to_float(value):
    if is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_blood_pressure(value):
    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", str(value or ""))
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def collect_health_signals(profile):
    signals = []
    predicted_age = to_float(profile.get("Predicted Body Age (years)"))
    bmi = to_float(profile.get("BMI"))
    cholesterol = to_float(profile.get("Cholesterol Level (mg/dL)"))
    glucose = to_float(profile.get("Blood Glucose Level (mg/dL)"))
    stress = to_float(profile.get("Stress Levels"))
    systolic, diastolic = parse_blood_pressure(profile.get("Blood Pressure (s/d)"))

    if predicted_age is not None and predicted_age >= 70:
        signals.append("High predicted body age: {:.1f} years".format(predicted_age))
    elif predicted_age is not None and predicted_age >= 55:
        signals.append("Moderately high predicted body age: {:.1f} years".format(predicted_age))

    if bmi is not None:
        if bmi >= 30:
            signals.append("BMI is in the obesity range: {:.1f}".format(bmi))
        elif bmi >= 25:
            signals.append("BMI is elevated: {:.1f}".format(bmi))
        elif bmi < 18.5:
            signals.append("BMI is low: {:.1f}".format(bmi))

    if systolic is not None and diastolic is not None:
        if systolic >= 140 or diastolic >= 90:
            signals.append("High blood pressure reading: {}/{}".format(int(systolic), int(diastolic)))
        elif systolic >= 130 or diastolic >= 80:
            signals.append("Borderline high blood pressure reading: {}/{}".format(int(systolic), int(diastolic)))

    if cholesterol is not None:
        if cholesterol >= 240:
            signals.append("High cholesterol: {:.1f} mg/dL".format(cholesterol))
        elif cholesterol >= 200:
            signals.append("Borderline high cholesterol: {:.1f} mg/dL".format(cholesterol))

    if glucose is not None:
        if glucose >= 126:
            signals.append("High blood glucose: {:.1f} mg/dL".format(glucose))
        elif glucose >= 100:
            signals.append("Borderline high blood glucose: {:.1f} mg/dL".format(glucose))

    activity = str(profile.get("Physical Activity Level") or "").lower()
    if activity == "low":
        signals.append("Low physical activity level")

    smoking = str(profile.get("Smoking Status") or "").lower()
    if smoking == "current":
        signals.append("Current smoking status")
    elif smoking == "former":
        signals.append("Former smoker: relapse prevention")

    alcohol = str(profile.get("Alcohol Consumption") or "").lower()
    if alcohol == "frequent":
        signals.append("Frequent alcohol consumption")

    sleep = str(profile.get("Sleep Patterns") or "").lower()
    if sleep == "insomnia":
        signals.append("Insomnia reported")

    if stress is not None and stress >= 7:
        signals.append("High stress level: {:.1f}".format(stress))

    if not signals:
        signals.append("No major high-risk signal from simple rule screening")

    return signals


def build_profile(row, predicted_age):
    profile = {column: clean_json_value(value) for column, value in row.to_dict().items()}
    profile["Predicted Body Age (years)"] = float(predicted_age)
    profile["key_health_signals"] = collect_health_signals(profile)
    return profile


def build_distillation_instruction():
    return (
        "Generate educational, personalized lifestyle recommendations from a synthetic "
        "health profile and predicted body age. Do not diagnose disease, do not infer "
        "chronological age, and do not give medication instructions."
    )


def build_qwen_prompt(profile):
    profile_json = json.dumps(profile, ensure_ascii=False, indent=2)
    return """
You are a senior preventive medicine and lifestyle medicine physician. This is a synthetic dataset project.
Create an educational lifestyle recommendation for instruction-response distillation data.

Strict safety rules:
- Do not diagnose disease or say the user has a disease.
- Do not give medication instructions, medication adjustment advice, dosage advice, or drug advice.
- Do not suggest nicotine replacement therapy or any smoking-cessation medication/product.
- Do not infer, compare, or mention actual chronological age. Test.csv has no true Age column.
- Use only the supplied key_health_signals and profile values. Do not invent unsupported risk factors.
- If blood pressure, glucose, or cholesterol are high, recommend consulting a qualified healthcare professional.
- Avoid HIIT or intense exercise advice when blood pressure is high; suggest gradual moderate activity.
- Every recommendation must cite at least one supplied feature, such as BMI, blood pressure, glucose, cholesterol, sleep, stress, activity, smoking, alcohol, or predicted body age.

Return exactly these headings:
1. Brief Profile Summary
2. Main Risk Signals
3. Personalized Recommendations
   - Exercise
   - Diet
   - Sleep and Stress
   - Smoking and Alcohol
   - Follow-up Checks
4. Why These Recommendations Match This User
5. Medical Disclaimer

User profile JSON:
{profile_json}
""".strip().format(profile_json=profile_json)


def call_ollama_qwen(prompt, model_name=MODEL_NAME, timeout=540, num_predict=650):
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Educational lifestyle recommendation only. Follow the strict safety "
                    "rules exactly. Never mention actual age or chronological age."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": num_predict,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started_at = time.time()
    with request.urlopen(req, timeout=timeout) as response:
        response_data = json.loads(response.read().decode("utf-8"))
    seconds = time.time() - started_at
    return response_data["message"]["content"].strip(), seconds


def validate_response(text):
    lower_text = text.lower()
    missing_headings = [heading for heading in REQUIRED_HEADINGS if heading.lower() not in lower_text]
    forbidden_hits = [
        pattern for pattern in FORBIDDEN_PATTERNS
        if re.search(pattern, lower_text, flags=re.IGNORECASE)
    ]
    return missing_headings, forbidden_hits


def choose_sample_indices(predictions, sample_size):
    if sample_size <= 0:
        return []
    total_rows = len(predictions)
    if sample_size >= total_rows:
        return list(range(total_rows))

    ranked = predictions.sort_values("Predicted Body Age (years)").reset_index(drop=False)
    positions = np.linspace(0, total_rows - 1, sample_size).round().astype(int)
    indices = []
    for position in positions:
        original_index = int(ranked.iloc[int(position)]["index"])
        if original_index not in indices:
            indices.append(original_index)

    cursor = 0
    while len(indices) < sample_size and cursor < total_rows:
        candidate = int(ranked.iloc[cursor]["index"])
        if candidate not in indices:
            indices.append(candidate)
        cursor += 1
    return indices[:sample_size]


def generate_dataset(sample_size=10, max_retries=1):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    test_data = pd.read_csv("Test.csv").reset_index(drop=True)
    prediction_path = Path("model_outputs") / "LinearRegression" / "test_predictions.csv"
    prediction_data = pd.read_csv(str(prediction_path)).reset_index(drop=True)

    if len(test_data) != len(prediction_data):
        raise ValueError("Test.csv row count does not match LinearRegression predictions.")

    sample_indices = choose_sample_indices(prediction_data, sample_size)
    rows = []
    instruction = build_distillation_instruction()
    created_at = datetime.now().isoformat(timespec="seconds")

    for output_row_id, person_index in enumerate(sample_indices):
        predicted_age = prediction_data.loc[person_index, "Predicted Body Age (years)"]
        profile = build_profile(test_data.iloc[person_index], predicted_age)
        prompt = build_qwen_prompt(profile)

        response_text = ""
        generation_seconds = np.nan
        status = "not_started"
        missing_headings = []
        forbidden_hits = []
        error_message = ""

        for attempt in range(max_retries + 1):
            try:
                response_text, generation_seconds = call_ollama_qwen(prompt)
                missing_headings, forbidden_hits = validate_response(response_text)
                if not missing_headings and not forbidden_hits:
                    status = "passed"
                    break
                status = "retry_needed"
                prompt = (
                    prompt
                    + "\n\nQuality correction: your previous answer missed required headings "
                    + "or used forbidden wording. Rewrite the answer without mentioning actual "
                    + "age or chronological age, and keep every required heading."
                )
            except Exception as exc:
                error_message = str(exc)
                status = "failed"
                break

        if status != "passed" and status != "failed":
            status = "review_needed"

        row = {
            "distillation_id": output_row_id,
            "person_index": int(person_index),
            "instruction": instruction,
            "input_profile_json": json.dumps(profile, ensure_ascii=False),
            "teacher_response": response_text,
            "teacher_model": MODEL_NAME,
            "recommendation_source": "Local Ollama Qwen2.5",
            "predicted_body_age_years": float(predicted_age),
            "generation_seconds": round(float(generation_seconds), 3) if not pd.isna(generation_seconds) else np.nan,
            "quality_status": status,
            "missing_headings": "; ".join(missing_headings),
            "forbidden_hits": "; ".join(forbidden_hits),
            "error_message": error_message,
            "created_at": created_at,
        }
        rows.append(row)
        print(
            "[{}/{}] person_index={} status={} seconds={}".format(
                output_row_id + 1,
                len(sample_indices),
                person_index,
                status,
                row["generation_seconds"],
            )
        )

    df = pd.DataFrame(rows)
    csv_path = OUTPUT_DIR / "qwen25_7b_distillation_dataset.csv"
    jsonl_path = OUTPUT_DIR / "qwen25_7b_distillation_dataset.jsonl"
    metadata_path = OUTPUT_DIR / "qwen25_7b_distillation_metadata.json"

    df.to_csv(str(csv_path), index=False, encoding="utf-8-sig")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            json.dump(row, handle, ensure_ascii=False)
            handle.write("\n")

    metadata = {
        "teacher_model": MODEL_NAME,
        "recommendation_source": "Local Ollama Qwen2.5",
        "ollama_url": OLLAMA_URL,
        "sample_size_requested": sample_size,
        "rows_generated": int(len(df)),
        "rows_passed_quality_check": int((df["quality_status"] == "passed").sum()),
        "input_dataset": "Test.csv plus LinearRegression predicted body age",
        "output_csv": str(csv_path),
        "output_jsonl": str(jsonl_path),
        "created_at": created_at,
        "note": (
            "This is a synthetic educational distillation dataset generated locally with "
            "Qwen2.5-7B-Instruct through Ollama. It is not medical diagnosis data."
        ),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return df, csv_path, jsonl_path, metadata_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument("--max-retries", type=int, default=1)
    args = parser.parse_args()

    df, csv_path, jsonl_path, metadata_path = generate_dataset(
        sample_size=args.sample_size,
        max_retries=args.max_retries,
    )
    print("\nSaved distillation CSV:", csv_path)
    print("Saved distillation JSONL:", jsonl_path)
    print("Saved metadata:", metadata_path)
    print("Quality status counts:")
    print(df["quality_status"].value_counts())


if __name__ == "__main__":
    main()
