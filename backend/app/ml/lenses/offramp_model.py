"""Off-ramp Lens: conversion and exit pattern detection."""
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)

OFFRAMP_NUMERIC_FEATURES = [
    "fan_in_ratio", "weighted_in", "in_degree",
    "suspicious_neighbor_ratio_1hop", "suspicious_neighbor_ratio_2hop",
    "amount", "log_amount", "relay_pattern_score",
]

class OfframpLens:
    LENS_TAGS = ["offramp"]

    def __init__(self):
        self.classifier = None

    def _select_features(self, features_df: pd.DataFrame) -> np.ndarray:
        """8 offramp columns in fixed order (must match train_offramp)."""
        n = len(features_df)
        if features_df.empty or n == 0:
            return np.zeros((0, len(OFFRAMP_NUMERIC_FEATURES)), dtype=np.float32)
        out = np.zeros((n, len(OFFRAMP_NUMERIC_FEATURES)), dtype=np.float32)
        for j, name in enumerate(OFFRAMP_NUMERIC_FEATURES):
            if name in features_df.columns:
                out[:, j] = features_df[name].fillna(0).to_numpy(dtype=np.float64)
        return out

    @staticmethod
    def _heuristic_aggregates(h_vec: np.ndarray | None) -> np.ndarray:
        h = np.asarray(h_vec, dtype=np.float32).ravel() if h_vec is not None else np.zeros(185, dtype=np.float32)
        nz = h[h > 0]
        hm = float(nz.mean()) if len(nz) else 0.0
        hx = float(h.max())
        htc = float(np.sum(h > 0))
        return np.array([[hm, hx, htc, hx]], dtype=np.float32)

    def predict(self, features_df: pd.DataFrame, heuristic_scores: np.ndarray = None, context: dict = None) -> dict:
        base = self._select_features(features_df)
        n = base.shape[0]
        if n == 0:
            return {"offramp_score": np.array([])}
        agg = self._heuristic_aggregates(heuristic_scores)
        agg = np.repeat(agg, n, axis=0)
        x = np.hstack([base, agg]).astype(np.float32)
        if self.classifier is not None:
            try:
                scores = (
                    self.classifier.predict_proba(x)[:, 1]
                    if hasattr(self.classifier, "predict_proba")
                    else self.classifier.predict(x)
                )
            except Exception as exc:
                logger.warning("Offramp classifier inference failed: %s", exc)
                scores = np.zeros(n)
        else:
            scores = np.zeros(n)
        return {"offramp_score": scores}

    def load(self, model_path: str):
        p = Path(model_path)
        if p.exists():
            self.classifier = joblib.load(p)
            logger.info(f"Loaded off-ramp classifier from {p}")
