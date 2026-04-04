"""Graph Lens: GAT-based structural anomaly detection."""
import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv
from torch_geometric.data import Data
from pathlib import Path
import networkx as nx
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GATClassifier(torch.nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int = 64, heads: int = 8, num_classes: int = 2):
        super().__init__()
        self.conv1 = GATConv(in_channels, hidden_channels, heads=heads, dropout=0.3)
        self.conv2 = GATConv(hidden_channels * heads, num_classes, heads=1, concat=False, dropout=0.3)

    def forward(self, x, edge_index):
        x = F.elu(self.conv1(x, edge_index))
        x = F.dropout(x, p=0.3, training=self.training)
        x = self.conv2(x, edge_index)
        return x

    def get_embeddings(self, x, edge_index):
        x = F.elu(self.conv1(x, edge_index))
        return x


class GraphLens:
    LENS_TAGS = ["graph"]

    def __init__(self):
        self.model = None
        self.node_mapping = {}

    def nx_to_pyg(self, G: nx.DiGraph, node_features: dict, heuristic_scores: dict = None) -> Data:
        """Convert NetworkX graph to PyTorch Geometric Data object."""
        nodes = sorted(G.nodes())
        node_map = {n: i for i, n in enumerate(nodes)}
        self.node_mapping = node_map
        feat_list = []
        for n in nodes:
            nf = node_features.get(n, {})
            feat_vec = [
                nf.get("in_degree", 0), nf.get("out_degree", 0),
                nf.get("weighted_in", 0), nf.get("weighted_out", 0),
                nf.get("betweenness_centrality", 0), nf.get("pagerank", 0),
                nf.get("clustering_coefficient", 0),
            ]
            if heuristic_scores and n in heuristic_scores:
                feat_vec.extend(heuristic_scores[n])
            feat_list.append(feat_vec)
        x = torch.FloatTensor(feat_list)
        edges = [(node_map[u], node_map[v]) for u, v in G.edges() if u in node_map and v in node_map]
        if edges:
            edge_index = torch.LongTensor(edges).t().contiguous()
        else:
            edge_index = torch.zeros((2, 0), dtype=torch.long)
        return Data(x=x, edge_index=edge_index)

    def predict(self, G: nx.DiGraph, node_features: dict, heuristic_scores: dict = None) -> dict:
        """Run GAT inference."""
        data = self.nx_to_pyg(G, node_features, heuristic_scores)
        if self.model is None:
            return {"graph_score": np.zeros(data.x.shape[0]), "embeddings": data.x.numpy()}
        self.model.eval()
        with torch.no_grad():
            logits = self.model(data.x, data.edge_index)
            probs = F.softmax(logits, dim=1)
            embeddings = self.model.get_embeddings(data.x, data.edge_index)
        inv_map = {v: k for k, v in self.node_mapping.items()}
        return {
            "graph_score": probs[:, 1].numpy(),
            "embeddings": embeddings.numpy(),
            "node_mapping": inv_map,
        }

    def load(self, model_path: str):
        p = Path(model_path)
        if p.exists():
            state = torch.load(p, map_location="cpu", weights_only=True)
            in_channels = state.get("in_channels", 7)
            self.model = GATClassifier(in_channels)
            self.model.load_state_dict(state["model_state_dict"])
            logger.info(f"Loaded GAT model from {p}")
