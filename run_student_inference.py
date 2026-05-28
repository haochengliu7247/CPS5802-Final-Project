import argparse
import json
import os
import re
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_LORA_ROOT = Path(os.getenv("QWEN_LORA_ROOT", r"E:\CPS5802_Qwen_LoRA"))
DEFAULT_BASE_MODEL_DIR = DEFAULT_LORA_ROOT / "base_models" / "Qwen2.5-0.5B-Instruct"
DEFAULT_MODEL_NAME = str(DEFAULT_BASE_MODEL_DIR) if DEFAULT_BASE_MODEL_DIR.exists() else "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_ADAPTER_DIR = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "final_adapter"
DEFAULT_SAMPLE_JSONL = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "data" / "test.jsonl"


SAFETY_REWRITES = [
    (re.compile(r"\bhas diabetes\b", re.IGNORECASE), "reports a diabetes-related profile flag"),
    (re.compile(r"\bhas hypertension\b", re.IGNORECASE), "shows a high blood-pressure signal"),
    (re.compile(r"\byou have diabetes\b", re.IGNORECASE), "your profile includes a diabetes-related flag"),
    (re.compile(r"\byou have hypertension\b", re.IGNORECASE), "your profile shows a high blood-pressure signal"),
    (re.compile(r"\byour chronic condition of diabetes\b", re.IGNORECASE), "the diabetes-related profile flag"),
    (re.compile(r"\bchronic condition of diabetes\b", re.IGNORECASE), "diabetes-related profile flag"),
]


def read_jsonl(path):
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_student(model_name, adapter_dir, dtype):
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


def soften_medical_claims(text):
    for pattern, replacement in SAFETY_REWRITES:
        text = pattern.sub(replacement, text)
    text = re.sub(r"(^|\n)(\s*-\s*)reports", r"\1\2Reports", text)
    text = re.sub(r"(^|\n)(\s*-\s*)shows", r"\1\2Shows", text)
    return text


def main():
    parser = argparse.ArgumentParser(description="Run local inference with Qwen2.5-0.5B-Instruct + LoRA adapter.")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--adapter-dir", type=Path, default=DEFAULT_ADAPTER_DIR)
    parser.add_argument("--sample-jsonl", type=Path, default=DEFAULT_SAMPLE_JSONL)
    parser.add_argument("--sample-index", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=700)
    parser.add_argument("--dtype", choices=["bf16", "fp16", "fp32"], default="fp16")
    args = parser.parse_args()

    records = read_jsonl(args.sample_jsonl)
    record = records[args.sample_index]
    model, tokenizer = load_student(args.model_name, args.adapter_dir, args.dtype)

    input_ids = tokenizer.apply_chat_template(
        record["messages"][:2],
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
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    response = tokenizer.decode(generated[0, input_ids.shape[-1]:], skip_special_tokens=True).strip()
    response = soften_medical_claims(response)
    print("distillation_id:", record["distillation_id"])
    print("person_index:", record["person_index"])
    print("student_response:\n")
    print(response)


if __name__ == "__main__":
    main()
