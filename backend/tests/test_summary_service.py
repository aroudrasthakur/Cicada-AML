"""Tests for report summary fallback (no OpenAI)."""
from app.services.summary_service import _generate_fallback_summary


def test_fallback_summary_includes_key_metrics():
    content = {
        "summary": {
            "total_transactions": 100,
            "suspicious_transactions": 5,
            "cluster_count": 2,
            "threshold_used": 0.014,
        },
        "score_distribution": {"high": 1, "medium": 2, "low": 97},
        "top_suspicious_transactions": [
            {
                "transaction_id": "TXN001",
                "meta_score": 0.9,
                "risk_level": "high",
                "typology": "PeelChain",
            },
        ],
        "cluster_findings": [
            {"label": "Cluster A", "typology": "fan-out", "wallet_count": 4},
        ],
    }
    text = _generate_fallback_summary(content)
    assert "100" in text
    assert "5" in text
    assert "TXN001" in text
    assert "•" in text
    wc = len(text.split())
    assert wc <= 110, f"expected ≤~100 words, got {wc}"
