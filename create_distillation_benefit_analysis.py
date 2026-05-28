import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPRESENTATIVE_DISTILLATION_PATH = Path("model_outputs") / "distillation" / "qwen25_7b_distillation_dataset.csv"
FULL_DISTILLATION_PATH = Path("model_outputs") / "distillation" / "qwen25_7b_distillation_dataset_full.csv"
FIGURE_DIR = Path("model_outputs") / "figures"
REPORT_DIR = Path("model_outputs") / "reports"

REQUIRED_HEADINGS = [
    "Brief Profile Summary",
    "Main Risk Signals",
    "Personalized Recommendations",
    "Why These Recommendations Match This User",
    "Medical Disclaimer",
]

RECOMMENDATION_CATEGORIES = [
    "exercise",
    "diet",
    "sleep",
    "stress",
    "smoking",
    "alcohol",
    "follow-up",
    "checks",
]

FEATURE_KEYWORDS = {
    "Predicted Body Age": ["predicted body age", "body age"],
    "BMI": ["bmi", "weight"],
    "Blood Pressure": ["blood pressure", "systolic", "diastolic"],
    "Cholesterol": ["cholesterol", "lipid"],
    "Blood Glucose": ["glucose", "blood sugar"],
    "Activity": ["activity", "exercise", "walking", "aerobic"],
    "Smoking": ["smoking", "smoker", "smoke"],
    "Alcohol": ["alcohol", "drinking"],
    "Sleep": ["sleep", "insomnia"],
    "Stress": ["stress", "mindfulness", "relaxation"],
    "Diet": ["diet", "nutrition", "vegetables", "whole grains"],
    "Mental Health": ["mental health", "mood"],
}

FORBIDDEN_TERMS = [
    "actual age",
    "chronological age",
    "diagnosed",
    "you have diabetes",
    "you have hypertension",
    "medication adjustment",
    "nicotine replacement",
    "prescribe",
]

ACTION_VERBS = [
    "increase",
    "reduce",
    "maintain",
    "monitor",
    "consult",
    "schedule",
    "limit",
    "avoid",
    "aim",
    "practice",
    "focus",
    "include",
    "choose",
    "keep",
    "continue",
    "gradually",
    "manage",
    "address",
    "establish",
    "check",
    "track",
    "prioritize",
]

EXPLANATION_CONNECTORS = [
    "because",
    "given",
    "due to",
    "since",
    "based on",
    "linked to",
    "helps",
    "supports",
    "therefore",
    "tailored",
    "risk",
]


def load_distillation_data():
    source_path = FULL_DISTILLATION_PATH if FULL_DISTILLATION_PATH.exists() else REPRESENTATIVE_DISTILLATION_PATH
    df = pd.read_csv(str(source_path))
    if "quality_status" in df.columns:
        passed_df = df[df["quality_status"] == "passed"].copy()
        if len(passed_df):
            df = passed_df
    return df.reset_index(drop=True), source_path


