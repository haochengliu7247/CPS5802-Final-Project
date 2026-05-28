import argparse
import csv
import json
import os
import random
from datetime import datetime
from pathlib import Path


DEFAULT_SOURCE_CSV = Path("model_outputs") / "distillation" / "qwen25_7b_distillation_dataset_full.csv"
DEFAULT_LORA_ROOT = Path(os.getenv("QWEN_LORA_ROOT", r"E:\CPS5802_Qwen_LoRA"))
DEFAULT_OUTPUT_DIR = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "data"

SYSTEM_PROMPT = (
    "You are a careful educational lifestyle recommendation assistant. "
    "Generate personalized lifestyle recommendations from a synthetic health profile and predicted body age. "
    "Do not diagnose disease, do not infer chronological age, and do not give medication instructions. "
    "The field named Predicted Body Age (years) is not chronological age; never label it as Age or actual age. "
    "Always keep the response educational and include a medical disclaimer."
)


def read_distillation_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def make_user_prompt(row):
    instruction = (row.get("instruction") or "").strip()
    profile_json = (row.get("input_profile_json") or "").strip()
    return (
        f"{instruction}\n\n"
        "Synthetic health profile JSON:\n"
        f"{profile_json}\n\n"
        "Write the recommendation using the required structured headings. "
        "Refer to Predicted Body Age only as predicted body age, not as age or actual age."
    )


def make_record(row):
    return {
        "distillation_id": int(row["distillation_id"]),
        "person_index": int(row["person_index"]),
        "quality_status": row.get("quality_status", ""),
        "predicted_body_age_years": float(row["predicted_body_age_years"]),
        "teacher_model": row.get("teacher_model", ""),
        "recommendation_source": row.get("recommendation_source", ""),
        "instruction": row.get("instruction", ""),
        "input_profile_json": row.get("input_profile_json", ""),
        "teacher_response": row.get("teacher_response", ""),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": make_user_prompt(row)},
            {"role": "assistant", "content": row.get("teacher_response", "").strip()},
        ],
    }


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def summarize_records(records):
    char_lengths = []
    response_lengths = []
    for record in records:
        joined = "\n".join(message["content"] for message in record["messages"])
        char_lengths.append(len(joined))
        response_lengths.append(len(record["teacher_response"]))
    if not records:
        return {
            "rows": 0,
            "approx_total_tokens_chars_4": 0,
            "approx_mean_tokens_chars_4": 0,
        }
    return {
        "rows": len(records),
        "mean_chars": round(sum(char_lengths) / len(char_lengths), 2),
        "max_chars": max(char_lengths),
        "mean_response_chars": round(sum(response_lengths) / len(response_lengths), 2),
        "approx_total_tokens_chars_4": round(sum(char_lengths) / 4),
        "approx_mean_tokens_chars_4": round((sum(char_lengths) / len(char_lengths)) / 4),
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare Qwen2.5-0.5B LoRA SFT data from Qwen2.5-7B teacher CSV.")
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=5802)
    parser.add_argument("--train-ratio", type=float, default=0.85)
    parser.add_argument("--validation-ratio", type=float, default=0.10)
    parser.add_argument("--quality-status", default="passed")
    args = parser.parse_args()

    if not args.source_csv.exists():
        raise FileNotFoundError(f"Source CSV not found: {args.source_csv}")

    rows = read_distillation_rows(args.source_csv)
    filtered = [row for row in rows if row.get("quality_status") == args.quality_status]
    if not filtered:
        raise ValueError(f"No rows found with quality_status={args.quality_status!r}")

    records = [make_record(row) for row in filtered]
    random.Random(args.seed).shuffle(records)

    train_count = int(len(records) * args.train_ratio)
    validation_count = int(len(records) * args.validation_ratio)
    train_records = records[:train_count]
    validation_records = records[train_count:train_count + validation_count]
    test_records = records[train_count + validation_count:]

    write_jsonl(args.output_dir / "train.jsonl", train_records)
    write_jsonl(args.output_dir / "validation.jsonl", validation_records)
    write_jsonl(args.output_dir / "test.jsonl", test_records)

    metadata = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_csv": str(args.source_csv),
        "quality_status_filter": args.quality_status,
        "seed": args.seed,
        "total_source_rows": len(rows),
        "usable_rows": len(records),
        "splits": {
            "train": summarize_records(train_records),
            "validation": summarize_records(validation_records),
            "test": summarize_records(test_records),
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "dataset_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
