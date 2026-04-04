from __future__ import annotations

from app.supabase_client import get_supabase


def upsert_transaction_scores(records: list[dict]) -> list[dict]:
    if not records:
        return []
    try:
        sb = get_supabase()
        resp = sb.table("transaction_scores").upsert(
            records, on_conflict="transaction_id"
        ).execute()
        return list(resp.data or [])
    except Exception:
        return []


def get_transaction_score(transaction_id: str) -> dict | None:
    try:
        sb = get_supabase()
        resp = (
            sb.table("transaction_scores")
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


def upsert_wallet_scores(records: list[dict]) -> list[dict]:
    if not records:
        return []
    try:
        sb = get_supabase()
        resp = sb.table("wallet_scores").upsert(
            records, on_conflict="wallet_address"
        ).execute()
        return list(resp.data or [])
    except Exception:
        return []


def get_wallet_score(wallet_address: str) -> dict | None:
    try:
        sb = get_supabase()
        resp = (
            sb.table("wallet_scores")
            .select("*")
            .eq("wallet_address", wallet_address)
            .maybe_single()
            .execute()
        )
        if resp is None:
            return None
        return resp.data
    except Exception:
        return None
