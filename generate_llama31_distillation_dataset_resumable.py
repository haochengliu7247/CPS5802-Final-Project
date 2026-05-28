import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import generate_llama31_distillation_dataset as base

EXPECTED_LLAMA_MODEL = "llama3.1:8b"


def write_outputs(rows, csv_path, jsonl_path, metadata_path, sample_size, created_at):
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    df = pd.DataFrame(rows)
    df.to_csv(str(csv_path), index=False, encoding="utf-8-sig")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            record = {}
            for key, value in row.items():
                if isinstance(value, float) and np.isnan(value):
                    record[key] = ""
                else:
                    record[key] = value
            json.dump(record, handle, ensure_ascii=False)
            handle.write("\n")

    metadata = {
        "teacher_model": base.MODEL_NAME,
        "recommendation_source": "Local Ollama Llama3.1",
        "ollama_url": base.OLLAMA_URL,
        "sample_size_requested": sample_size,
        "rows_generated": int(len(df)),
        "rows_passed_quality_check": int((df["quality_status"] == "passed").sum()) if len(df) else 0,
        "input_dataset": "Test.csv plus LinearRegression predicted body age",
        "output_csv": str(csv_path),
        "output_jsonl": str(jsonl_path),
        "created_at": created_at,
        "last_saved_at": datetime.now().isoformat(timespec="seconds"),
        "note": (
            "Resumable local Llama 3.1 8B distillation output. "
            "This is synthetic educational data, not medical diagnosis data."
        ),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    if base.MODEL_NAME != EXPECTED_LLAMA_MODEL:
        raise ValueError(
            "Expected local teacher model {}, but base.MODEL_NAME is {}".format(
                EXPECTED_LLAMA_MODEL,
                base.MODEL_NAME,
            )
        )

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=3000)
    parser.add_argument("--output-prefix", default="llama31_8b_distillation_dataset_full")
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--flush-every", type=int, default=1)
    args = parser.parse_args()

    output_dir = Path("model_outputs") / "distillation"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "{}.csv".format(args.output_prefix)
    jsonl_path = output_dir / "{}.jsonl".format(args.output_prefix)
    metadata_path = output_dir / "{}_metadata.json".format(args.output_prefix)

    test_data = pd.read_csv("Test.csv").reset_index(drop=True)
    prediction_data = pd.read_csv("model_outputs/LinearRegression/test_predictions.csv").reset_index(drop=True)
    sample_indices = base.choose_sample_indices(prediction_data, args.sample_size)

    if csv_path.exists():
        existing_df = pd.read_csv(str(csv_path))
        rows = existing_df.to_dict("records")
        completed_indices = set(existing_df["person_index"].astype(int).tolist()) if len(existing_df) else set()
        created_at = existing_df["created_at"].iloc[0] if len(existing_df) and "created_at" in existing_df.columns else datetime.now().isoformat(timespec="seconds")
    else:
        rows = []
        completed_indices = set()
        created_at = datetime.now().isoformat(timespec="seconds")

    instruction = base.build_distillation_instruction()
    pending_indices = [idx for idx in sample_indices if idx not in completed_indices]

    print("Target rows:", len(sample_indices))
    print("Already completed:", len(completed_indices))
    print("Pending:", len(pending_indices))
    print("Output CSV:", csv_path)

    for pending_position, person_index in enumerate(pending_indices, 1):
        predicted_age = prediction_data.loc[person_index, "Predicted Body Age (years)"]
        profile = base.build_profile(test_data.iloc[person_index], predicted_age)
        prompt = base.build_llama31_prompt(profile)

        response_text = ""
        generation_seconds = np.nan
        status = "not_started"
        missing_headings = []
        forbidden_hits = []
        error_message = ""

        for attempt in range(args.max_retries + 1):
            try:
                response_text, generation_seconds = base.call_ollama_llama31(prompt, num_predict=700)
                missing_headings, forbidden_hits = base.validate_response(response_text)
                if not missing_headings and not forbidden_hits:
                    status = "passed"
                    break
                status = "review_needed"
                prompt += (
                    "\n\nRewrite completely. Include all five required headings and avoid "
                    "actual age, chronological age, diagnosis, medication advice, dosage "
                    "advice, and nicotine replacement advice."
                )
            except Exception as exc:
                error_message = str(exc)
                status = "failed"
                break

        row = {
            "distillation_id": len(rows),
            "person_index": int(person_index),
            "instruction": instruction,
            "input_profile_json": json.dumps(profile, ensure_ascii=False),
            "teacher_response": response_text,
            "teacher_model": base.MODEL_NAME,
            "recommendation_source": "Local Ollama Llama3.1",
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
                len(rows),
                len(sample_indices),
                person_index,
                status,
                row["generation_seconds"],
            )
        , flush=True)

        if len(rows) % args.flush_every == 0:
            write_outputs(rows, csv_path, jsonl_path, metadata_path, args.sample_size, created_at)

    write_outputs(rows, csv_path, jsonl_path, metadata_path, args.sample_size, created_at)
    print("Done. Generated rows:", len(rows))
    print("Saved:", csv_path)
    print("Saved:", jsonl_path)
    print("Saved:", metadata_path)


if __name__ == "__main__":
    main()
