# Model Card — Hospital No-Show Risk (HGBM + isotonic)
Version: v1.0 (2026-09-21) | Owner: TBD | Review: quarterly

## Intended use
Triage appointment no-show risk to prioritize reminders and risk-based overbooking.
NOT for clinical decisions or penalizing individual patients.

## Training data
110,514 appointments (Kaggle Medical Appointment No Shows, Apr–Jun 2016, cleaned + feature-engineered v2).
Target `no_show` base rate 20.19%. Stratified 80/20 split, random_state=42.

## Features
Numeric: age, lead_time_days, scheduled_hour, scholarship, hypertension, diabetes, alcoholism, handicap (raw 0–4), sms_received, has_any_condition, n_conditions.
Categoricals: gender, age_group (0-18/19-35/36-50/51-64/65+), neighbourhood (77 after OTHER grouping), appointment_dow (0–5, no Sunday).
Dropped (leakage/noise): scheduledday, appointmentday, is_weekend (n=39), conditions string.

## Performance (test, n=22,103)
PR-AUC 0.3831 (uncal HGBM), ROC 0.7425; calibrated Brier 0.1422, mean proba 0.2024 ≈ base rate.
@0.25: prec 0.338, rec 0.678, F1 0.451, flagged 40.6%. @0.35: prec 0.410, rec 0.275, flagged 13.5%.

## Subgroup performance
See reports/fairness_table.csv. Recall: 19–35 0.89 vs 65+ 0.29; parity gap 0.444 (age), TPR gap 0.599. Seniors under-flagged (calibrated-correct, ops-unequal).

## Known limitations (I1–I7)
No patient history (PatientId dropped); SMS is selection proxy (Simpson's); hours 20/21 tiny-n (kept numeric, tested grouping, no gain); OHE-neighbourhood PR −0.008 vs native categorical (deploy native, interpret OHE); costs $100/$30 placeholders; +5 cap needs capacity sign-off.

## Ethical considerations
Do not use gender/neighbourhood/age to deny care. Monitor parity/TPR gaps monthly. Segment thresholds available but raise flagged rate to 65% — values decision required.

## Deployment
Artifact: models/best_calibrated.joblib. Threshold via reports/threshold_decision_rule.csv (default 0.25 at FN/FP≈3.3; 0.35 if flag budget ≤20%). Overbooking: (0.25,+5) saves ~62%/day in sim; validate waiting room D≤2.