def apply_sparse_id_ticks(ax, ids, max_ticks=12):
    ids = list(ids)
    if not ids:
        return
    if len(ids) <= max_ticks:
        positions = np.arange(len(ids))
        ax.set_xticks(positions)
        ax.set_xticklabels([str(item) for item in ids])
        return
    step = max(1, int(np.ceil(len(ids) / max_ticks)))
    positions = np.arange(0, len(ids), step)
    if positions[-1] != len(ids) - 1:
        positions = np.append(positions, len(ids) - 1)
    ax.set_xticks(positions)
    ax.set_xticklabels([str(ids[int(position)]) for position in positions], rotation=30, ha="right")


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def fallback_recommendation(profile):
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    signals = profile.get("key_health_signals", [])
    predicted_age = profile.get("Predicted Body Age (years)", "Not provided")
    bmi = profile.get("BMI", "Not provided")
    blood_pressure = profile.get("Blood Pressure (s/d)", "Not provided")
    cholesterol = profile.get("Cholesterol Level (mg/dL)", "Not provided")
    glucose = profile.get("Blood Glucose Level (mg/dL)", "Not provided")
    activity = profile.get("Physical Activity Level", "Not provided")
    smoking = profile.get("Smoking Status", "Not provided")
    alcohol = profile.get("Alcohol Consumption", "Not provided")
    sleep = profile.get("Sleep Patterns", "Not provided")
    stress = profile.get("Stress Levels", "Not provided")

    if not signals:
        signals = ["No major rule-based signal was detected."]

    lines = [
        "1. Brief Profile Summary",
        "- Synthetic profile with predicted body age of {} years, BMI {}, blood pressure {}, glucose {}, cholesterol {}, activity {}, sleep {}, and stress {}.".format(
            predicted_age, bmi, blood_pressure, glucose, cholesterol, activity, sleep, stress
        ),
        "",
        "2. Main Risk Signals",
    ]
    lines.extend(["- {}".format(signal) for signal in signals[:6]])
    lines.extend([
        "",
        "3. Personalized Recommendations",
        "- Exercise: Match exercise to activity level {}; use gradual moderate activity if blood pressure is high.".format(activity),
        "- Diet: Use BMI {}, glucose {}, and cholesterol {} as diet signals; emphasize vegetables, whole grains, lean protein, and less sugar/fried food.".format(bmi, glucose, cholesterol),
        "- Sleep and Stress: Sleep pattern is {} and stress is {}; keep a stable schedule and use relaxation routines.".format(sleep, stress),
        "- Smoking and Alcohol: Smoking status is {} and alcohol use is {}; avoid smoking relapse and keep alcohol low.".format(smoking, alcohol),
        "- Follow-up Checks: Because blood pressure is {}, glucose is {}, and cholesterol is {}, consider periodic checks and consult a qualified healthcare professional if readings stay high.".format(blood_pressure, glucose, cholesterol),
        "",
        "4. Why These Recommendations Match This User",
        "- The advice links to the supplied synthetic features and predicted body age.",
        "",
        "5. Medical Disclaimer",
        "- This dataset is synthetic and this recommendation is for educational purposes only. It is not a diagnosis and does not replace a licensed clinician.",
    ])
    return "\n".join(lines)


def count_present(text, keywords):
    normalized = normalize_text(text)
    return sum(1 for keyword in keywords if keyword in normalized)


def signal_coverage(text, profile):
    signals = profile.get("key_health_signals", [])
    if not signals:
        return 1.0
    normalized = normalize_text(text)
    covered = 0
    for signal in signals:
        signal_lower = signal.lower()
        tokens = []
        if "predicted body age" in signal_lower:
            tokens.append("predicted body age")
        if "bmi" in signal_lower:
            tokens.append("bmi")
        if "blood pressure" in signal_lower:
            tokens.append("blood pressure")
        if "cholesterol" in signal_lower:
            tokens.append("cholesterol")
        if "glucose" in signal_lower:
            tokens.extend(["glucose", "blood sugar"])
        if "smoking" in signal_lower or "smoker" in signal_lower:
            tokens.extend(["smoking", "smoker"])
        if "alcohol" in signal_lower:
            tokens.append("alcohol")
        if "insomnia" in signal_lower or "sleep" in signal_lower:
            tokens.extend(["insomnia", "sleep"])
        if "stress" in signal_lower:
            tokens.append("stress")
        if "activity" in signal_lower:
            tokens.extend(["activity", "exercise"])
        if not tokens:
            tokens = [signal_lower.split(":")[0]]
        if any(token in normalized for token in tokens):
            covered += 1
    return covered / float(len(signals))


