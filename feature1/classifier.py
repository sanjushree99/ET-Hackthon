"""
XGBoost multi-class classifier with Platt scaling calibration.
Calibration ensures confidence scores are meaningful probabilities,
not raw softmax outputs (which XGBoost tends to over-/under-estimate).
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
from xgboost import XGBClassifier

from features import CLASSIFIER_FEATURES
from synthetic_data import get_training_data

MODEL_PATH = Path(__file__).parent / "model.joblib"
ENCODER_PATH = Path(__file__).parent / "label_encoder.joblib"

CATEGORIES = ["industrial", "vehicular", "construction", "biomass", "other"]


def train(save: bool = True):
    df = get_training_data()
    X = df[CLASSIFIER_FEATURES]
    le = LabelEncoder().fit(CATEGORIES)
    y = le.transform(df["true_category"])

    X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    base = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )
    # Platt scaling via sigmoid calibration (cv="prefit" after fitting base)
    base.fit(X_tr.to_numpy(), y_tr)
    calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    calibrated.fit(X_val.to_numpy(), y_val)

    val_preds = calibrated.predict(X_val.to_numpy())
    val_proba = calibrated.predict_proba(X_val.to_numpy())
    print(f"[classifier] val accuracy={accuracy_score(y_val, val_preds):.3f}  "
          f"log-loss={log_loss(y_val, val_proba):.3f}")

    if save:
        joblib.dump(calibrated, MODEL_PATH)
        joblib.dump(le, ENCODER_PATH)
        print(f"[classifier] saved -> {MODEL_PATH}")

    return calibrated, le


def load():
    if not MODEL_PATH.exists():
        print("[classifier] model not found, training now...")
        return train()
    return joblib.load(MODEL_PATH), joblib.load(ENCODER_PATH)


def predict_zones(feature_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns feature_df augmented with:
      - predicted_category
      - confidence  (calibrated probability of predicted class)
      - proba_*     (per-class calibrated probabilities)
    """
    model, le = load()
    X = feature_df[CLASSIFIER_FEATURES].to_numpy()
    proba = model.predict_proba(X)          # shape (n, n_classes)
    pred_idx = np.argmax(proba, axis=1)
    pred_labels = le.inverse_transform(pred_idx)
    confidences = proba[np.arange(len(proba)), pred_idx]

    out = feature_df.copy()
    out["predicted_category"] = pred_labels
    out["confidence"] = confidences
    for i, cat in enumerate(le.classes_):
        out[f"proba_{cat}"] = proba[:, i]
    return out
