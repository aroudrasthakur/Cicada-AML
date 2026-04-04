"""Build ``meta_features.csv`` for :mod:`app.ml.training.train_meta` from ``train_features.csv``.

Lens score columns are filled from ``train_features`` when present; otherwise **0.0** (dev /
fast-iteration mode). For production-quality meta training, extend this script or export scores
from the inference pipeline.

Run from ``backend``::

  python -m scripts.prepare_meta_features --data-dir ../data/processed_subset
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Keep aligned with app.ml.training.train_meta.META_FEATURES
META_FEATURES = [
    "behavioral_score",
    "behavioral_anomaly_score",
    "graph_score",
    "entity_score",
    "temporal_score",
    "offramp_score",
    "heuristic_mean",
    "heuristic_max",
    "heuristic_triggered_count",
    "heuristic_top_confidence",
    "heuristic_triggered_ratio",
    "has_entity_intel",
    "has_address_tags",
    "coverage_tier_0",
    "coverage_tier_1",
    "coverage_tier_2",
    "n_lenses_available",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build meta_features.csv from train_features.csv")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/processed"),
        help="Directory containing train_features.csv (and writes meta_features.csv here)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: <data-dir>/meta_features.csv)",
    )
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    train_path = data_dir / "train_features.csv"
    if not train_path.exists():
        raise FileNotFoundError(f"Not found: {train_path}")

    df = pd.read_csv(train_path)
    if "label" not in df.columns:
        raise ValueError("train_features.csv must contain a 'label' column")

    out = pd.DataFrame()
    out["label"] = pd.to_numeric(df["label"], errors="coerce").fillna(0).astype(int)

    for c in META_FEATURES:
        if c in df.columns:
            out[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0).astype("float64")
        else:
            out[c] = 0.0

    out_path = (args.output or (data_dir / "meta_features.csv")).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    logger.info("Wrote %s (%d rows, %d columns)", out_path, len(out), len(out.columns))


if __name__ == "__main__":
    main()
