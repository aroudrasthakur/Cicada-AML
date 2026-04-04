"""Wallet endpoints."""
from fastapi import APIRouter, Query, HTTPException
from app.repositories.wallets_repo import get_wallets, get_wallet_by_address
from app.repositories.scores_repo import get_wallet_score

router = APIRouter()


@router.get("")
async def list_wallets(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=500)):
    data, total = get_wallets(page=page, limit=limit)
    return {"items": data, "total": total, "page": page, "limit": limit}


@router.get("/{address}")
async def get_wallet(address: str):
    wallet = get_wallet_by_address(address)
    if not wallet:
        raise HTTPException(404, "Wallet not found")
    score = get_wallet_score(address)
    return {**wallet, "score": score}


@router.get("/{address}/graph")
async def get_wallet_graph(address: str, hops: int = Query(3, ge=1, le=5)):
    from app.services.graph_service import build_wallet_graph, get_wallet_graph_json
    from app.repositories.transactions_repo import get_transactions
    data, _ = get_transactions(page=1, limit=10000)
    if not data:
        return {"elements": []}
    G = build_wallet_graph(data)
    return get_wallet_graph_json(G, address, hops)
