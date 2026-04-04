"""Transaction-level tabular features."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

_REQUIRED_SEND = ("sender_wallet", "sender", "from")
_REQUIRED_RECV = ("receiver_wallet", "receiver", "to")


def _resolve_col(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def compute_transaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Augment a transactions DataFrame with derived risk-style features."""
    if df is None or df.empty:
        logger.info("compute_transaction_features: empty DataFrame")
        return pd.DataFrame()

    out = df.copy()
    out["_feat_row"] = np.arange(len(out), dtype=np.int64)

    if "amount" not in out.columns:
        out["amount"] = 0.0
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)

    out["log_amount"] = np.log1p(out["amount"].clip(lower=0))

    am = out["amount"].to_numpy()
    with np.errstate(invalid="ignore"):
        round_mask = np.isfinite(am) & (am % 1 == 0) & (am % 10 == 0)
    out["is_round_amount"] = round_mask

    if "fee" in out.columns:
        fee = pd.to_numeric(out["fee"], errors="coerce")
    else:
        fee = pd.Series(0.0, index=out.index)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = fee / out["amount"].replace(0, np.nan)
    out["fee_ratio"] = ratio.fillna(0.0)
    out.loc[out["amount"] == 0, "fee_ratio"] = 0.0

    send_col = _resolve_col(out, _REQUIRED_SEND)
    recv_col = _resolve_col(out, _REQUIRED_RECV)
    if send_col is None or recv_col is None:
        logger.warning("Missing sender/receiver columns; time and pair features will be zero")
        out["time_since_prev_out"] = 0.0
        out["time_since_prev_in"] = 0.0
        out["sender_tx_count"] = 0
        out["receiver_tx_count"] = 0
        out["sender_repeat_count"] = 0
        out["burstiness_score"] = 0.0
        out["amount_deviation"] = 0.0
        return out.drop(columns=["_feat_row"], errors="ignore")

    if "timestamp" not in out.columns:
        out["timestamp"] = pd.NaT
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")

    out["sender_tx_count"] = out.groupby(send_col, sort=False)[send_col].transform("size")
    out["receiver_tx_count"] = out.groupby(recv_col, sort=False)[recv_col].transform("size")

    s_send = out.sort_values([send_col, "timestamp"], na_position="last")
    tso = s_send.groupby(send_col, sort=False)["timestamp"].diff().dt.total_seconds().fillna(0.0)
    s_send = s_send.assign(_tso=tso)
    out = out.merge(s_send[["_feat_row", "_tso"]], on="_feat_row", how="left")
    out["time_since_prev_out"] = out["_tso"].fillna(0.0)
    out = out.drop(columns=["_tso"], errors="ignore")

    s_recv = out.sort_values([recv_col, "timestamp"], na_position="last")
    tsi = s_recv.groupby(recv_col, sort=False)["timestamp"].diff().dt.total_seconds().fillna(0.0)
    s_recv = s_recv.assign(_tsi=tsi)
    out = out.merge(s_recv[["_feat_row", "_tsi"]], on="_feat_row", how="left")
    out["time_since_prev_in"] = out["_tsi"].fillna(0.0)
    out = out.drop(columns=["_tsi"], errors="ignore")

    s_pair = out.sort_values([send_col, recv_col, "timestamp"], na_position="last")
    s_pair = s_pair.assign(
        _sr=s_pair.groupby([send_col, recv_col], sort=False).cumcount() + 1,
    )
    out = out.merge(s_pair[["_feat_row", "_sr"]], on="_feat_row", how="left")
    out["sender_repeat_count"] = out["_sr"].fillna(0).astype(int)
    out = out.drop(columns=["_sr"], errors="ignore")

    def _sender_burstiness(s: pd.Series) -> float:
        s = s.dropna()
        if len(s) < 3:
            return 0.0
        delta = s.sort_values().diff().dt.total_seconds().dropna()
        if delta.empty:
            return 0.0
        std = float(delta.std(ddof=0))
        return std if np.isfinite(std) else 0.0

    s_b = out.sort_values([send_col, "timestamp"], na_position="last")
    burst = s_b.groupby(send_col, sort=False)["timestamp"].transform(_sender_burstiness)
    s_b = s_b.assign(_burst=burst)
    out = out.merge(s_b[["_feat_row", "_burst"]], on="_feat_row", how="left")
    out["burstiness_score"] = out["_burst"].fillna(0.0)
    out = out.drop(columns=["_burst"], errors="ignore")

    s_z = out.sort_values([send_col, "timestamp"], na_position="last")
    g_amt = s_z.groupby(send_col, sort=False)["amount"]
    exp_mean = g_amt.transform(lambda x: x.expanding().mean().shift(1))
    exp_std = g_amt.transform(lambda x: x.expanding().std(ddof=0).shift(1))
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (s_z["amount"] - exp_mean) / exp_std.replace(0, np.nan)
    s_z = s_z.assign(_z=z.fillna(0.0))
    out = out.merge(s_z[["_feat_row", "_z"]], on="_feat_row", how="left")
    out["amount_deviation"] = out["_z"].fillna(0.0)
    out = out.drop(columns=["_z", "_feat_row"], errors="ignore")

    return out
