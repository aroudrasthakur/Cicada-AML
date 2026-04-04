from __future__ import annotations

from app.supabase_client import get_supabase


def _page_range(page: int, limit: int) -> tuple[int, int]:
    p = max(1, page)
    lim = max(1, limit)
    start = (p - 1) * lim
    end = start + lim - 1
    return start, end


def insert_transactions(records: list[dict]) -> list[dict]:
    if not records:
        return []
    try:
        sb = get_supabase()
        resp = sb.table("transactions").upsert(
            records, on_conflict="transaction_id"
        ).execute()
        return list(resp.data or [])
    except Exception:
        return []


def get_transactions(
    page: int = 1,
    limit: int = 50,
    label: str | None = None,
    min_risk: float | None = None,
) -> tuple[list[dict], int]:
    start, end = _page_range(page, limit)
    try:
        sb = get_supabase()
        if min_risk is not None:
            q = (
                sb.table("transactions")
                .select(
                    "*, transaction_scores!inner(meta_score)",
                    count="exact",
                )
                .gte("transaction_scores.meta_score", min_risk)
            )
        else:
            q = sb.table("transactions").select("*", count="exact")
        if label is not None:
            q = q.eq("label", label)
        q = q.order("timestamp", desc=True).range(start, end)
        resp = q.execute()
        return list(resp.data or []), int(resp.count or 0)
    except Exception:
        return [], 0


def get_transaction_by_id(transaction_id: str) -> dict | None:
    try:
        sb = get_supabase()
        resp = (
            sb.table("transactions")
            .select("*")
            .eq("transaction_id", transaction_id)
            .maybe_single()
            .execute()
        )
        if resp is None:
            return None
        return resp.data
    except Exception:
        return None
