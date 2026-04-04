"""Transaction endpoints."""
from fastapi import APIRouter, Query, HTTPException
from app.repositories.transactions_repo import get_transactions, get_transaction_by_id
from app.repositories.scores_repo import get_transaction_score
from app.schemas.transaction import TransactionListResponse, TransactionResponse

router = APIRouter()


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    label: str | None = None,
    min_risk: float | None = Query(None, ge=0, le=1),
):
    data, total = get_transactions(page=page, limit=limit, label=label, min_risk=min_risk)
    return TransactionListResponse(
        items=[TransactionResponse(**d) for d in data],
        total=total, page=page, limit=limit,
    )


@router.get("/{transaction_id}")
async def get_transaction(transaction_id: str):
    tx = get_transaction_by_id(transaction_id)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    score = get_transaction_score(transaction_id)
    return {**tx, "score": score}


@router.post("/score")
async def score_all():
    from app.ml.infer_pipeline import InferencePipeline
    from app.repositories.transactions_repo import get_transactions
    data, total = get_transactions(page=1, limit=10000)
    if not data:
        return {"scored": 0}
    pipeline = InferencePipeline()
    pipeline.load_models()
    # Graph will be built automatically inside score_transactions
    results = pipeline.score_transactions(data, graph=None)
    return {"scored": len(results)}
