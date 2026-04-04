"""Heuristic engine endpoints."""
from fastapi import APIRouter, HTTPException
from app.ml.heuristics.registry import get_registry_entries
from app.repositories.heuristics_repo import get_heuristic_result, get_heuristic_stats

router = APIRouter()


@router.get("/registry")
async def heuristic_registry():
    return get_registry_entries()


@router.get("/stats")
async def heuristic_stats():
    return get_heuristic_stats()


@router.get("/{transaction_id}")
async def heuristic_results(transaction_id: str):
    result = get_heuristic_result(transaction_id)
    if not result:
        raise HTTPException(404, "No heuristic results for this transaction")
    return result
