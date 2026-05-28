import argparse
import re
from pathlib import Path

import pandas as pd


OUTPUT_COLUMNS = [
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

SCORE_COLUMNS = OUTPUT_COLUMNS[1:8]

KNOWN_MAIN_ISSUES = [
    "direct diagnosis",
    "unsafe medication advice",
    "medication advice",
    "unsupported claim",
    "incomplete coverage",
    "missing follow-up",
    "policy issue",
    "safety issue",
    "hallucination",
    "none",
]


def workflow_dir():
    return Path(__file__).resolve().parents[1]


def normalize_line(line):
    return re.sub(r"\s+", " ", str(line).strip())


def read_records(raw_text):
    records = []
    current = None
    for raw_line in raw_text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            continue
        if line.startswith("```") or line.lower().startswith("eval_id "):
            continue
        if re.match(r"^E\d{4}\b", line):
            if current:
                records.append(current)
            current = line
        elif current:
            current += " " + line
    if current:
        records.append(current)
    return records


def split_main_issue_and_reason(tail):
    tail = normalize_line(tail)
    lower = tail.lower()
    for issue in KNOWN_MAIN_ISSUES:
        if lower == issue:
            return issue, ""
        if lower.startswith(issue + " "):
            return tail[: len(issue)], tail[len(issue) :].strip()

    # Fallback: use the first 1-3 words as issue label and the rest as the reason.
    words = tail.split()
    if not words:
        return "", ""
    if len(words) == 1:
        return words[0], ""
    if len(words) == 2:
        return " ".join(words), ""
    return " ".join(words[:2]), " ".join(words[2:])


def parse_record(record):
    pattern = (
        r"^(E\d{4})\s+"
        r"([1-5])\s+([1-5])\s+([1-5])\s+([1-5])\s+([1-5])\s+([1-5])\s+([1-5])\s+"
        r"(TRUE|FALSE|True|False|true|false)\s+"
        r"(.+)$"
    )
    match = re.match(pattern, record)
    if not match:
        raise ValueError("Could not parse record: {}".format(record[:300]))

    eval_id = match.group(1)
    scores = list(match.groups()[1:8])
    overall_pass = match.group(9).upper()
    tail = match.group(10)
    main_issue, brief_reason = split_main_issue_and_reason(tail)

    row = {
        "eval_id": eval_id,
        "overall_pass": overall_pass,
        "main_issue": main_issue,
        "brief_reason": brief_reason,
    }
    for column, score in zip(SCORE_COLUMNS, scores):
        row[column] = int(score)
    return {column: row.get(column, "") for column in OUTPUT_COLUMNS}


def main():
    parser = argparse.ArgumentParser(
        description="Parse one raw text file containing manually copied GPT-5.5 batch outputs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=workflow_dir() / "results" / "gpt55_raw_outputs.txt",
        help="Raw txt file containing all GPT-5.5 outputs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=workflow_dir() / "results" / "gpt55_results_filled.csv",
        help="Parsed CSV path for validate_filled_results.py and aggregate_results.py.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(
            "Raw GPT output txt not found. Save all copied GPT outputs here first: {}".format(args.input)
        )

    raw_text = args.input.read_text(encoding="utf-8-sig")
    records = read_records(raw_text)
    rows = [parse_record(record) for record in records]
    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    df = df.drop_duplicates(subset=["eval_id"], keep="last").sort_values("eval_id")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")

    print("Parsed records:", len(records))
    print("Unique eval_id rows saved:", len(df))
    print("Saved:", args.output)
    print("Next run: python evaluation/03_gpt55_reference_evaluation/scripts/validate_filled_results.py")


if __name__ == "__main__":
    main()
