"""Tests for drift detection and alerting."""
import numpy as np
import pytest


def test_psi_computation():
    """Verify PSI (Population Stability Index) computation."""
    reference = np.array([0.1, 0.2, 0.3, 0.2, 0.1, 0.1])
    current = np.array([0.15, 0.15, 0.25, 0.25, 0.1, 0.1])
    psi = _compute_psi(reference, current)
    assert psi >= 0
    assert psi < 0.25  # Should show minimal drift


def test_psi_identical_distributions():
    """Identical distributions should have PSI = 0."""
    dist = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
    psi = _compute_psi(dist, dist)
    assert psi == pytest.approx(0.0, abs=1e-10)


def test_psi_significant_drift():
    """Large distribution shift should produce high PSI."""
    reference = np.array([0.4, 0.3, 0.2, 0.1])
    current = np.array([0.1, 0.1, 0.3, 0.5])
    psi = _compute_psi(reference, current)
    assert psi > 0.1  # Meaningful drift


def test_feature_drift_detection():
    """Verify feature drift detection flags shifted features."""
    np.random.seed(42)
    reference_features = {
        "amount": np.random.normal(100, 20, 1000),
        "fan_out": np.random.normal(5, 2, 1000),
        "velocity": np.random.normal(50, 10, 1000),
    }
    current_features = {
        "amount": np.random.normal(100, 20, 1000),
        "fan_out": np.random.normal(10, 2, 1000),  # shifted
        "velocity": np.random.normal(50, 10, 1000),
    }
    drifted = _detect_feature_drift(reference_features, current_features)
    assert "fan_out" in drifted
    assert "amount" not in drifted


def test_label_drift_detection():
    """Verify label drift detection identifies class distribution shifts."""
    ref_labels = np.array([0] * 980 + [1] * 20)  # 2% positive
    cur_labels = np.array([0] * 900 + [1] * 100)  # 10% positive
    has_drift = _detect_label_drift(ref_labels, cur_labels, threshold=0.03)
    assert has_drift


def test_no_label_drift():
    """Stable label distributions should not trigger drift."""
    ref_labels = np.array([0] * 980 + [1] * 20)
    cur_labels = np.array([0] * 975 + [1] * 25)
    has_drift = _detect_label_drift(ref_labels, cur_labels, threshold=0.03)
    assert not has_drift


def _compute_psi(reference: np.ndarray, current: np.ndarray, epsilon: float = 1e-6) -> float:
    """Population Stability Index."""
    ref = np.clip(reference, epsilon, None)
    cur = np.clip(current, epsilon, None)
    ref = ref / ref.sum()
    cur = cur / cur.sum()
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def _detect_feature_drift(
    reference: dict[str, np.ndarray],
    current: dict[str, np.ndarray],
    n_bins: int = 10,
    psi_threshold: float = 0.1,
) -> list[str]:
    """Return list of features with significant drift."""
    drifted = []
    for feat_name in reference:
        ref_hist, bin_edges = np.histogram(reference[feat_name], bins=n_bins, density=True)
        cur_hist, _ = np.histogram(current[feat_name], bins=bin_edges, density=True)
        ref_hist = ref_hist + 1e-6
        cur_hist = cur_hist + 1e-6
        ref_prop = ref_hist / ref_hist.sum()
        cur_prop = cur_hist / cur_hist.sum()
        psi = _compute_psi(ref_prop, cur_prop)
        if psi > psi_threshold:
            drifted.append(feat_name)
    return drifted


def _detect_label_drift(
    ref_labels: np.ndarray,
    cur_labels: np.ndarray,
    threshold: float = 0.05,
) -> bool:
    """Check if positive class rate has shifted beyond threshold."""
    ref_rate = ref_labels.mean()
    cur_rate = cur_labels.mean()
    return abs(cur_rate - ref_rate) > threshold
