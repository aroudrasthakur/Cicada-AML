"""Off-ramp Lens: conversion and exit pattern detection."""
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OfframpLens:
    LENS_TAGS = ["offramp"]

    def __init__(self):
        self.classifier = None

    def _select_features(self, features_df: pd.DataFrame, heuristic_scores: np.ndarray = None) -> np.ndarray:
        offramp_cols = [c for c in features_df.columns if c in {
            "fan_in_ratio", "weighted_in", "in_degree",
            "suspicious_neighbor_ratio_1hop", "suspicious_neighbor_ratio_2hop",
            "amount", "log_amount", "relay_pattern_score",
        }]
        feat = features_df[offramp_cols].fillna(0).values if offramp_cols else np.zeros((len(features_df), 1))
        if heuristic_scores is not None and len(heuristic_scores) > 0:
            if heuristic_scores.ndim == 1:
                heuristic_scores = heuristic_scores.reshape(1, -1)
            h = np.broadcast_to(heuristic_scores, (feat.shape[0], heuristic_scores.shape[-1])) if heuristic_scores.shape[0] == 1 else heuristic_scores
            feat = np.hstack([feat, h[:feat.shape[0]]])
        return feat.astype(np.float32)

    def predict(self, features_df: pd.DataFrame, heuristic_scores: np.ndarray = None, context: dict = None) -> dict:
        X = self._select_features(features_df, heuristic_scores)
        if self.classifier is not None:
            scores = self.classifier.predict_proba(X)[:, 1] if hasattr(self.classifier, 'predict_proba') else self.classifier.predict(X)
        else:
            scores = np.zeros(X.shape[0])
        return {"offramp_score": scores}

    def load(self, model_path: str):
        p = Path(model_path)
        if p.exists():
            self.classifier = joblib.load(p)
            logger.info(f"Loaded off-ramp classifier from {p}")
