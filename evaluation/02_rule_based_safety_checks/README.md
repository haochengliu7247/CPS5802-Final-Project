# Rule-Based Hard Safety Checks

This folder contains an automated evaluation-stage safety audit aligned to the existing guideline-derived checklist workbook.

## Inputs

- Five-model output table: `model_outputs\reports\step21_five_model_common_passed_outputs_long.csv`
- Test profiles: `Test.csv`
- Checklist source: `evaluation/checklist/Guideline-derived evaluation checklist/Guideline-derived evaluation checklist.xlsx`

## Outputs

- `rule_based_hard_safety_item_level.csv`: one row per response-rule check.
- `rule_based_hard_safety_response_scores.csv`: one row per model response.
- `rule_based_hard_safety_model_summary.csv`: model-level pass rates and violation rates.
- `rule_based_hard_safety_rule_summary.csv`: rule-level violation rates by model.
- `rule_based_hard_safety_rulebook.json`: rule definitions and checklist/source traceability.

## Model Summary

| model_key               | model_label_short        | n_responses | mean_rule_based_safety_score_100 | median_rule_based_safety_score_100 | hard_policy_pass_rate_percent | rule_based_gate_pass_rate_percent | any_violation_rate_percent | hard_policy_violation_rate_percent | required_context_failure_rate_percent | structure_boundary_failure_rate_percent | avg_total_violations_per_response | avg_hard_policy_violations_per_response | avg_required_context_failures_per_response | critical_violation_responses | major_violation_responses |
| ----------------------- | ------------------------ | ----------- | -------------------------------- | ---------------------------------- | ----------------------------- | --------------------------------- | -------------------------- | ---------------------------------- | ------------------------------------- | --------------------------------------- | --------------------------------- | --------------------------------------- | ------------------------------------------ | ---------------------------- | ------------------------- |
| teacher_qwen25_7b       | Teacher: Qwen2.5-7B      | 2933        | 81.98431639959087                | 80.0                               | 99.727241732015               | 41.15240368223662                 | 58.84759631776338          | 0.2727582679849983                 | 58.74531196726901                     | 0.0                                     | 0.8874872144561882                | 0.002727582679849983                    | 0.8847596317763382                         | 52                           | 1713                      |
| teacher_llama31_8b      | Teacher: Llama 3.1 8B    | 2933        | 85.91885441527447                | 80.0                               | 99.89771564950563             | 47.562222979884076                | 52.43777702011593          | 0.10228435049437436                | 52.4036822366178                      | 0.0                                     | 0.6917831571769519                | 0.0010228435049437436                   | 0.6907603136720082                         | 48                           | 1517                      |
| student_qwen_from_qwen  | Student: 0.5B from Qwen  | 2933        | 83.1145584725537                 | 80.0                               | 100.0                         | 42.75485850664849                 | 57.24514149335151          | 0.0                                | 57.24514149335151                     | 0.0                                     | 0.832253665189226                 | 0.0                                     | 0.832253665189226                          | 47                           | 1664                      |
| student_qwen_from_llama | Student: 0.5B from Llama | 2933        | 89.73576542788953                | 100.0                              | 99.79543129901126             | 52.74463007159904                 | 47.25536992840095          | 0.20456870098874871                | 47.15308557790658                     | 0.0                                     | 0.5001704739174906                | 0.002045687009887487                    | 0.49812478690760315                        | 51                           | 1365                      |
| student_qwen_from_both  | Student: 0.5B from Both  | 2933        | 89.37436072280941                | 100.0                              | 99.96590521650187             | 51.75588135015343                 | 48.24411864984658          | 0.03409478349812479                | 48.24411864984658                     | 0.0                                     | 0.5192635526764405                | 0.00034094783498124785                  | 0.5189226048414592                         | 47                           | 1393                      |

## Highest-Violation Rules

| model_label_short        | rule_id                                 | severity | rule_group              | triggered_count | violation_count | triggered_violation_rate_percent |
| ------------------------ | --------------------------------------- | -------- | ----------------------- | --------------- | --------------- | -------------------------------- |
| Student: 0.5B from Both  | FAMILY_HISTORY_RISK_CONTEXT             | major    | required_safety_context | 1500            | 1369            | 91.26666666666667                |
| Student: 0.5B from Llama | FAMILY_HISTORY_RISK_CONTEXT             | major    | required_safety_context | 1500            | 1348            | 89.86666666666666                |
| Teacher: Llama 3.1 8B    | FAMILY_HISTORY_RISK_CONTEXT             | major    | required_safety_context | 1500            | 1317            | 87.8                             |
| Student: 0.5B from Qwen  | FAMILY_HISTORY_RISK_CONTEXT             | major    | required_safety_context | 1500            | 1169            | 77.93333333333334                |
| Teacher: Qwen2.5-7B      | MEDICATION_USE_CLINICIAN_DISCUSSION     | major    | required_safety_context | 1743            | 1152            | 66.09294320137694                |
| Teacher: Qwen2.5-7B      | FAMILY_HISTORY_RISK_CONTEXT             | major    | required_safety_context | 1500            | 1098            | 73.2                             |
| Student: 0.5B from Qwen  | MEDICATION_USE_CLINICIAN_DISCUSSION     | major    | required_safety_context | 1743            | 876             | 50.25817555938038                |
| Teacher: Llama 3.1 8B    | MEDICATION_USE_CLINICIAN_DISCUSSION     | major    | required_safety_context | 1743            | 502             | 28.800917957544463               |
| Student: 0.5B from Qwen  | MENTAL_HEALTH_SUPPORT_WITHOUT_DIAGNOSIS | major    | required_safety_context | 1451            | 247             | 17.022742935906273               |
| Teacher: Qwen2.5-7B      | MENTAL_HEALTH_SUPPORT_WITHOUT_DIAGNOSIS | major    | required_safety_context | 1451            | 173             | 11.922811853893867               |
| Teacher: Llama 3.1 8B    | CHRONIC_DISEASE_HEALTHCARE_TEAM_CONTEXT | major    | required_safety_context | 1643            | 158             | 9.616555082166768                |
| Teacher: Qwen2.5-7B      | CHRONIC_DISEASE_HEALTHCARE_TEAM_CONTEXT | major    | required_safety_context | 1643            | 127             | 7.72976262933658                 |
| Student: 0.5B from Qwen  | CHRONIC_DISEASE_HEALTHCARE_TEAM_CONTEXT | major    | required_safety_context | 1643            | 102             | 6.20815581253804                 |
| Student: 0.5B from Both  | MEDICATION_USE_CLINICIAN_DISCUSSION     | major    | required_safety_context | 1743            | 70              | 4.016064257028113                |
| Student: 0.5B from Llama | BP_RED_FLAG_URGENT_ATTENTION            | critical | required_safety_context | 50              | 49              | 98.0                             |

Interpretation note: this is a reproducible proxy safety audit, not clinical validation.
