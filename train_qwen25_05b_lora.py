import argparse
import inspect
import json
import os
from dataclasses import dataclass
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    set_seed,
)


DEFAULT_LORA_ROOT = Path(os.getenv("QWEN_LORA_ROOT", r"E:\CPS5802_Qwen_LoRA"))
DEFAULT_BASE_MODEL_DIR = DEFAULT_LORA_ROOT / "base_models" / "Qwen2.5-0.5B-Instruct"
DEFAULT_MODEL_NAME = str(DEFAULT_BASE_MODEL_DIR) if DEFAULT_BASE_MODEL_DIR.exists() else "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_DATA_DIR = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "data"
DEFAULT_OUTPUT_DIR = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "checkpoints"
DEFAULT_FINAL_ADAPTER_DIR = DEFAULT_LORA_ROOT / "student_qwen25_05b_lora" / "final_adapter"

QWEN_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def read_jsonl(path):
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def choose_dtype(dtype_name):
    if dtype_name == "auto":
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
            return torch.bfloat16, "bf16"
        if torch.cuda.is_available():
            return torch.float16, "fp16"
        return torch.float32, "fp32"
    if dtype_name == "bf16":
        return torch.bfloat16, "bf16"
    if dtype_name == "fp16":
        return torch.float16, "fp16"
    if dtype_name == "fp32":
        return torch.float32, "fp32"
    raise ValueError(f"Unsupported dtype: {dtype_name}")


def parse_target_modules(value):
    if value == "qwen":
        return QWEN_TARGET_MODULES
    if value == "all-linear":
        return "all-linear"
    return [item.strip() for item in value.split(",") if item.strip()]


def get_chat_template_input_ids(tokenizer, messages, add_generation_prompt):
    encoded = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=add_generation_prompt,
    )
    if hasattr(encoded, "keys") and "input_ids" in encoded.keys():
        encoded = encoded["input_ids"]
    if hasattr(encoded, "tolist"):
        encoded = encoded.tolist()
    if encoded and isinstance(encoded[0], list):
        encoded = encoded[0]
    return list(encoded)


def tokenize_record(record, tokenizer, max_seq_length):
    messages = record["messages"]
    full_ids = get_chat_template_input_ids(tokenizer, messages, add_generation_prompt=False)
    prompt_ids = get_chat_template_input_ids(tokenizer, messages[:2], add_generation_prompt=True)
    if len(full_ids) > max_seq_length:
        full_ids = full_ids[:max_seq_length]

    labels = list(full_ids)
    prompt_len = min(len(prompt_ids), len(labels))
    labels[:prompt_len] = [-100] * prompt_len

    supervised_tokens = sum(1 for value in labels if value != -100)
    return {
        "input_ids": full_ids,
        "attention_mask": [1] * len(full_ids),
        "labels": labels,
        "supervised_tokens": supervised_tokens,
        "distillation_id": record.get("distillation_id"),
        "person_index": record.get("person_index"),
    }


def pack_tokenized_records(records, max_seq_length):
    packed = []
    current = {"input_ids": [], "attention_mask": [], "labels": [], "supervised_tokens": 0}

    def flush():
        nonlocal current
        if current["input_ids"]:
            packed.append(current)
        current = {"input_ids": [], "attention_mask": [], "labels": [], "supervised_tokens": 0}

    for record in records:
        if not record["input_ids"] or record["supervised_tokens"] == 0:
            continue
        if len(record["input_ids"]) > max_seq_length:
            record = {
                "input_ids": record["input_ids"][:max_seq_length],
                "attention_mask": record["attention_mask"][:max_seq_length],
                "labels": record["labels"][:max_seq_length],
                "supervised_tokens": sum(1 for value in record["labels"][:max_seq_length] if value != -100),
            }
        if len(current["input_ids"]) + len(record["input_ids"]) > max_seq_length:
            flush()
        current["input_ids"].extend(record["input_ids"])
        current["attention_mask"].extend(record["attention_mask"])
        current["labels"].extend(record["labels"])
        current["supervised_tokens"] += record["supervised_tokens"]
    flush()
    return packed


