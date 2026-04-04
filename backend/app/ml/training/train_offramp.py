"""Train Off-ramp Lens: XGBoost on off-ramp features + heuristic scores."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from app.utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("models/offramp")

OFFRAMP_FEATURES = [
    "fan_in_ratio", "weighted_in", "in_degree",
    "suspicious_neighbor_ratio_1hop", "suspicious_neighbor_ratio_2hop",
    "amount", "log_amount", "relay_pattern_score",
]

HEURISTIC_AGGREGATE_FEATURES = [
    "heuristic_mean", "heuristic_max", "heuristic_triggered_count",
    "heuristic_top_confidence",
]


def _load_data(data_dir: Path) -> pd.DataFrame:
    offramp_path = data_dir / "offramp_features.csv"
    train_path = data_dir / "train_features.csv"
    path = offramp_path if offramp_path.exists() else train_path
    if not path.exists():
        logger.error("Training data not found at %s", data_dir)
        logger.info(
            "Run the feature pipeline first:\n"
            "  python -m scripts.prepare_features --output %s",
            data_dir,
        )
        sys.exit(1)
    df = pd.read_csv(path)
    logger.info("Loaded off-ramp data from %s: %d rows", path, len(df))
    return df


def _prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    all_candidates = OFFRAMP_FEATURES + HEURISTIC_AGGREGATE_FEATURES
    cols = [c for c in all_candidates if c in df.columns]
    if not cols:
        logger.warning("No expected feature columns; using all numeric columns")
        cols = df.select_dtypes(include=[np.number]).columns.drop("label", errors="ignore").tolist()
    return df[cols].fillna(0).values.astype(np.float32), cols


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Off-ramp Lens classifier")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with preprocessed data")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    logger.info("=== Training Off-ramp Lens ===")
    df = _load_data(data_dir)

    if "label" not in df.columns:
        logger.error("No 'label' column found in data; cannot train")
        sys.exit(1)

    X, feature_names = _prepare_features(df)
    y = df["label"].values.astype(int)

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    spw = n_neg / max(n_pos, 1)
    logger.info("Features=%d  balance: %d pos / %d neg → spw=%.2f", len(feature_names), n_pos, n_neg, spw)

    model = XGBClassifier(
        n_estimators=250,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=spw,
        eval_metric="aucpr",
        early_stopping_rounds=20,
        random_state=42,
        use_label_encoder=False,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    y_prob = model.predict_proba(X_val)[:, 1]
    pr_auc = average_precision_score(y_val, y_prob)
    logger.info("Off-ramp XGBoost PR-AUC on validation: %.4f", pr_auc)
    logger.info("\n%s", classification_report(y_val, (y_prob >= 0.5).astype(int), zero_division=0))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUTPUT_DIR / "offramp_classifier.pkl")
    joblib.dump(feature_names, OUTPUT_DIR / "feature_names.pkl")
    logger.info("Artifacts saved to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
