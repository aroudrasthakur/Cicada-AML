"""Resolve PyTorch / XGBoost device from settings with CPU fallback."""
from __future__ import annotations

import numpy as np
import torch
import xgboost as xgb
from xgboost import XGBClassifier
from xgboost.callback import TrainingCallback

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_xgb_use_gpu: bool | None = None


def _xgb_cuda_available() -> bool:
    """Cached check: is XGBoost CUDA inference viable?"""
    global _xgb_use_gpu
    if _xgb_use_gpu is not None:
        return _xgb_use_gpu
    if not settings.ml_use_gpu:
        _xgb_use_gpu = False
        return False
    _xgb_use_gpu = torch.cuda.is_available()
    return _xgb_use_gpu


def xgb_predict_proba(model, X: np.ndarray) -> np.ndarray:
    """GPU-native ``predict_proba`` for any XGBClassifier / Booster-backed model.

    When the model lives on CUDA, builds an ``xgb.DMatrix`` so data flows through
    the GPU path without the "mismatched devices / falling back" warning.
    Returns shape ``(n, 2)`` identical to ``XGBClassifier.predict_proba``.
    """
    if not _xgb_cuda_available():
        return model.predict_proba(X)

    booster = _extract_booster(model)
    if booster is None:
        return model.predict_proba(X)

    dm = xgb.DMatrix(X, nthread=-1)
    raw = booster.predict(dm)

    if raw.ndim == 1:
        pos = raw.astype(np.float64)
        return np.column_stack([1.0 - pos, pos])
    return raw.astype(np.float64)


def _extract_booster(model) -> xgb.Booster | None:
    """Get the underlying Booster from an XGBClassifier (or calibrated wrapper)."""
    if isinstance(model, xgb.Booster):
        return model
    if isinstance(model, XGBClassifier):
        try:
            return model.get_booster()
        except Exception:
            return None
    return None


class _XGBoostRoundLogger(TrainingCallback):
    """Log boosting rounds (epoch equivalent) via the application logger."""

    def __init__(self, period: int, n_estimators: int, log) -> None:
        self.period = max(1, period)
        self.n_estimators = int(n_estimators)
        self._log = log

    def after_iteration(self, model, epoch, evals_log) -> bool:
        current = epoch + 1
        if current != 1 and current % self.period != 0:
            return False
        parts: list[str] = []
        if evals_log:
            for ds_name, metrics in evals_log.items():
                for m_name, values in metrics.items():
                    if values:
                        parts.append(f"{ds_name}-{m_name}={float(values[-1]):.6f}")
        msg = ", ".join(parts) if parts else "(no eval metrics)"
        self._log.info("XGBoost round %d/%d  %s", current, self.n_estimators, msg)
        return False


def _attach_round_logger(model: XGBClassifier, log_period: int | None) -> None:
    if log_period is None or log_period <= 0:
        return
    n_est = int(model.get_params().get("n_estimators") or 100)
    cb = _XGBoostRoundLogger(period=log_period, n_estimators=n_est, log=logger)
    existing = list(model.callbacks or [])
    model.set_params(callbacks=existing + [cb])
    logger.info(
        "XGBoost: starting training (up to %d boosting rounds; log every %d)",
        n_est,
        log_period,
    )


def _log_xgboost_fit_complete(model: XGBClassifier) -> None:
    bi = getattr(model, "best_iteration", None)
    bs = getattr(model, "best_score", None)
    if bi is not None or bs is not None:
        logger.info("XGBoost: finished best_iteration=%s best_score=%s", bi, bs)
        return
    try:
        n_rounds = model.get_booster().num_boosted_rounds()
    except Exception:
        n_rounds = None
    if n_rounds is not None:
        logger.info("XGBoost: finished (%d boosting rounds)", n_rounds)
    else:
        logger.info("XGBoost: finished")

_cached_torch_device: torch.device | None = None


def _pytorch_cuda_kernels_work() -> bool:
    """True if this PyTorch build can run kernels on the current GPU (not just detect CUDA).

    Newer GPUs (e.g. Blackwell sm_120) may be visible to the driver while prebuilt wheels
    only ship SMs up to sm_90, causing 'no kernel image is available' at runtime.
    """
    if not torch.cuda.is_available():
        return False
    try:
        torch.randperm(2, device="cuda")
        return True
    except RuntimeError as e:
        msg = str(e).lower()
        if "no kernel image" in msg or "kernel image" in msg:
            logger.warning(
                "PyTorch cannot run CUDA kernels on this GPU with the installed build (%s). "
                "Using CPU for PyTorch; install a wheel with sm_120 support (e.g. cu128 from "
                "https://pytorch.org/get-started/locally/) to use the GPU. XGBoost may still use CUDA.",
                torch.__version__,
            )
            return False
        raise


def resolve_torch_device() -> torch.device:
    """CUDA if enabled, available, and kernels work; else MPS (Apple); else CPU."""
    global _cached_torch_device
    if _cached_torch_device is not None:
        return _cached_torch_device
    if not settings.ml_use_gpu:
        _cached_torch_device = torch.device("cpu")
        return _cached_torch_device
    if _pytorch_cuda_kernels_work():
        _cached_torch_device = torch.device("cuda")
        return _cached_torch_device
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        _cached_torch_device = torch.device("mps")
        return _cached_torch_device
    logger.warning("ML_USE_GPU is enabled but no usable CUDA/MPS device for PyTorch; using CPU")
    _cached_torch_device = torch.device("cpu")
    return _cached_torch_device


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
    log_period: int | None = 10,
) -> XGBClassifier:
    """Fit XGBoost; on CUDA failure, rebuild with CPU and retry once.

    ``log_period`` controls how often boosting rounds are logged (XGBoost's analogue to
    epochs). Set to ``None`` or ``0`` to disable round logging.
    """
    _attach_round_logger(model, log_period)

    def _fit(m: XGBClassifier) -> None:
        if eval_set is not None:
            m.fit(X_train, y_train, eval_set=eval_set, verbose=verbose)
        else:
            m.fit(X_train, y_train, verbose=verbose)

    try:
        _fit(model)
        _log_xgboost_fit_complete(model)
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
        _fit(cpu_model)
        _log_xgboost_fit_complete(cpu_model)
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
