"""Document Lens: metadata consistency and narrative analysis."""
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentLens:
    LENS_TAGS = ["document"]

    def __init__(self):
        self.classifier = None
        self.mode = "limited"  # "limited" or "full"

    def predict(self, features_df: pd.DataFrame = None, heuristic_scores: np.ndarray = None, document_events: list[dict] = None) -> dict:
        """Score document risk. Operates in limited mode without document data."""
        n = len(features_df) if features_df is not None else 1
        if document_events:
            self.mode = "full"
            scores = self._score_with_documents(features_df, heuristic_scores, document_events)
        else:
            self.mode = "limited"
            scores = np.full(n, 0.1)
            if heuristic_scores is not None:
                h = heuristic_scores if heuristic_scores.ndim == 1 else heuristic_scores.mean(axis=0)
                scores = np.full(n, float(np.mean(h)) * 0.5) if len(h) > 0 else scores
        return {"document_score": scores, "document_lens_mode": self.mode}

    def _score_with_documents(self, features_df, heuristic_scores, document_events):
        """Full document scoring when document data is available."""
        if self.classifier is not None and features_df is not None:
            X = features_df.fillna(0).values
            return self.classifier.predict_proba(X)[:, 1]
        return np.full(len(features_df) if features_df is not None else 1, 0.3)

    def load(self, model_path: str):
        p = Path(model_path)
        if p.exists():
            self.classifier = joblib.load(p)
            self.mode = "full"
            logger.info(f"Loaded document classifier from {p}")
