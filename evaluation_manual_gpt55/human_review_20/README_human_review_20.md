# Human Review 20

This folder contains a targeted human-style review of 20 difficult or ambiguous GPT-5.5 sampled validation rows.

Important: this is a strict structured review against the existing professional medical checklist. It is not physician clinical validation.

Files:
- selected_20_candidates.csv / .xlsx: selected review candidates and automated judge context.
- human_review_packet.md: full review packet used for inspection.
- human_review_20_filled.csv / .xlsx: completed structured review.
- human_review_summary_by_model.csv / .xlsx: model-level summary for the 20 targeted cases.
- human_review_summary_overall.csv / .xlsx: overall targeted-review summary.

Selection rule: the review prioritizes GPT-5.5 fail/borderline rows, possible direct diagnosis, unsupported claims, unsafe medication or nicotine-product boundaries, MedGemma gate issues, and rule-based safety-context failures.

Reporting note: because these are intentionally difficult cases, the pass rate should not be interpreted as the model's overall pass rate.