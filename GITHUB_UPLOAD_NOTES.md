# GitHub Upload Notes

This folder is prepared as the GitHub-ready copy of the project.

## Recommended Upload Method

Use GitHub Desktop or Git CLI. Browser upload can reject individual files larger
than 25 MB, while normal Git upload supports files up to GitHub's 100 MB hard
limit.

The largest included files are the rule-based item-level audit table and the
three LoRA adapter weights:

```text
model_outputs/rule_based_hard_safety_checks/rule_based_hard_safety_item_level.csv
model_outputs/lora_student/final_adapter/adapter_model.safetensors
model_outputs/lora_student_llama31_teacher/final_adapter/adapter_model.safetensors
model_outputs/lora_student_multiteacher_qwen_llama31/final_adapter/adapter_model.safetensors
```

The largest file is about 79 MB, and each adapter is about 67 MB. They are under
the 100 MB GitHub limit. The full prepared folder is about 1.07 GB, so GitHub
Desktop or Git CLI is strongly recommended.

## If GitHub Blocks Large Files

If upload is blocked by a repository policy, move the large model artifacts and/or
the rule-based item-level CSV to a release asset or Git LFS, then keep the paths
documented in the README.

## Secret Scan Result

No real API keys were found. The notebook references environment variable names
such as `OPENAI_API_KEY`, and the handoff guide references `HF_TOKEN` as setup
instructions. These are placeholders/env-var names, not credentials.

The GPT-5.5 reference judge workflow is manual and does not call the OpenAI API.

The base model weights and cache folders were excluded because they are downloaded
dependencies, not project source files.
