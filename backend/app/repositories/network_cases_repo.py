from __future__ import annotations

from app.supabase_client import get_supabase


def _page_range(page: int, limit: int) -> tuple[int, int]:
    p = max(1, page)
    lim = max(1, limit)
    start = (p - 1) * lim
    end = start + lim - 1
    return start, end


def insert_network_case(case_data: dict, wallet_addresses: list[str]) -> dict:
    try:
        sb = get_supabase()
        case_resp = sb.table("network_cases").insert(case_data).select().execute()
        rows = case_resp.data or []
        if not rows:
            return {}
        case_row = rows[0] if isinstance(rows, list) else rows
        if not isinstance(case_row, dict):
            return {}
        case_id = case_row.get("id")
        if case_id is None:
            return {}
        links = [
            {"case_id": case_id, "wallet_address": addr} for addr in wallet_addresses
        ]
        if links:
            sb.table("network_case_wallets").insert(links).execute()
        out = dict(case_row)
        out["wallet_addresses"] = list(wallet_addresses)
        return out
    except Exception:
        return {}


def get_network_cases(page: int = 1, limit: int = 50) -> tuple[list[dict], int]:
    start, end = _page_range(page, limit)
    try:
        sb = get_supabase()
        resp = (
            sb.table("network_cases")
            .select("*", count="exact")
            .order("created_at", desc=True)
            .range(start, end)
            .execute()
        )
        return list(resp.data or []), int(resp.count or 0)
    except Exception:
        return [], 0


def get_network_case(case_id: str) -> dict | None:
    try:
        sb = get_supabase()
        resp = (
            sb.table("network_cases")
            .select("*, network_case_wallets(wallet_address)")
            .eq("id", case_id)
            .maybe_single()
            .execute()
        )
        if resp is None:
            return None
        row = resp.data
        if not isinstance(row, dict):
            return None
        nested = row.pop("network_case_wallets", None) or []
        addresses = []
        for w in nested:
            if isinstance(w, dict) and w.get("wallet_address"):
                addresses.append(w["wallet_address"])
        row["wallet_addresses"] = addresses
        return row
    except Exception:
        return None
