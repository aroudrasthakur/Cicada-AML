"""Behavioral Lens: detects economically unnecessary activity."""
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
from pathlib import Path

from app.ml.ml_device import resolve_torch_device, xgb_predict_proba
from app.utils.logger import get_logger

logger = get_logger(__name__)

BEHAVIORAL_FEATURE_ORDER = [
    "amount", "log_amount", "fee_ratio", "is_round_amount",
    "burstiness_score", "amount_deviation", "sender_tx_count",
    "receiver_tx_count", "sender_repeat_count",
    "balance_ratio", "unique_counterparties", "relay_pattern_score",
]


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
        self._device = None

    def _select_features(self, features_df: pd.DataFrame, heuristic_scores: np.ndarray) -> np.ndarray:
        """12 columns in fixed order (must match train_behavioral / scaler)."""
        n = len(features_df)
        if features_df.empty or n == 0:
            return np.zeros((0, len(BEHAVIORAL_FEATURE_ORDER)), dtype=np.float32)
        out = np.zeros((n, len(BEHAVIORAL_FEATURE_ORDER)), dtype=np.float32)
        for j, name in enumerate(BEHAVIORAL_FEATURE_ORDER):
            if name in features_df.columns:
                out[:, j] = features_df[name].fillna(0).to_numpy(dtype=np.float64)
        return out

    def predict(self, features_df: pd.DataFrame, heuristic_scores: np.ndarray = None) -> dict:
        """Run inference. Returns behavioral_score and behavioral_anomaly_score."""
        X = self._select_features(features_df, heuristic_scores)
        
        # Apply scaler if available (trained models expect scaled features)
        if self.scaler is not None:
            X = self.scaler.transform(X)
        
        behavioral_score = np.zeros(X.shape[0])
        anomaly_score = np.zeros(X.shape[0])
        if self.xgb_model is not None:
            behavioral_score = xgb_predict_proba(self.xgb_model, X)[:, 1] if hasattr(self.xgb_model, 'predict_proba') else self.xgb_model.predict(X)
        if self.autoencoder is not None:
            device = self._device or resolve_torch_device()
            self.autoencoder.eval()
            with torch.no_grad():
                tensor = torch.FloatTensor(X).to(device)
                recon = self.autoencoder(tensor)
                anomaly_score = ((tensor - recon) ** 2).mean(dim=1).cpu().numpy()
        return {"behavioral_score": behavioral_score, "behavioral_anomaly_score": anomaly_score}

    def load(self, xgb_path: str, ae_path: str):
        xgb_p, ae_p = Path(xgb_path), Path(ae_path)
        if xgb_p.exists():
            self.xgb_model = joblib.load(xgb_p)
            logger.info(f"Loaded behavioral XGBoost from {xgb_p}")
        
        # Load scaler
        scaler_path = xgb_p.parent / "scaler_behavioral.pkl"
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)
            logger.info(f"Loaded behavioral scaler from {scaler_path}")
        
        if ae_p.exists():
            self._device = resolve_torch_device()
            state = torch.load(ae_p, map_location=self._device, weights_only=True)
            input_dim = state.get("input_dim", 32)
            self.autoencoder = BehavioralAutoencoder(input_dim)
            self.autoencoder.load_state_dict(state["model_state_dict"])
            self.autoencoder.to(self._device)
            logger.info(f"Loaded behavioral autoencoder from {ae_p} (device={self._device})")
