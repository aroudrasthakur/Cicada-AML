from typing import Any
import networkx as nx


def k_hop_subgraph(G: nx.DiGraph, node: Any, k: int) -> nx.DiGraph:
    nodes = {node}
    frontier = {node}
    for _ in range(k):
        next_frontier = set()
        for n in frontier:
            next_frontier.update(G.successors(n))
            next_frontier.update(G.predecessors(n))
        nodes.update(next_frontier)
        frontier = next_frontier - nodes | next_frontier
    return G.subgraph(nodes).copy()


def detect_cycles(G: nx.DiGraph, max_length: int = 10) -> list[list]:
    cycles = []
    try:
        for cycle in nx.simple_cycles(G, length_bound=max_length):
            cycles.append(cycle)
            if len(cycles) > 1000:
                break
    except Exception:
        pass
    return cycles


def fan_out_degree(G: nx.DiGraph, node: Any) -> int:
    return G.out_degree(node)


def fan_in_degree(G: nx.DiGraph, node: Any) -> int:
    return G.in_degree(node)


def graph_to_cytoscape(G: nx.DiGraph) -> dict:
    elements = []
    for node, data in G.nodes(data=True):
        elements.append({"data": {"id": str(node), **{k: _serialize(v) for k, v in data.items()}}})
    for u, v, data in G.edges(data=True):
        elements.append({
            "data": {"source": str(u), "target": str(v), **{k: _serialize(v_) for k, v_ in data.items()}}
        })
    return {"elements": elements}


def _serialize(val: Any) -> Any:
    if isinstance(val, (int, float, str, bool)):
        return val
    return str(val)
