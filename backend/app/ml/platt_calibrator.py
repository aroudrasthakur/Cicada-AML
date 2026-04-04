"""Platt (sigmoid) calibration for XGBoost base models.

Used by the meta-learner. Lives in this module so ``joblib`` pickles reference
``app.ml.platt_calibrator.PlattSigmoidCalibrator``, not ``__main__``.
"""
from __future__ import annotations

import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from app.ml.ml_device import xgb_predict_proba


class PlattSigmoidCalibrator:
    """Sigmoid (Platt) calibration on a fitted classifier's positive-class probabilities.

    Newer scikit-learn rejects ``CalibratedClassifierCV(..., cv='prefit')``; this matches
    that behavior for XGBoost base models.
    """

    def __init__(self, base_estimator: XGBClassifier):
        self.base_estimator = base_estimator
        self._calibrator = LogisticRegression(solver="lbfgs", max_iter=2000, random_state=42)

    def fit(self, X, y) -> "PlattSigmoidCalibrator":
        p = xgb_predict_proba(self.base_estimator, X)[:, 1].reshape(-1, 1)
        self._calibrator.fit(p, np.asarray(y).astype(int))
        return self

    def predict_proba(self, X) -> np.ndarray:
        p = xgb_predict_proba(self.base_estimator, X)[:, 1].reshape(-1, 1)
        return self._calibrator.predict_proba(p)


def ensure_platt_sigmoid_calibrator_on_main() -> None:
    """Older ``meta_model.pkl`` files reference ``__main__.PlattSigmoidCalibrator``."""
    main = sys.modules.get("__main__")
    if main is None:
        return
    if getattr(main, "PlattSigmoidCalibrator", None) is PlattSigmoidCalibrator:
        return
    try:
        setattr(main, "PlattSigmoidCalibrator", PlattSigmoidCalibrator)
    except (AttributeError, TypeError):
        pass
