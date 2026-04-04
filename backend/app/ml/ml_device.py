"""Resolve PyTorch / XGBoost device from settings with CPU fallback."""
from __future__ import annotations

import torch
from xgboost import XGBClassifier

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def resolve_torch_device() -> torch.device:
    """CUDA if enabled and available, else MPS (Apple), else CPU."""
    if not settings.ml_use_gpu:
        return torch.device("cpu")
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    logger.warning("ML_USE_GPU is enabled but no CUDA/MPS device found; using CPU")
    return torch.device("cpu")


def xgboost_fit_kwargs() -> dict:
    """Extra kwargs for ``XGBClassifier`` (XGBoost 2.x ``device`` + ``tree_method``)."""
    if not settings.ml_use_gpu:
        return {"tree_method": "hist", "device": "cpu"}
    if torch.cuda.is_available():
        return {"tree_method": "hist", "device": "cuda"}
    logger.warning("ML_USE_GPU is enabled but CUDA is not available for XGBoost; using CPU")
    return {"tree_method": "hist", "device": "cpu"}


def fit_xgboost_classifier(
    model: XGBClassifier,
    X_train,
    y_train,
    *,
    eval_set=None,
    verbose: bool = False,
) -> XGBClassifier:
    """Fit XGBoost; on CUDA failure, rebuild with CPU and retry once."""
    try:
        if eval_set is not None:
            model.fit(X_train, y_train, eval_set=eval_set, verbose=verbose)
        else:
            model.fit(X_train, y_train, verbose=verbose)
        return model
    except Exception as e:
        params = model.get_params()
        dev = params.get("device")
        if not settings.ml_use_gpu or dev is None or not str(dev).startswith("cuda"):
            raise
        logger.warning("XGBoost GPU fit failed (%s); retrying on CPU", e)
        params = dict(params)
        params["device"] = "cpu"
        params["tree_method"] = "hist"
        cpu_model = XGBClassifier(**params)
        if eval_set is not None:
            cpu_model.fit(X_train, y_train, eval_set=eval_set, verbose=verbose)
        else:
            cpu_model.fit(X_train, y_train, verbose=verbose)
        return cpu_model


def log_device_banner(module_logger, label: str = "ML") -> None:
    """Log chosen device once per process (useful in training scripts)."""
    d = resolve_torch_device()
    xkw = xgboost_fit_kwargs()
    module_logger.info(
        "[%s] device=%s  XGBoost device=%s",
        label,
        d,
        xkw.get("device", "cpu"),
    )
