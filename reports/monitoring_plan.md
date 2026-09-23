# Monitoring Plan — No-Show Model v1.0
| Metric | Cadence | Threshold | Action |
|---|---|---|---|
| Prediction drift PSI (y_proba_calibrated vs train) | weekly | PSI>0.2 | investigate shift; freeze overbooking cap |
| Feature drift PSI (lead_time_days, age, scheduled_hour) | weekly | PSI>0.2 | check scheduling policy changes |
| Outcome drift (14-day rolling no-show rate vs 20.19%) | daily/weekly | ±3pp | recalibrate threshold via decision rule |
| Fairness drift (age parity gap, TPR gap) | monthly | parity>0.5 or TPR gap>0.65 | ethics review; consider segment thresholds |
| Calibration (Brier, reliability slope) | monthly | Brier>0.16 | refit isotonic on recent 4–8 weeks |
| Ops (doubles/day, wasted/day) | daily | doubles>2/day avg over 7d | raise threshold one step |
Retrain trigger: outcome drift sustained 4 weeks, or feature PSI>0.25 twice, or quarterly refresh. Always re-run fairness + cost-sensitivity before promoting.