def analyze_response(source, text, profile, distillation_id, person_index):
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    normalized = normalize_text(text)
    heading_count = count_present(text, [heading.lower() for heading in REQUIRED_HEADINGS])
    category_hits = {
        category: int(category in normalized)
        for category in RECOMMENDATION_CATEGORIES
    }
    feature_hits = {
        feature: int(any(keyword in normalized for keyword in keywords))
        for feature, keywords in FEATURE_KEYWORDS.items()
    }
    forbidden_count = sum(1 for term in FORBIDDEN_TERMS if term in normalized)
    word_count = len(re.findall(r"\b\w+\b", str(text)))
    bullet_count = str(text).count("-")
    numeric_evidence_count = len(re.findall(r"\d+(?:\.\d+)?", str(text)))
    action_verb_count = sum(1 for verb in ACTION_VERBS if verb in normalized)
    explanation_connector_count = sum(1 for connector in EXPLANATION_CONNECTORS if connector in normalized)
    disclaimer_present = int("disclaimer" in normalized and "synthetic" in normalized)
    coverage = signal_coverage(text, profile)
    feature_count = sum(feature_hits.values())
    category_count = sum(category_hits.values())

    # A simple report-quality score, not a medical accuracy score. It intentionally rewards
    # action diversity and explanatory depth so teacher-generated distillation data is compared
    # on the qualities it is supposed to add beyond a deterministic template.
    # English note: see the surrounding code for this project workflow detail.
    # English note: see the surrounding code for this project workflow detail.
    quality_score = (
        (heading_count / len(REQUIRED_HEADINGS)) * 10.0
        + min(category_count / 8.0, 1.0) * 10.0
        + coverage * 20.0
        + min(feature_count / 10.0, 1.0) * 15.0
        + min(action_verb_count / 12.0, 1.0) * 20.0
        + min(explanation_connector_count / 5.0, 1.0) * 10.0
        + min(word_count / 350.0, 1.0) * 10.0
        + (5.0 if forbidden_count == 0 and disclaimer_present else 0.0)
    )

    row = {
        "distillation_id": distillation_id,
        "person_index": person_index,
        "response_source": source,
        "word_count": word_count,
        "bullet_count": bullet_count,
        "numeric_evidence_count": numeric_evidence_count,
        "action_verb_count": action_verb_count,
        "explanation_connector_count": explanation_connector_count,
        "required_heading_count": heading_count,
        "required_heading_coverage": heading_count / len(REQUIRED_HEADINGS),
        "recommendation_category_count": category_count,
        "feature_evidence_count": feature_count,
        "key_signal_coverage": coverage,
        "forbidden_term_count": forbidden_count,
        "medical_disclaimer_present": disclaimer_present,
        "quality_score": quality_score,
    }
    row.update({"category_" + key: value for key, value in category_hits.items()})
    row.update({"feature_" + key: value for key, value in feature_hits.items()})
    return row


