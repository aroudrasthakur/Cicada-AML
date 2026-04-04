"""Network case assembly: detect suspicious clusters and create cases."""
import networkx as nx
from app.repositories.transactions_repo import get_transactions
from app.repositories.scores_repo import get_transaction_scores_batch
from app.repositories.network_cases_repo import insert_network_case
from app.services.graph_service import build_wallet_graph, compute_node_features
from app.ml.typology_taxonomy import infer_cluster_typology
from app.utils.logger import get_logger

logger = get_logger(__name__)


def detect_suspicious_networks(risk_threshold: float = 0.75, min_cluster_size: int = 3) -> list[dict]:
    """Scan scored transactions, find high-risk clusters, create cases."""
    data, total = get_transactions(page=1, limit=50000)
    if not data:
        return []
    
    G = build_wallet_graph(data)
    node_features = compute_node_features(G)
    
    tx_ids = [tx.get("transaction_id", "") for tx in data if tx.get("transaction_id")]
    scores_map = get_transaction_scores_batch(tx_ids)

    high_risk_wallets = set()
    for tx in data:
        tx_id = tx.get("transaction_id", "")
        score = scores_map.get(tx_id)
        if score and (score.get("meta_score") or 0) >= risk_threshold:
            high_risk_wallets.add(tx.get("sender_wallet"))
            high_risk_wallets.add(tx.get("receiver_wallet"))
    
    if not high_risk_wallets:
        logger.info("No high-risk wallets found")
        return []
    
    # Expand to connected components
    undirected = G.to_undirected()
    cases = []
    visited = set()
    
    for wallet in high_risk_wallets:
        if wallet in visited or not undirected.has_node(wallet):
            continue
        component = nx.node_connected_component(undirected, wallet)
        risky_in_component = component & high_risk_wallets
        
        if len(risky_in_component) < min_cluster_size:
            continue
        
        visited.update(component)
        
        # Compute case metrics
        sub = G.subgraph(component)
        total_amount = sum(d.get("amount", 0) for _, _, d in sub.edges(data=True))
        timestamps = [d.get("timestamp") for _, _, d in sub.edges(data=True) if d.get("timestamp")]
        
        cluster_txs = [
            t for t in data
            if t.get("sender_wallet") in component
            or t.get("receiver_wallet") in component
        ]
        cluster_scores = [
            scores_map.get(t.get("transaction_id", ""), {})
            for t in cluster_txs
            if scores_map.get(t.get("transaction_id", ""))
        ]
        typology = infer_cluster_typology(
            sub, transactions=cluster_txs, scoring_rows=cluster_scores,
        )
        logger.info(
            "investigation_typology_trace | nodes=%d edges=%d typology=%s",
            sub.number_of_nodes(), sub.number_of_edges(), typology,
        )

        case_data = {
            "case_name": f"Suspicious Network ({len(risky_in_component)} wallets)",
            "typology": typology,
            "risk_score": len(risky_in_component) / len(component),
            "total_amount": total_amount,
            "start_time": min(timestamps) if timestamps else None,
            "end_time": max(timestamps) if timestamps else None,
            "explanation": f"Cluster of {len(component)} wallets with {len(risky_in_component)} high-risk nodes. Total flow: {total_amount:.2f}",
        }
        
        result = insert_network_case(case_data, list(risky_in_component))
        if result:
            cases.append(result)
    
    logger.info(f"Created {len(cases)} network cases")
    return cases


