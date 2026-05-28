import argparse
import csv
import json
import os
import re
from pathlib import Path

import pandas as pd
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from create_distillation_benefit_analysis import analyze_response


DEFAULT_LORA_ROOT = Path(os.getenv("QWEN_LORA_ROOT", r"E:\CPS5802_Qwen_LoRA"))
DEFAULT_BASE_MODEL_DIR = DEFAULT_LORA_ROOT / "base_models" / "Qwen2.5-0.5B-Instruct"
DEFAULT_MODEL_NAME = str(DEFAULT_BASE_MODEL_DIR) if DEFAULT_BASE_MODEL_DIR.exists() else "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_ADAPTER_DIR = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "final_adapter"
DEFAULT_TEST_JSONL = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "data" / "test.jsonl"
DEFAULT_EVAL_DIR = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "eval"


SAFETY_REWRITES = [
    (re.compile(r"\bhas diabetes\b", re.IGNORECASE), "reports a diabetes-related profile flag"),
    (re.compile(r"\bhas hypertension\b", re.IGNORECASE), "shows a high blood-pressure signal"),
    (re.compile(r"\byou have diabetes\b", re.IGNORECASE), "your profile includes a diabetes-related flag"),
    (re.compile(r"\byou have hypertension\b", re.IGNORECASE), "your profile shows a high blood-pressure signal"),
]


def read_jsonl(path):
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_model(model_name, adapter_dir, dtype):
    tokenizer = AutoTokenizer.from_pretrained(adapter_dir, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    torch_dtype = torch.bfloat16 if dtype == "bf16" else torch.float16 if dtype == "fp16" else torch.float32
    base = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch_dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, adapter_dir)
    model.eval()
    return model, tokenizer


def generate_response(model, tokenizer, messages, max_new_tokens):
    prompt_messages = messages[:2]
    input_ids = tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    )
    if hasattr(input_ids, "keys") and "input_ids" in input_ids.keys():
        input_ids = input_ids["input_ids"]
    input_ids = input_ids.to(model.device)
    with torch.no_grad():
        generated = model.generate(
            input_ids=input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    new_tokens = generated[0, input_ids.shape[-1]:]
    return soften_medical_claims(tokenizer.decode(new_tokens, skip_special_tokens=True).strip())


def soften_medical_claims(text):
    for pattern, replacement in SAFETY_REWRITES:
        text = pattern.sub(replacement, text)
    text = re.sub(r"(^|\n)(\s*-\s*)reports", r"\1\2Reports", text)
    text = re.sub(r"(^|\n)(\s*-\s*)shows", r"\1\2Shows", text)
    return text


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Evaluate a Qwen2.5-0.5B LoRA student adapter on held-out data.")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--adapter-dir", type=Path, default=DEFAULT_ADAPTER_DIR)
    parser.add_argument("--test-jsonl", type=Path, default=DEFAULT_TEST_JSONL)
    parser.add_argument("--eval-dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-new-tokens", type=int, default=700)
    parser.add_argument("--dtype", choices=["bf16", "fp16", "fp32"], default="fp16")
    parser.add_argument("--teacher-label", default="")
    args = parser.parse_args()

    records = read_jsonl(args.test_jsonl)
    if args.limit > 0:
        records = records[:args.limit]
    model, tokenizer = load_model(args.model_name, args.adapter_dir, args.dtype)

    output_rows = []
    score_rows = []
    for index, record in enumerate(records, 1):
        generated = generate_response(model, tokenizer, record["messages"], args.max_new_tokens)
        profile = json.loads(record["input_profile_json"])
        distillation_id = int(record["distillation_id"])
        person_index = int(record["person_index"])

        output_rows.append({
            "distillation_id": distillation_id,
            "person_index": person_index,
            "predicted_body_age_years": record["predicted_body_age_years"],
            "teacher_response": record["teacher_response"],
            "student_response": generated,
        })
        teacher_label = args.teacher_label.strip()
        if not teacher_label:
            teacher_model = record.get("teacher_model") or "teacher"
            teacher_label = "{} teacher".format(teacher_model)
        score_rows.append(analyze_response("Qwen2.5-0.5B LoRA student", generated, profile, distillation_id, person_index))
        score_rows.append(analyze_response(teacher_label, record["teacher_response"], profile, distillation_id, person_index))
        print(f"[{index}/{len(records)}] generated distillation_id={distillation_id}")

    args.eval_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.eval_dir / "student_sample_outputs.csv", output_rows)

    score_df = pd.DataFrame(score_rows)
    score_df.to_csv(args.eval_dir / "student_eval_scores.csv", index=False, encoding="utf-8-sig")
    summary_df = (
        score_df
        .groupby("response_source")
        [[
            "word_count",
            "bullet_count",
            "numeric_evidence_count",
            "action_verb_count",
            "explanation_connector_count",
            "required_heading_coverage",
            "recommendation_category_count",
            "feature_evidence_count",
            "key_signal_coverage",
            "forbidden_term_count",
            "medical_disclaimer_present",
            "quality_score",
        ]]
        .mean()
        .reset_index()
    )
    summary_df.to_csv(args.eval_dir / "student_eval_summary.csv", index=False, encoding="utf-8-sig")
    print(summary_df)
    print(f"Saved evaluation outputs: {args.eval_dir}")


if __name__ == "__main__":
    main()