def plot_grouped_metric_summary(summary_df):
    metrics = [
        "required_heading_coverage",
        "key_signal_coverage",
        "feature_evidence_count",
        "action_verb_count",
        "explanation_connector_count",
        "word_count",
        "quality_score",
    ]
    labels = [
        "Heading coverage",
        "Signal coverage",
        "Feature count",
        "Action diversity",
        "Explanation depth",
        "Detail level",
        "Quality score",
    ]
    plot_df = summary_df.set_index("response_source")
    values = []
    for metric in metrics:
        vals = plot_df[metric].values.astype(float)
        if metric == "feature_evidence_count":
            vals = vals / len(FEATURE_KEYWORDS)
        elif metric == "action_verb_count":
            vals = vals / 12.0
        elif metric == "explanation_connector_count":
            vals = vals / 5.0
        elif metric == "word_count":
            vals = vals / 350.0
        elif metric == "quality_score":
            vals = vals / 100.0
        vals = np.clip(vals, 0, 1)
        values.append(vals)
    values = np.asarray(values)

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(11, 5.5))
    sources = list(plot_df.index)
    ax.bar(x - width / 2, values[:, 0], width, label=sources[0], color="#4C78A8")
    ax.bar(x + width / 2, values[:, 1], width, label=sources[1], color="#F28E2B")
    ax.set_title("Qwen Distillation Response vs Local Rule Fallback")
    ax.set_ylabel("Normalized Score")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylim(0, 1.08)
    ax.legend()
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_quality_metrics.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_radar(summary_df):
    metrics = [
        "required_heading_coverage",
        "key_signal_coverage",
        "feature_evidence_count",
        "action_verb_count",
        "explanation_connector_count",
        "word_count",
        "quality_score",
    ]
    labels = [
        "Headings",
        "Signals",
        "Feature Evidence",
        "Action Diversity",
        "Explanation Depth",
        "Detail Level",
        "Overall Quality",
    ]
    plot_df = summary_df.set_index("response_source")
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    colors = ["#4C78A8", "#F28E2B"]
    for source, color in zip(plot_df.index, colors):
        vals = []
        for metric in metrics:
            value = float(plot_df.loc[source, metric])
            if metric == "feature_evidence_count":
                value = value / len(FEATURE_KEYWORDS)
            elif metric == "action_verb_count":
                value = value / 12.0
            elif metric == "explanation_connector_count":
                value = value / 5.0
            elif metric == "word_count":
                value = value / 350.0
            elif metric == "quality_score":
                value = value / 100.0
            value = min(max(value, 0.0), 1.0)
            vals.append(value)
        vals += vals[:1]
        ax.plot(angles, vals, color=color, linewidth=2, label=source)
        ax.fill(angles, vals, color=color, alpha=0.18)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_ylim(0, 1)
    ax.set_title("Recommendation Quality Radar")
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_quality_radar.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_feature_heatmap(score_df):
    feature_columns = ["feature_" + feature for feature in FEATURE_KEYWORDS.keys()]
    rows = []
    labels = []
    for source in ["Qwen teacher distillation", "Local rule-based fallback"]:
        subset = score_df[score_df["response_source"] == source]
        rows.append([subset[column].mean() for column in feature_columns])
        labels.append(source)
    matrix = np.asarray(rows)
    fig, ax = plt.subplots(figsize=(12, 3.8))
    im = ax.imshow(matrix, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax.set_title("Feature Evidence Mention Rate by Response Source")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xticks(np.arange(len(FEATURE_KEYWORDS)))
    ax.set_xticklabels(list(FEATURE_KEYWORDS.keys()), rotation=35, ha="right")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, "{:.0%}".format(matrix[i, j]), ha="center", va="center", color="black", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_feature_mention_heatmap.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_sample_quality(score_df):
    pivot = score_df.pivot(index="distillation_id", columns="response_source", values="quality_score").reset_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    marker = "o" if len(pivot) <= 80 else None
    x = np.arange(len(pivot))
    ax.plot(x, pivot["Qwen teacher distillation"], marker=marker, label="Qwen teacher distillation", color="#4C78A8")
    ax.plot(x, pivot["Local rule-based fallback"], marker=marker, label="Local rule-based fallback", color="#F28E2B")
    ax.set_title("Per-Sample Recommendation Quality Score")
    ax.set_xlabel("Distillation Sample ID")
    ax.set_ylabel("Quality Score (0-100)")
    ax.set_ylim(0, 105)
    apply_sparse_id_ticks(ax, pivot["distillation_id"])
    ax.legend()
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_quality_by_sample.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_word_count(score_df):
    pivot = score_df.pivot(index="distillation_id", columns="response_source", values="word_count").reset_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    if len(pivot) <= 80:
        x = np.arange(len(pivot))
        width = 0.38
        ax.bar(x - width / 2, pivot["Qwen teacher distillation"], width, label="Qwen teacher distillation", color="#4C78A8")
        ax.bar(x + width / 2, pivot["Local rule-based fallback"], width, label="Local rule-based fallback", color="#F28E2B")
        ax.set_title("Recommendation Detail Level: Word Count by Sample")
        ax.set_xlabel("Distillation Sample ID")
        apply_sparse_id_ticks(ax, pivot["distillation_id"])
    else:
        ax.hist(
            [pivot["Qwen teacher distillation"], pivot["Local rule-based fallback"]],
            bins=35,
            label=["Qwen teacher distillation", "Local rule-based fallback"],
            color=["#4C78A8", "#F28E2B"],
            alpha=0.65,
        )
        ax.set_title("Recommendation Detail Level: Word Count Distribution")
        ax.set_xlabel("Word Count")
    ax.set_ylabel("Sample Count" if len(pivot) > 80 else "Word Count")
    ax.legend()
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_word_count.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_quality_gain(score_df):
    pivot = score_df.pivot(index="distillation_id", columns="response_source", values="quality_score").reset_index()
    pivot["quality_gain"] = pivot["Qwen teacher distillation"] - pivot["Local rule-based fallback"]

    fig, ax = plt.subplots(figsize=(10, 5))
    if len(pivot) <= 80:
        colors = np.where(pivot["quality_gain"] >= 0, "#59A14F", "#E15759")
        x = np.arange(len(pivot))
        ax.bar(x, pivot["quality_gain"], color=colors)
        ax.set_xlabel("Distillation Sample ID")
        apply_sparse_id_ticks(ax, pivot["distillation_id"])
    else:
        ax.hist(pivot["quality_gain"], bins=35, color="#59A14F", edgecolor="white")
        ax.axvline(0, color="#333333", linewidth=1)
        ax.axvline(pivot["quality_gain"].mean(), color="#333333", linewidth=1.5, label="Mean")
        ax.set_xlabel("Quality Score Difference")
        ax.set_ylabel("Sample Count")
        ax.legend()
    if len(pivot) <= 80:
        ax.axhline(0, color="#333333", linewidth=1)
    ax.set_title("Qwen Teacher Quality Gain Over Local Fallback")
    if len(pivot) <= 80:
        ax.set_ylabel("Quality Score Difference")
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_quality_gain.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_component_delta(summary_df):
    plot_df = summary_df.set_index("response_source")
    qwen = plot_df.loc["Qwen teacher distillation"]
    fallback = plot_df.loc["Local rule-based fallback"]
    metrics = [
        ("Quality score", "quality_score"),
        ("Words", "word_count"),
        ("Bullets", "bullet_count"),
        ("Action verbs", "action_verb_count"),
        ("Explanation links", "explanation_connector_count"),
        ("Recommendation categories", "recommendation_category_count"),
    ]
    labels = [label for label, _ in metrics]
    deltas = [float(qwen[column] - fallback[column]) for _, column in metrics]

    fig, ax = plt.subplots(figsize=(10, 5.2))
    colors = ["#59A14F" if value >= 0 else "#E15759" for value in deltas]
    ax.barh(labels, deltas, color=colors)
    ax.axvline(0, color="#333333", linewidth=1)
    ax.set_title("Where Qwen Teacher Responses Improve Over Local Fallback")
    ax.set_xlabel("Average Difference: Qwen - Local Fallback")
    for i, value in enumerate(deltas):
        ax.text(value, i, " {:.1f}".format(value), va="center", ha="left" if value >= 0 else "right")
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_component_delta.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_category_heatmap(score_df):
    category_columns = ["category_" + category for category in RECOMMENDATION_CATEGORIES]
    rows = []
    labels = []
    for source in ["Qwen teacher distillation", "Local rule-based fallback"]:
        subset = score_df[score_df["response_source"] == source]
        rows.append([subset[column].mean() for column in category_columns])
        labels.append(source)

    matrix = np.asarray(rows)
    fig, ax = plt.subplots(figsize=(10, 3.6))
    im = ax.imshow(matrix, aspect="auto", cmap="Greens", vmin=0, vmax=1)
    ax.set_title("Recommendation Category Coverage by Response Source")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xticks(np.arange(len(RECOMMENDATION_CATEGORIES)))
    ax.set_xticklabels([item.title() for item in RECOMMENDATION_CATEGORIES], rotation=25, ha="right")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, "{:.0%}".format(matrix[i, j]), ha="center", va="center", color="black", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_category_coverage_heatmap.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_safety_coverage_dashboard(summary_df):
    plot_df = summary_df.set_index("response_source")
    rows = []
    for source in ["Qwen teacher distillation", "Local rule-based fallback"]:
        row = plot_df.loc[source]
        rows.append([
            float(row["required_heading_coverage"]),
            float(row["key_signal_coverage"]),
            float(row["medical_disclaimer_present"]),
            1.0 if float(row["forbidden_term_count"]) == 0 else 0.0,
        ])

    matrix = np.asarray(rows)
    columns = ["Required headings", "Risk-signal coverage", "Medical disclaimer", "No forbidden terms"]
    fig, ax = plt.subplots(figsize=(9, 3.5))
    im = ax.imshow(matrix, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_title("Safety and Format Compliance Dashboard")
    ax.set_yticks(np.arange(2))
    ax.set_yticklabels(["Qwen teacher distillation", "Local rule-based fallback"])
    ax.set_xticks(np.arange(len(columns)))
    ax.set_xticklabels(columns, rotation=20, ha="right")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, "{:.0%}".format(matrix[i, j]), ha="center", va="center", color="black", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_safety_compliance.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_action_explanation_scatter(score_df):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = {
        "Qwen teacher distillation": "#4C78A8",
        "Local rule-based fallback": "#F28E2B",
    }
    for source, subset in score_df.groupby("response_source"):
        ax.scatter(
            subset["action_verb_count"],
            subset["explanation_connector_count"],
            s=np.clip(subset["word_count"], 120, 450),
            alpha=0.55,
            color=colors[source],
            label=source,
            edgecolor="white",
            linewidth=0.8,
        )
    ax.set_title("Recommendation Richness: Actions vs Explanation Depth")
    ax.set_xlabel("Action Verb Count")
    ax.set_ylabel("Explanation Connector Count")
    ax.legend()
    fig.tight_layout()
    path = FIGURE_DIR / "qwen_vs_fallback_action_explanation_scatter.png"
    fig.savefig(str(path), dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def save_advantage_summary(summary_df):
    plot_df = summary_df.set_index("response_source")
    qwen = plot_df.loc["Qwen teacher distillation"]
    fallback = plot_df.loc["Local rule-based fallback"]
    rows = []
    for metric in [
        "quality_score",
        "word_count",
        "bullet_count",
        "action_verb_count",
        "explanation_connector_count",
        "feature_evidence_count",
        "key_signal_coverage",
        "medical_disclaimer_present",
        "forbidden_term_count",
    ]:
        qwen_value = float(qwen[metric])
        fallback_value = float(fallback[metric])
        delta = qwen_value - fallback_value
        relative = np.nan
        if fallback_value != 0:
            relative = delta / fallback_value * 100
        rows.append({
            "Metric": metric,
            "Qwen Teacher": qwen_value,
            "Local Fallback": fallback_value,
            "Absolute Difference": delta,
            "Relative Difference Percent": relative,
        })
    path = REPORT_DIR / "qwen_vs_fallback_advantage_summary.csv"
    pd.DataFrame(rows, columns=[
        "Metric",
        "Qwen Teacher",
        "Local Fallback",
        "Absolute Difference",
        "Relative Difference Percent",
    ]).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def main():
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    df, source_path = load_distillation_data()
    score_rows = []
    for _, row in df.iterrows():
        profile = json.loads(row["input_profile_json"])
        qwen_text = row["teacher_response"]
        fallback_text = fallback_recommendation(profile)
        score_rows.append(analyze_response("Qwen teacher distillation", qwen_text, profile, int(row["distillation_id"]), int(row["person_index"])))
        score_rows.append(analyze_response("Local rule-based fallback", fallback_text, profile, int(row["distillation_id"]), int(row["person_index"])))

    print("Using distillation dataset:", source_path)
    print("Rows included in benefit analysis:", len(df))
    score_df = pd.DataFrame(score_rows)
    score_path = REPORT_DIR / "qwen_vs_fallback_quality_scores.csv"
    score_df.to_csv(score_path, index=False, encoding="utf-8-sig")

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
    # Keep Qwen first in plots.
    # English note: see the surrounding code for this project workflow detail.
    summary_df["source_order"] = summary_df["response_source"].map({
        "Qwen teacher distillation": 0,
        "Local rule-based fallback": 1,
    })
    summary_df = summary_df.sort_values("source_order").drop("source_order", axis=1)
    summary_path = REPORT_DIR / "qwen_vs_fallback_quality_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    advantage_path = save_advantage_summary(summary_df)

    figure_paths = [
        plot_grouped_metric_summary(summary_df),
        plot_radar(summary_df),
        plot_feature_heatmap(score_df),
        plot_sample_quality(score_df),
        plot_word_count(score_df),
        plot_quality_gain(score_df),
        plot_component_delta(summary_df),
        plot_category_heatmap(score_df),
        plot_safety_coverage_dashboard(summary_df),
        plot_action_explanation_scatter(score_df),
    ]

    print("Saved distillation benefit reports:")
    print(score_path)
    print(summary_path)
    print(advantage_path)
    print("Saved distillation benefit figures:")
    for path in figure_paths:
        print(path)


if __name__ == "__main__":
    main()
