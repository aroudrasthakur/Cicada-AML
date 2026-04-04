"""Network case assembly: detect suspicious clusters and create cases."""
import networkx as nx
from app.repositories.transactions_repo import get_transactions
from app.repositories.scores_repo import get_transaction_score
from app.repositories.network_cases_repo import insert_network_case
from app.services.graph_service import build_wallet_graph, compute_node_features
from app.utils.graph_utils import detect_cycles
from app.utils.logger import get_logger

logger = get_logger(__name__)


def detect_suspicious_networks(risk_threshold: float = 0.75, min_cluster_size: int = 3) -> list[dict]:
    """Scan scored transactions, find high-risk clusters, create cases."""
    data, total = get_transactions(page=1, limit=50000)
    if not data:
        return []
    
    G = build_wallet_graph(data)
    node_features = compute_node_features(G)
    
    # Identify high-risk wallets
    high_risk_wallets = set()
    for tx in data:
        score = get_transaction_score(tx.get("transaction_id", ""))
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
        
        case_data = {
            "case_name": f"Suspicious Network ({len(risky_in_component)} wallets)",
            "typology": _classify_typology(sub),
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


def _classify_typology(G: nx.DiGraph) -> str:
    """Classify the dominant typology of a subgraph."""
    max_out = max((G.out_degree(n) for n in G.nodes()), default=0)
    max_in = max((G.in_degree(n) for n in G.nodes()), default=0)
    cycles = detect_cycles(G, max_length=6)
    
    if max_out > 10:
        return "fan-out dispersal"
    if max_in > 10:
        return "fan-in aggregation"
    if len(cycles) > 3:
        return "circular layering"
    avg_degree = sum(G.degree(n) for n in G.nodes()) / max(len(G.nodes()), 1)
    if avg_degree < 2.5:
        return "peel chain"
    return "layering"
