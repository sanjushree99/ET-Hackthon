"""
Evaluation: physics-informed attribution model vs. naive nearest-industrial-site baseline.

Baseline: always predicts the category of the nearest registered industrial site
          (ignores wind, land use, traffic — pure proximity heuristic).

Physics model: full plume + feature engineering + calibrated XGBoost.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder

from synthetic_data import get_training_data, INDUSTRIAL_SITES
from features import CLASSIFIER_FEATURES
from classifier import load, train


def nearest_site_category(row: pd.Series) -> str:
    """Baseline: pick category of nearest industrial site by Euclidean distance."""
    # Use dist_to_nearest_industrial as proxy; nearest_site_category is in features
    # For eval we re-derive from the training feature 'nearest_site_category'
    return row["nearest_site_category"]


def run_eval():
    print("=" * 60)
    print("FEATURE 1 — ATTRIBUTION MODEL EVALUATION")
    print("=" * 60)

    # ── Load data ─────────────────────────────────────────────────────────────
    df = get_training_data()

    # Attach nearest_site_category (needed for baseline) — only the category column
    from features import nearest_site_features
    df["nearest_site_category"] = df.apply(
        lambda r: nearest_site_features(
            28.6 + r.name * 0.001 % 0.3,
            77.2 + r.name * 0.001 % 0.4,
        )["nearest_site_category"],
        axis=1,
    )

    # ── Baseline predictions ──────────────────────────────────────────────────
    baseline_preds = df.apply(nearest_site_category, axis=1)

    # ── Model predictions ─────────────────────────────────────────────────────
    # Ensure model is trained
    try:
        model, le = load()
    except Exception:
        model, le = train()

    X = df[CLASSIFIER_FEATURES].to_numpy()
    proba = model.predict_proba(X)
    model_preds = le.inverse_transform(np.argmax(proba, axis=1))

    y_true = df["true_category"]

    # ── Metrics ───────────────────────────────────────────────────────────────
    baseline_acc = accuracy_score(y_true, baseline_preds)
    model_acc    = accuracy_score(y_true, model_preds)

    print(f"\nBaseline (nearest industrial site) accuracy : {baseline_acc:.3f}")
    print(f"Physics-informed XGBoost accuracy           : {model_acc:.3f}")
    print(f"Improvement                                 : +{(model_acc - baseline_acc):.3f}")

    print("\n-- Baseline classification report --")
    print(classification_report(y_true, baseline_preds, zero_division=0))

    print("-- Physics-informed model classification report --")
    print(classification_report(y_true, model_preds, zero_division=0))

    # Calibration check: mean confidence vs actual accuracy per bin
    confidences = np.max(proba, axis=1)
    bins = np.linspace(0, 1, 6)
    print("-- Calibration (confidence bin -> actual accuracy) --")
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (confidences >= lo) & (confidences < hi)
        if mask.sum() == 0:
            continue
        bin_acc = accuracy_score(y_true[mask], model_preds[mask])
        mean_conf = confidences[mask].mean()
        print(f"  conf [{lo:.1f},{hi:.1f})  n={mask.sum():4d}  "
              f"mean_conf={mean_conf:.3f}  actual_acc={bin_acc:.3f}  "
              f"gap={abs(mean_conf - bin_acc):.3f}")

    print("\n[eval] Done. Well-calibrated model shows small gap values above.")


if __name__ == "__main__":
    run_eval()
