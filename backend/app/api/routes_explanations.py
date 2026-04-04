"""Explanation endpoints."""
from fastapi import APIRouter, HTTPException
from app.services.explanation_service import explain_transaction, explain_case

router = APIRouter()


@router.get("/{transaction_id}")
async def get_transaction_explanation(transaction_id: str):
    try:
        explanation = explain_transaction(transaction_id)
        if not explanation:
            raise HTTPException(404, "No explanation available")
        return explanation
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/case/{case_id}")
async def get_case_explanation(case_id: str):
    try:
        explanation = explain_case(case_id)
        if not explanation:
            raise HTTPException(404, "No explanation available")
        return explanation
    except Exception as e:
        raise HTTPException(500, str(e))
