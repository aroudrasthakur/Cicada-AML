"""Network case endpoints."""
from fastapi import APIRouter, Query, HTTPException
from app.repositories.network_cases_repo import get_network_cases, get_network_case

router = APIRouter()


@router.get("")
async def list_networks(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=500)):
    data, total = get_network_cases(page=page, limit=limit)
    return {"items": data, "total": total, "page": page, "limit": limit}


@router.get("/{case_id}")
async def get_case(case_id: str):
    case = get_network_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.get("/{case_id}/graph")
async def get_case_graph(case_id: str):
    case = get_network_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    wallets = case.get("wallet_addresses", [])
    from app.services.graph_service import build_wallet_graph
    from app.repositories.transactions_repo import get_transactions
    from app.utils.graph_utils import graph_to_cytoscape
    data, _ = get_transactions(page=1, limit=10000)
    G = build_wallet_graph(data)
    sub_nodes = set()
    for w in wallets:
        if G.has_node(w):
            sub_nodes.add(w)
            sub_nodes.update(G.successors(w))
            sub_nodes.update(G.predecessors(w))
    sub = G.subgraph(sub_nodes)
    return graph_to_cytoscape(sub)


@router.post("/detect")
async def detect_networks():
    from app.services.investigation_service import detect_suspicious_networks
    cases = detect_suspicious_networks()
    return {"cases_created": len(cases)}
