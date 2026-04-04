from __future__ import annotations

from app.supabase_client import get_supabase


def _page_range(page: int, limit: int) -> tuple[int, int]:
    p = max(1, page)
    lim = max(1, limit)
    start = (p - 1) * lim
    end = start + lim - 1
    return start, end


def upsert_wallets(records: list[dict]) -> list[dict]:
    if not records:
        return []
    try:
        sb = get_supabase()
        resp = sb.table("wallets").upsert(records, on_conflict="wallet_address").execute()
        return list(resp.data or [])
    except Exception:
        return []


def get_wallets(page: int = 1, limit: int = 50) -> tuple[list[dict], int]:
    start, end = _page_range(page, limit)
    try:
        sb = get_supabase()
        resp = (
            sb.table("wallets")
            .select("*", count="exact")
            .order("last_seen", desc=True)
            .range(start, end)
            .execute()
        )
        return list(resp.data or []), int(resp.count or 0)
    except Exception:
        return [], 0


def get_wallet_by_address(address: str) -> dict | None:
    try:
        sb = get_supabase()
        resp = (
            sb.table("wallets")
            .select("*")
            .eq("wallet_address", address)
            .maybe_single()
            .execute()
        )
        if resp is None:
            return None
        return resp.data
    except Exception:
        return None
