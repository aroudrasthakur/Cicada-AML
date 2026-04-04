"""Behavioral Lens: detects economically unnecessary activity."""
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BehavioralAutoencoder(nn.Module):
    def __init__(self, input_dim: int, latent_dim: int = 32):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, latent_dim), nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 64), nn.ReLU(),
            nn.Linear(64, 128), nn.ReLU(),
            nn.Linear(128, input_dim),
        )

    def forward(self, x):
        z = self.encoder(x)
        return self.decoder(z)


class BehavioralLens:
    LENS_TAGS = ["behavioral"]

    def __init__(self):
        self.xgb_model = None
        self.autoencoder = None
        self.scaler = None
        self.feature_names = None

    def _select_features(self, features_df: pd.DataFrame, heuristic_scores: np.ndarray) -> np.ndarray:
        """Combine behavioral features with heuristic scores tagged for this lens."""
        behavioral_cols = [c for c in features_df.columns if c in {
            "amount", "log_amount", "fee_ratio", "is_round_amount",
            "burstiness_score", "amount_deviation", "sender_tx_count",
            "receiver_tx_count", "sender_repeat_count",
            "balance_ratio", "unique_counterparties", "relay_pattern_score",
        }]
        feat = features_df[behavioral_cols].fillna(0).values if behavioral_cols else np.zeros((len(features_df), 1))
        if heuristic_scores is not None and len(heuristic_scores) > 0:
            if heuristic_scores.ndim == 1:
                heuristic_scores = heuristic_scores.reshape(1, -1)
            h_expanded = np.broadcast_to(heuristic_scores, (feat.shape[0], heuristic_scores.shape[-1])) if heuristic_scores.shape[0] == 1 else heuristic_scores
            feat = np.hstack([feat, h_expanded[:feat.shape[0]]])
        return feat.astype(np.float32)

    def predict(self, features_df: pd.DataFrame, heuristic_scores: np.ndarray = None) -> dict:
        """Run inference. Returns behavioral_score and behavioral_anomaly_score."""
        X = self._select_features(features_df, heuristic_scores)
        behavioral_score = np.zeros(X.shape[0])
        anomaly_score = np.zeros(X.shape[0])
        if self.xgb_model is not None:
            behavioral_score = self.xgb_model.predict_proba(X)[:, 1] if hasattr(self.xgb_model, 'predict_proba') else self.xgb_model.predict(X)
        if self.autoencoder is not None:
            self.autoencoder.eval()
            with torch.no_grad():
                tensor = torch.FloatTensor(X)
                recon = self.autoencoder(tensor)
                anomaly_score = ((tensor - recon) ** 2).mean(dim=1).numpy()
        return {"behavioral_score": behavioral_score, "behavioral_anomaly_score": anomaly_score}

    def load(self, xgb_path: str, ae_path: str):
        xgb_p, ae_p = Path(xgb_path), Path(ae_path)
        if xgb_p.exists():
            self.xgb_model = joblib.load(xgb_p)
            logger.info(f"Loaded behavioral XGBoost from {xgb_p}")
        if ae_p.exists():
            state = torch.load(ae_p, map_location="cpu", weights_only=True)
            input_dim = state.get("input_dim", 32)
            self.autoencoder = BehavioralAutoencoder(input_dim)
            self.autoencoder.load_state_dict(state["model_state_dict"])
            logger.info(f"Loaded behavioral autoencoder from {ae_p}")
