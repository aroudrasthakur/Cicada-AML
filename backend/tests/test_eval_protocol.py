"""Tests for evaluation metrics: classification, ranking, and calibration."""
import pytest
import numpy as np

from app.utils.metrics import (
    compute_classification_metrics,
    precision_at_k,
    recall_at_k,
    compute_ranking_metrics,
    expected_calibration_error,
)


class TestClassificationMetrics:
    def test_perfect_predictions(self):
        y_true = np.array([0, 0, 1, 1, 1])
        y_pred = np.array([0, 0, 1, 1, 1])
        y_prob = np.array([0.1, 0.2, 0.9, 0.8, 0.95])

        metrics = compute_classification_metrics(y_true, y_pred, y_prob)
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1"] == 1.0
        assert metrics["balanced_accuracy"] == 1.0

    def test_known_values(self):
        y_true = np.array([1, 0, 1, 0, 1, 0])
        y_pred = np.array([1, 0, 0, 0, 1, 1])
        y_prob = np.array([0.9, 0.2, 0.4, 0.3, 0.8, 0.6])

        metrics = compute_classification_metrics(y_true, y_pred, y_prob)
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "roc_auc" in metrics
        assert "confusion_matrix" in metrics
        assert isinstance(metrics["confusion_matrix"], list)

    def test_all_same_class(self):
        y_true = np.array([0, 0, 0, 0])
        y_pred = np.array([0, 0, 0, 0])
        y_prob = np.array([0.1, 0.2, 0.1, 0.3])

        metrics = compute_classification_metrics(y_true, y_pred, y_prob)
        assert metrics["roc_auc"] == 0.0
        assert metrics["pr_auc"] == 0.0


class TestRankingMetrics:
    def test_precision_at_k(self):
        y_true = np.array([1, 0, 1, 0, 1, 0, 0, 0, 0, 0])
        y_prob = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])

        p_at_3 = precision_at_k(y_true, y_prob, 3)
        assert p_at_3 == pytest.approx(2 / 3, abs=1e-6)

    def test_recall_at_k(self):
        y_true = np.array([1, 0, 1, 0, 1, 0, 0, 0, 0, 0])
        y_prob = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])

        r_at_3 = recall_at_k(y_true, y_prob, 3)
        assert r_at_3 == pytest.approx(2 / 3, abs=1e-6)

    def test_compute_ranking_metrics_keys(self):
        y_true = np.array([1, 0, 1, 0, 1])
        y_prob = np.array([0.9, 0.3, 0.8, 0.2, 0.7])

        metrics = compute_ranking_metrics(y_true, y_prob, k_values=[2, 3])
        assert "precision_at_2" in metrics
        assert "recall_at_2" in metrics
        assert "precision_at_3" in metrics
        assert "recall_at_3" in metrics

    def test_edge_cases(self):
        assert precision_at_k(np.array([]), np.array([]), 5) == 0.0
        assert recall_at_k(np.array([0, 0]), np.array([0.5, 0.3]), 1) == 0.0
        assert precision_at_k(np.array([1]), np.array([0.9]), 0) == 0.0


class TestCalibrationError:
    def test_perfectly_calibrated(self):
        np.random.seed(42)
        n = 10000
        y_prob = np.random.rand(n)
        y_true = (np.random.rand(n) < y_prob).astype(int)

        ece = expected_calibration_error(y_true, y_prob, n_bins=10)
        assert ece < 0.05, f"ECE={ece} is too high for well-calibrated predictions"

    def test_worst_case_calibration(self):
        y_true = np.array([0, 0, 0, 0, 0])
        y_prob = np.array([0.99, 0.99, 0.99, 0.99, 0.99])
        ece = expected_calibration_error(y_true, y_prob)
        assert ece > 0.9, f"ECE={ece} should be close to 1.0 for miscalibrated predictions"

    def test_empty_input(self):
        ece = expected_calibration_error(np.array([]), np.array([]))
        assert ece == 0.0
