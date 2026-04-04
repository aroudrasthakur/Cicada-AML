"""Train Meta-Learner: XGBoost on stacked lens scores + heuristic aggregates + data flags."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from app.ml.model_paths import MODELS_DIR
from app.ml.ml_device import fit_xgboost_classifier, log_device_banner, xgboost_fit_kwargs
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlattSigmoidCalibrator:
    """Sigmoid (Platt) calibration on a fitted classifier's positive-class probabilities.

    Newer scikit-learn rejects ``CalibratedClassifierCV(..., cv='prefit')``; this matches
    that behavior for XGBoost base models.
    """

    def __init__(self, base_estimator: XGBClassifier):
        self.base_estimator = base_estimator
        self._calibrator = LogisticRegression(solver="lbfgs", max_iter=2000, random_state=42)

    def fit(self, X, y) -> "PlattSigmoidCalibrator":
        p = self.base_estimator.predict_proba(X)[:, 1].reshape(-1, 1)
        self._calibrator.fit(p, np.asarray(y).astype(int))
        return self

    def predict_proba(self, X) -> np.ndarray:
        p = self.base_estimator.predict_proba(X)[:, 1].reshape(-1, 1)
        return self._calibrator.predict_proba(p)


OUTPUT_DIR = MODELS_DIR / "meta"
ARTIFACTS_DIR = MODELS_DIR / "artifacts"

META_FEATURES = [
    # 5 lens scores
    "behavioral_score",
    "behavioral_anomaly_score",
    "graph_score",
    "entity_score",
    "temporal_score",
    "offramp_score",
    # heuristic aggregates
    "heuristic_mean",
    "heuristic_max",
    "heuristic_triggered_count",
    "heuristic_top_confidence",
    "heuristic_triggered_ratio",
    # data availability flags
    "has_entity_intel",
    "has_address_tags",
    # coverage encoding
    "coverage_tier_0",
    "coverage_tier_1",
    "coverage_tier_2",
    # meta signal
    "n_lenses_available",
]


def _load_data(data_dir: Path) -> pd.DataFrame:
    meta_path = data_dir / "meta_features.csv"
    if not meta_path.exists():
        logger.error("Meta feature file not found at %s", meta_path)
        logger.info(
            "Run the full training pipeline to generate stacked lens scores:\n"
            "  make train-all  OR\n"
            "  python -m scripts.prepare_meta_features --data-dir %s",
            data_dir,
        )
        sys.exit(1)
    df = pd.read_csv(meta_path)
    logger.info("Loaded meta features: %d rows, %d columns", len(df), len(df.columns))
    return df


def _prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    cols = [c for c in META_FEATURES if c in df.columns]
    if len(cols) < len(META_FEATURES):
        missing = set(META_FEATURES) - set(cols)
        logger.warning("Missing %d meta features: %s", len(missing), sorted(missing))
        for m in missing:
            df[m] = 0.0
        cols = META_FEATURES
    return df[cols].fillna(0).values.astype(np.float32), cols


def _find_optimal_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    min_recall: float = 0.95,
) -> dict:
    """Select threshold that maximises precision while keeping recall >= min_recall.

    AML systems prioritise recall on illicit flows.  F1 weights precision
    equally with recall and therefore sets the threshold too high for this
    domain.  Instead we find the *highest* threshold (= best precision)
    that still achieves the target recall.
    """
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)

    # Indices where recall is at or above the target
    valid = recall >= min_recall
    if valid.any():
        # Among valid points, pick the one with best precision
        candidates = np.where(valid)[0]
        best_idx = int(candidates[np.argmax(precision[candidates])])
    else:
        # Fallback: lowest available threshold (highest recall point)
        best_idx = len(thresholds) - 1 if len(thresholds) > 0 else 0

    f1 = float(
        2 * precision[best_idx] * recall[best_idx]
        / (precision[best_idx] + recall[best_idx] + 1e-8)
    )
    return {
        "optimal_threshold": float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5,
        "optimal_f1": f1,
        "precision_at_threshold": float(precision[best_idx]),
        "recall_at_threshold": float(recall[best_idx]),
        "min_recall_target": min_recall,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Meta-Learner")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with preprocessed data")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    logger.info("=== Training Meta-Learner ===")
    log_device_banner(logger, "train_meta")

    # Validate that all lens models exist before training meta-model
    required_models = [
        MODELS_DIR / "behavioral" / "xgboost_behavioral.pkl",
        MODELS_DIR / "graph" / "gat_model.pt",
        MODELS_DIR / "entity" / "entity_classifier.pkl",
        MODELS_DIR / "temporal" / "lstm_model.pt",
        MODELS_DIR / "offramp" / "offramp_classifier.pkl",
    ]
    missing = [str(m) for m in required_models if not m.exists()]
    if missing:
        logger.error("Missing required lens models: %s", missing)
        logger.info("Train all lens models first before training the meta-learner")
        sys.exit(1)
    
    df = _load_data(data_dir)

    if "label" not in df.columns:
        logger.error("No 'label' column found in data; cannot train")
        sys.exit(1)

    X, feature_names = _prepare_features(df)
    y = df["label"].values.astype(int)
    logger.info("Meta features: %d total (%s)", len(feature_names), feature_names)

    X_train, X_holdout, y_train, y_holdout = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y,
    )
    X_cal, X_test, y_cal, y_test = train_test_split(
        X_holdout, y_holdout, test_size=0.5, random_state=42, stratify=y_holdout,
    )
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    spw = n_neg / max(n_pos, 1)
    logger.info(
        "Balance: %d pos / %d neg -> spw=%.2f  |  train=%d  cal=%d  test=%d",
        n_pos, n_neg, spw, len(y_train), len(y_cal), len(y_test),
    )

    base_model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.03,
        scale_pos_weight=spw,
        eval_metric="aucpr",
        early_stopping_rounds=25,
        random_state=42,
        use_label_encoder=False,
        subsample=0.8,
        colsample_bytree=0.8,
        **xgboost_fit_kwargs(),
    )
    base_model = fit_xgboost_classifier(
        base_model, X_train, y_train, eval_set=[(X_cal, y_cal)], verbose=False,
    )

    logger.info("Applying Platt calibration on held-out calibration set...")
    calibrated = PlattSigmoidCalibrator(base_model)
    calibrated.fit(X_cal, y_cal)

    y_prob = calibrated.predict_proba(X_test)[:, 1]
    pr_auc = average_precision_score(y_test, y_prob)
    roc = roc_auc_score(y_test, y_prob)
    threshold_info = _find_optimal_threshold(y_test, y_prob)
    threshold = threshold_info["optimal_threshold"]

    logger.info("Meta-Learner PR-AUC: %.4f  ROC-AUC: %.4f", pr_auc, roc)
    logger.info("Optimal threshold: %.4f (F1=%.4f, P=%.4f, R=%.4f)",
                threshold, threshold_info["optimal_f1"],
                threshold_info["precision_at_threshold"],
                threshold_info["recall_at_threshold"])
    logger.info("\n%s", classification_report(y_test, (y_prob >= threshold).astype(int), zero_division=0))

    importances = base_model.feature_importances_
    importance_pairs = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    logger.info("Feature importance (top 10):")
    for name, imp in importance_pairs[:10]:
        logger.info("  %-35s %.4f", name, imp)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(calibrated, OUTPUT_DIR / "meta_model.pkl")
    joblib.dump(feature_names, OUTPUT_DIR / "feature_names.pkl")

    threshold_config = {
        "decision_threshold": threshold,
        "high_risk_threshold": min(threshold * 1.5, 0.95),
        "low_risk_ceiling": max(threshold * 0.5, 0.1),
        **threshold_info,
    }
    with open(ARTIFACTS_DIR / "threshold_config.json", "w") as f:
        json.dump(threshold_config, f, indent=2)

    metrics_report = {
        "pr_auc": pr_auc,
        "roc_auc": roc,
        "threshold": threshold,
        "n_train": len(y_train),
        "n_cal": len(y_cal),
        "n_test": len(y_test),
        "n_features": len(feature_names),
        "feature_importance": {name: float(imp) for name, imp in importance_pairs},
    }
    with open(ARTIFACTS_DIR / "metrics_report.json", "w") as f:
        json.dump(metrics_report, f, indent=2)

    importance_df = pd.DataFrame(importance_pairs, columns=["feature", "importance"])
    importance_df.to_csv(ARTIFACTS_DIR / "feature_importance.csv", index=False)

    logger.info("Artifacts saved to %s and %s", OUTPUT_DIR, ARTIFACTS_DIR)


if __name__ == "__main__":
    main()
