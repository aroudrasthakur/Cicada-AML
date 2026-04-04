import numpy as np
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
    balanced_accuracy_score,
    matthews_corrcoef,
    brier_score_loss,
)


def compute_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0,
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0,
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def precision_at_k(y_true: np.ndarray, y_prob: np.ndarray, k: int) -> float:
    if k <= 0 or len(y_true) == 0:
        return 0.0
    top_k_idx = np.argsort(y_prob)[::-1][:k]
    return float(np.mean(y_true[top_k_idx]))


def recall_at_k(y_true: np.ndarray, y_prob: np.ndarray, k: int) -> float:
    total_pos = np.sum(y_true)
    if total_pos == 0 or k <= 0:
        return 0.0
    top_k_idx = np.argsort(y_prob)[::-1][:k]
    return float(np.sum(y_true[top_k_idx]) / total_pos)


def compute_ranking_metrics(y_true: np.ndarray, y_prob: np.ndarray, k_values: list[int] | None = None) -> dict:
    if k_values is None:
        k_values = [50, 100, 200, 500]
    result = {}
    for k in k_values:
        result[f"precision_at_{k}"] = precision_at_k(y_true, y_prob, k)
        result[f"recall_at_{k}"] = recall_at_k(y_true, y_prob, k)
    return result


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        ece += mask.sum() * abs(bin_acc - bin_conf)
    return float(ece / len(y_true)) if len(y_true) > 0 else 0.0
