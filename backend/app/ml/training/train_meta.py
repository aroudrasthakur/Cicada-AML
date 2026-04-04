"""Train Meta-Learner: XGBoost on stacked lens scores + heuristic aggregates + data flags."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from app.utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("models/meta")
ARTIFACTS_DIR = Path("models/artifacts")

META_FEATURES = [
    # 6 lens scores
    "behavioral_score",
    "behavioral_anomaly_score",
    "graph_score",
    "entity_score",
    "temporal_score",
    "document_score",
    "offramp_score",
    # heuristic aggregates
    "heuristic_mean",
    "heuristic_max",
    "heuristic_triggered_count",
    "heuristic_top_confidence",
    "heuristic_triggered_ratio",
    # data availability flags
    "has_entity_intel",
    "has_document_intel",
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
            "  python -m scripts.prepare_meta_features --output %s",
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


def _find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
    best_idx = int(np.argmax(f1_scores))
    return {
        "optimal_threshold": float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5,
        "optimal_f1": float(f1_scores[best_idx]),
        "precision_at_threshold": float(precision[best_idx]),
        "recall_at_threshold": float(recall[best_idx]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Meta-Learner")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with preprocessed data")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    logger.info("=== Training Meta-Learner ===")
    df = _load_data(data_dir)

    if "label" not in df.columns:
        logger.error("No 'label' column found in data; cannot train")
        sys.exit(1)

    X, feature_names = _prepare_features(df)
    y = df["label"].values.astype(int)
    logger.info("Meta features: %d total (%s)", len(feature_names), feature_names)

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    spw = n_neg / max(n_pos, 1)
    logger.info("Balance: %d pos / %d neg → spw=%.2f", n_pos, n_neg, spw)

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
    )
    base_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    logger.info("Applying Platt calibration (sigmoid)...")
    calibrated = CalibratedClassifierCV(base_model, cv="prefit", method="sigmoid")
    calibrated.fit(X_val, y_val)

    y_prob = calibrated.predict_proba(X_val)[:, 1]
    pr_auc = average_precision_score(y_val, y_prob)
    roc = roc_auc_score(y_val, y_prob)
    threshold_info = _find_optimal_threshold(y_val, y_prob)
    threshold = threshold_info["optimal_threshold"]

    logger.info("Meta-Learner PR-AUC: %.4f  ROC-AUC: %.4f", pr_auc, roc)
    logger.info("Optimal threshold: %.4f (F1=%.4f, P=%.4f, R=%.4f)",
                threshold, threshold_info["optimal_f1"],
                threshold_info["precision_at_threshold"],
                threshold_info["recall_at_threshold"])
    logger.info("\n%s", classification_report(y_val, (y_prob >= threshold).astype(int), zero_division=0))

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
        "n_val": len(y_val),
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