@dataclass
class CausalCollator:
    tokenizer: object
    pad_to_multiple_of: int = 8

    def __call__(self, features):
        max_len = max(len(feature["input_ids"]) for feature in features)
        if self.pad_to_multiple_of:
            multiple = self.pad_to_multiple_of
            max_len = ((max_len + multiple - 1) // multiple) * multiple

        pad_id = self.tokenizer.pad_token_id
        batch = {"input_ids": [], "attention_mask": [], "labels": []}
        for feature in features:
            pad_len = max_len - len(feature["input_ids"])
            batch["input_ids"].append(feature["input_ids"] + [pad_id] * pad_len)
            batch["attention_mask"].append(feature["attention_mask"] + [0] * pad_len)
            batch["labels"].append(feature["labels"] + [-100] * pad_len)

        return {key: torch.tensor(value, dtype=torch.long) for key, value in batch.items()}


def build_training_arguments(args, dtype_mode):
    kwargs = {
        "output_dir": str(args.output_dir),
        "num_train_epochs": args.epochs,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "per_device_eval_batch_size": args.per_device_eval_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "warmup_ratio": args.warmup_ratio,
        "lr_scheduler_type": args.lr_scheduler_type,
        "logging_steps": args.logging_steps,
        "save_strategy": "epoch",
        "save_total_limit": args.save_total_limit,
        "report_to": ["tensorboard"],
        "optim": args.optim,
        "gradient_checkpointing": args.gradient_checkpointing,
        "dataloader_num_workers": args.dataloader_num_workers,
        "dataloader_pin_memory": True,
        "remove_unused_columns": False,
        "bf16": dtype_mode == "bf16",
        "fp16": dtype_mode == "fp16",
        "tf32": torch.cuda.is_available(),
    }
    signature = inspect.signature(TrainingArguments)
    if "eval_strategy" in signature.parameters:
        kwargs["eval_strategy"] = "epoch"
    else:
        kwargs["evaluation_strategy"] = "epoch"
    if "torch_empty_cache_steps" in signature.parameters:
        kwargs["torch_empty_cache_steps"] = args.logging_steps
    if "eval_accumulation_steps" in signature.parameters:
        kwargs["eval_accumulation_steps"] = 1
    return TrainingArguments(**kwargs)


def main():
    parser = argparse.ArgumentParser(description="LoRA SFT training for Qwen2.5-0.5B-Instruct student model.")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--final-adapter-dir", type=Path, default=DEFAULT_FINAL_ADAPTER_DIR)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--epochs", type=float, default=3)
    parser.add_argument("--per-device-train-batch-size", type=int, default=24)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=24)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=1.5e-4)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--lr-scheduler-type", default="cosine")
    parser.add_argument("--lora-r", type=int, default=32)
    parser.add_argument("--lora-alpha", type=int, default=64)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--target-modules", default="qwen")
    parser.add_argument("--dtype", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    parser.add_argument("--packing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--gradient-checkpointing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--optim", default="adamw_torch_fused")
    parser.add_argument("--logging-steps", type=int, default=5)
    parser.add_argument("--save-total-limit", type=int, default=3)
    parser.add_argument("--dataloader-num-workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=5802)
    args = parser.parse_args()

    set_seed(args.seed)
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

    train_path = args.data_dir / "train.jsonl"
    validation_path = args.data_dir / "validation.jsonl"
    if not train_path.exists() or not validation_path.exists():
        raise FileNotFoundError(
            f"Missing train/validation data under {args.data_dir}. Run prepare_qwen25_lora_dataset.py first."
        )

    torch_dtype, dtype_mode = choose_dtype(args.dtype)
    print(f"Loading tokenizer: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    train_records = read_jsonl(train_path)
    validation_records = read_jsonl(validation_path)
    tokenized_train = [tokenize_record(record, tokenizer, args.max_seq_length) for record in train_records]
    tokenized_validation = [tokenize_record(record, tokenizer, args.max_seq_length) for record in validation_records]
    if args.packing:
        tokenized_train = pack_tokenized_records(tokenized_train, args.max_seq_length)
        tokenized_validation = pack_tokenized_records(tokenized_validation, args.max_seq_length)

    tokenized_train = [record for record in tokenized_train if record["supervised_tokens"] > 0]
    tokenized_validation = [record for record in tokenized_validation if record["supervised_tokens"] > 0]
    if not tokenized_train:
        raise ValueError(
            "No train sequences contain assistant-label tokens. "
            "Increase --max-seq-length; this dataset typically needs 1536 or 2048."
        )
    if not tokenized_validation:
        raise ValueError(
            "No validation sequences contain assistant-label tokens. "
            "Increase --max-seq-length; this dataset typically needs 1536 or 2048."
        )
    print(f"Train sequences: {len(tokenized_train)}")
    print(f"Validation sequences: {len(tokenized_validation)}")
    print(f"Packing enabled: {args.packing}")
    print(f"Torch dtype: {dtype_mode}")

    train_dataset = Dataset.from_list(tokenized_train)
    validation_dataset = Dataset.from_list(tokenized_validation)

    print(f"Loading base model: {args.model_name}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        torch_dtype=torch_dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    model.config.use_cache = False

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=parse_target_modules(args.target_modules),
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    training_args = build_training_arguments(args, dtype_mode)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        data_collator=CausalCollator(tokenizer),
    )

    trainer.train()

    args.final_adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(args.final_adapter_dir))
    tokenizer.save_pretrained(str(args.final_adapter_dir))

    training_config = vars(args).copy()
    training_config["dtype_mode"] = dtype_mode
    training_config["train_sequences"] = len(tokenized_train)
    training_config["validation_sequences"] = len(tokenized_validation)
    (args.final_adapter_dir / "training_config.json").write_text(
        json.dumps(training_config, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Saved final LoRA adapter: {args.final_adapter_dir}")


if __name__ == "__main__":
    main()
