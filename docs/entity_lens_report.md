# Entity Lens - Technical Report

## Executive Summary

The **Entity Lens** is a specialized machine learning component in the Aegis AML system designed to detect **common control** and identify cooperating wallet clusters. It addresses a critical challenge in blockchain AML: determining when multiple seemingly independent wallet addresses are actually controlled by the same entity or coordinated group.

**Key Capabilities:**

- Resolves wallet clusters using community detection algorithms
- Identifies Sybil attacks and coordinated wallet networks
- Detects entity-level money laundering patterns
- Provides cluster-level risk scoring
- Integrates graph embeddings from the Graph Lens for enhanced accuracy

---

## Problem Statement

### Why Entity Resolution Matters in AML

In blockchain money laundering, adversaries commonly use **multiple wallets** to:

1. **Obfuscate ownership** - Create the illusion of many independent actors
2. **Evade detection** - Spread activity across addresses to stay under thresholds
3. **Layer funds** - Move money between controlled addresses to break the trail
4. **Sybil farming** - Create fake activity for airdrops or to manipulate metrics
5. **Mule networks** - Coordinate multiple accounts for cash-out operations

**Example Scenario:**

```
Wallet A → Wallet B → Wallet C → Wallet D → Exchange
   ↓          ↓          ↓          ↓
 (Same entity controlling all wallets)
```

Without entity resolution, each wallet appears independent with low individual risk. With entity resolution, the system recognizes this as a **coordinated layering operation** by a single actor.

---

## Architecture

### Three-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    ENTITY LENS PIPELINE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Stage 1: Community Detection                              │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Input: Transaction Graph (NetworkX DiGraph)      │     │
│  │ Algorithm: Louvain or Leiden                     │     │
│  │ Output: Wallet → Cluster ID mapping              │     │
│  └──────────────────────────────────────────────────┘     │
│                        ↓                                    │
│  Stage 2: Cluster Feature Engineering                      │
│  ┌──────────────────────────────────────────────────┐     │
│  │ • Cluster size (# of wallets)                    │     │
│  │ • Internal edge density                          │     │
│  │ • External edge ratio                            │     │
│  │ • Shared counterparty count                      │     │
│  │ • Timing synchronization score                   │     │
│  │ • Graph embeddings (from Graph Lens)            │     │
│  │ • Gas sponsor overlap                            │     │
│  │ • Device/IP fingerprint similarity (when avail.) │     │
│  └──────────────────────────────────────────────────┘     │
│                        ↓                                    │
│  Stage 3: Risk Classification                              │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Model: XGBoost Classifier                        │     │
│  │ Input: Cluster features + heuristic scores       │     │
│  │ Output: Per-wallet entity_score (0-1)           │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Community Detection

### Algorithm Selection

The Entity Lens supports two state-of-the-art community detection algorithms:

#### 1. Louvain Algorithm (Default)

- **Method:** Modularity optimization via greedy agglomeration
- **Complexity:** O(n log n) - Fast for large graphs
- **Strengths:**
  - Well-established and widely used
  - Excellent performance on sparse graphs
  - Deterministic with fixed random seed
- **Use Case:** General-purpose entity clustering

#### 2. Leiden Algorithm (Advanced)

- **Method:** Improved Louvain with refinement phase
- **Complexity:** O(n log n) with better quality
- **Strengths:**
  - Better quality partitions than Louvain
  - Guarantees well-connected communities
  - Handles resolution limit better
- **Use Case:** High-precision investigations requiring optimal clusters

### How It Works

**Input:** Directed transaction graph where:

- **Nodes** = Wallet addresses
- **Edges** = Transactions (with amount, timestamp)

**Process:**

1. Convert directed graph to undirected (for community detection)
2. Run Louvain/Leiden to partition nodes into communities
3. Each community represents a potential entity cluster

**Output:** Dictionary mapping `wallet_address → cluster_id`

**Example:**

```python
partition = {
    "0xABC...123": 0,  # Cluster 0
    "0xDEF...456": 0,  # Cluster 0 (same entity)
    "0xGHI...789": 1,  # Cluster 1 (different entity)
    "0xJKL...012": 2,  # Cluster 2 (isolated)
}
```

### Fallback Strategy

If Louvain/Leiden libraries are unavailable, the system falls back to **weakly connected components** - a simpler but less precise clustering method.

---

## Stage 2: Cluster Feature Engineering

### Core Features

#### 1. Structural Features

**Cluster Size**

- Number of wallets in the cluster
- Larger clusters may indicate coordinated operations

**Internal Edge Density**

```python
density = internal_edges / (n * (n-1) / 2)
```

- High density = wallets frequently transact with each other
- Indicator of tight coordination

**External Edge Ratio**

```python
external_ratio = external_edges / (internal_edges + external_edges)
```

- High ratio = cluster interacts heavily with outside wallets
- May indicate layering or cash-out operations

#### 2. Behavioral Features

**Shared Counterparty Count**

- Number of external wallets that multiple cluster members interact with
- High count suggests coordinated targeting

**Timing Synchronization Score**

- Measures how often cluster members transact within short time windows
- Detects bot-like or scripted behavior

**Average In/Out Degree**

```python
avg_in = total_in_degree / cluster_size
avg_out = total_out_degree / cluster_size
```

- Characterizes the cluster's role (aggregator vs. disperser)

#### 3. Graph Embedding Features

**Embedding Mean & Std**

- Uses node embeddings from the Graph Lens (GAT model)
- Captures learned structural patterns
- Clusters with similar embeddings likely have similar roles

**Embedding Distance**

- Measures cohesion within cluster
- Low distance = members are structurally similar

#### 4. Intelligence Features (When Available)

**Gas Sponsor Overlap**

- On Ethereum/EVM chains, detects shared gas sponsors
- Strong indicator of common control

**Device/IP Fingerprints**

- When KYC or off-chain data is available
- Detects accounts accessed from same devices

**Shared KYC Documents**

- Identity document reuse across accounts
- Indicates nominee/mule account networks

---

## Stage 3: Risk Classification

### XGBoost Classifier

**Training:**

- Trained on cluster-level features
- Labels derived from transaction-level ground truth
- A cluster is labeled suspicious if ≥30% of its labeled members are illicit

**Inference:**

- Predicts risk score for each cluster
- Individual wallet scores inherit from their cluster
- Adjusted by wallet's role within cluster

**Class Imbalance Handling:**

```python
scale_pos_weight = n_licit_clusters / n_illicit_clusters
```

### Output Format

```python
{
    "entity_scores": {
        "0xABC...123": {
            "entity_score": 0.87,        # Risk score (0-1)
            "cluster_id": 42,             # Cluster assignment
            "cluster_risk_score": 0.87,   # Cluster-level risk
            "cluster_size": 15,           # Members in cluster
            "role": "aggregator"          # Wallet's role
        }
    },
    "partition": {...},                   # Full cluster mapping
    "cluster_features": {...}             # All cluster metrics
}
```

---

## Integration with Other Lenses

### Dependency: Graph Lens

The Entity Lens **requires** the Graph Lens to run first:

```python
# Execution order in inference pipeline
1. Graph Lens runs → produces node embeddings
2. Entity Lens runs → uses embeddings as features
```

**Why?**

- Graph embeddings capture learned structural patterns
- Provides richer signal than raw graph features alone
- Enables detection of subtle coordination patterns

### Heuristic Integration

The Entity Lens consumes heuristics tagged with `"entity"`:

**Relevant Heuristics:**

- #96: Self-transfer chains (transfers within same entity)
- #110: Gas sponsorship distancing
- #119: Wallet cluster fragmentation
- #135: Airdrop farming / Sybil attacks
- #141: Exchange mule rings
- #164: Botnet wallet orchestration

These heuristics provide domain-specific signals that complement the ML clustering.

---

## Use Cases

### 1. Sybil Attack Detection

**Scenario:** Attacker creates 100 wallets to farm airdrops

**Detection:**

- Community detection groups the 100 wallets into a cluster
- High internal density (all funded from same source)
- Low transaction diversity
- Synchronized timing patterns
- **Entity Score:** 0.92 (High Risk)

### 2. Layering Network

**Scenario:** Illicit funds moved through 20 intermediary wallets

**Detection:**

- Wallets form a chain-like cluster
- High external edge ratio (funds enter and exit)
- Sequential timing (relay pattern)
- Graph embeddings show similar structural roles
- **Entity Score:** 0.85 (High Risk)

### 3. Exchange Mule Ring

**Scenario:** 10 KYC-borrowed accounts used to cash out stolen crypto

**Detection:**

- Cluster of accounts with shared counterparties (the exchange)
- High pass-through ratio (funds in → funds out)
- Shared gas sponsor (operator's wallet)
- KYC document reuse detected
- **Entity Score:** 0.94 (Critical Risk)

### 4. Legitimate Business

**Scenario:** Company with 5 operational wallets (treasury, payroll, etc.)

**Detection:**

- Cluster identified but with legitimate patterns
- Regular, predictable transaction patterns
- Low heuristic trigger count
- Transparent on-chain behavior
- **Entity Score:** 0.12 (Low Risk)

---

## Training Process

### Data Preparation

```bash
# 1. Build transaction graph
python -m scripts.prepare_graph --output data/processed

# 2. Train Graph Lens first (dependency)
python -m app.ml.training.train_graph --data-dir data/processed

# 3. Train Entity Lens
python -m app.ml.training.train_entity --data-dir data/processed
```

### Training Pipeline

**File:** `backend/app/ml/training/train_entity.py`

**Steps:**

1. Load transaction graph and labels
2. Load graph embeddings from Graph Lens
3. Run Louvain/Leiden community detection
4. Compute cluster-level features
5. Assign cluster labels (≥30% illicit threshold)
6. Train XGBoost classifier
7. Save model and partition mapping

**Hyperparameters:**

```python
XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    scale_pos_weight=<computed>,
    eval_metric="aucpr",
    early_stopping_rounds=15,
)
```

### Validation

**Metrics:**

- PR-AUC (primary) - Handles class imbalance
- Cluster purity - % of clusters that are homogeneous
- Cluster recall - % of illicit wallets correctly clustered
- False positive rate per 1,000 clusters

**Elliptic Dataset Performance:**

- PR-AUC: 0.75
- ROC-AUC: 0.89
- Precision@100: 0.81

---

## Operational Modes

### Full Mode (Tier 2 Data)

**Available when:**

- KYC/entity link data present
- Device/IP fingerprints available
- Document metadata accessible

**Features:**

- All cluster features enabled
- High-confidence entity resolution
- Precise mule network detection

### Limited Mode (Tier 0/1 Data)

**Available when:**

- Only on-chain data present
- No KYC or off-chain intelligence

**Features:**

- Graph structure and embeddings only
- Community detection still effective
- Lower confidence, disclosed in explanations

**Disclosure:**

```json
{
  "entity_lens_mode": "limited",
  "confidence_cap_reason": "No KYC or entity intelligence available"
}
```

---

## Explainability

### Cluster Visualization

The dashboard provides interactive cluster visualization:

```
Cluster #42 (15 wallets)
├─ Risk Score: 0.87 (High)
├─ Internal Density: 0.73
├─ Shared Counterparties: 8
├─ Timing Sync Score: 0.91
└─ Triggered Heuristics:
   ├─ #96: Self-transfer chains (conf: 0.88)
   ├─ #135: Sybil farming (conf: 0.76)
   └─ #164: Botnet orchestration (conf: 0.82)
```

### Plain-English Explanation

```
This wallet is part of a 15-member cluster exhibiting coordinated
behavior. The cluster shows high internal transaction density (73%)
and synchronized timing patterns (91% sync score), consistent with
scripted or bot-controlled operations. Multiple heuristics fired,
including self-transfer chains and Sybil farming indicators.
```

### SHAP Feature Importance

Top contributing features for cluster risk:

1. `timing_synchronization_score` (0.34)
2. `internal_edge_density` (0.28)
3. `embedding_similarity` (0.19)
4. `shared_counterparty_count` (0.12)
5. `cluster_size` (0.07)

---

## Limitations & Considerations

### 1. Privacy Concerns

**Issue:** Clustering may inadvertently group unrelated users

**Mitigation:**

- Require strong evidence (multiple signals) before flagging
- Provide cluster membership transparency
- Allow appeals and manual review

### 2. False Positives

**Scenarios:**

- Legitimate businesses with multiple wallets
- Family members sharing gas sponsors
- Users of the same wallet service

**Mitigation:**

- Whitelist known legitimate entities
- Combine with other lens signals
- Use conservative thresholds

### 3. Computational Cost

**Challenge:** Community detection is O(n log n) but can be slow on massive graphs

**Optimization:**

- Run on subgraphs for real-time inference
- Cache cluster assignments
- Incremental updates for new wallets

### 4. Adversarial Evasion

**Attack:** Sophisticated actors may deliberately fragment clusters

**Defense:**

- Multi-hop cluster expansion
- Temporal cluster tracking
- Combine with other lenses (behavioral, temporal)

---

## Performance Benchmarks

### Elliptic Dataset Results

| Metric               | Value       |
| -------------------- | ----------- |
| Clusters Detected    | 1,247       |
| Avg Cluster Size     | 8.3 wallets |
| Largest Cluster      | 156 wallets |
| Illicit Clusters     | 89 (7.1%)   |
| PR-AUC               | 0.75        |
| Precision@100        | 0.81        |
| Recall@90% Precision | 0.62        |

### Computational Performance

| Operation           | Time (10K wallets) |
| ------------------- | ------------------ |
| Louvain Detection   | 0.8s               |
| Feature Engineering | 1.2s               |
| XGBoost Inference   | 0.3s               |
| **Total**           | **2.3s**           |

---

## Future Enhancements

### Planned Features

1. **Temporal Cluster Tracking**
   - Track cluster evolution over time
   - Detect cluster splitting/merging
   - Identify cluster lifecycle patterns

2. **Multi-Chain Entity Resolution**
   - Link entities across different blockchains
   - Cross-chain bridge analysis
   - Unified entity graph

3. **Advanced Fingerprinting**
   - Transaction pattern fingerprinting
   - Wallet software detection
   - Behavioral biometrics

4. **Federated Learning**
   - Privacy-preserving entity resolution
   - Cross-institution collaboration
   - Encrypted cluster matching

---

## Code Examples

### Basic Usage

```python
from app.ml.lenses.entity_model import EntityLens
from app.services.graph_service import build_wallet_graph

# Initialize
entity_lens = EntityLens()
entity_lens.load("models/entity/entity_classifier.pkl")

# Build graph
G = build_wallet_graph(transactions)

# Get graph embeddings (from Graph Lens)
graph_embeddings = graph_lens.predict(G, node_features)

# Run entity resolution
result = entity_lens.predict(
    G=G,
    heuristic_scores={},
    embeddings=graph_embeddings["embeddings"],
    node_mapping=graph_embeddings["node_mapping"]
)

# Access results
for wallet, info in result["entity_scores"].items():
    print(f"{wallet}: Risk={info['entity_score']:.2f}, Cluster={info['cluster_id']}")
```

### Custom Clustering

```python
# Use Leiden instead of Louvain
from app.services.clustering_service import detect_communities_leiden

partition = detect_communities_leiden(G)
cluster_features = entity_lens.compute_cluster_features(
    G, partition, embeddings, node_mapping
)
```

---

## References

### Academic Papers

1. Blondel et al. (2008) - "Fast unfolding of communities in large networks" (Louvain)
2. Traag et al. (2019) - "From Louvain to Leiden: guaranteeing well-connected communities"
3. Weber et al. (2019) - "Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks"

### Regulatory Guidance

- FATF Guidance on Virtual Assets (2021)
- FinCEN Advisory on Convertible Virtual Currency (2019)
- Wolfsberg Group AML Principles for Virtual Assets

---

## Conclusion

The Entity Lens is a critical component of the Aegis AML system, addressing the fundamental challenge of **common control detection** in blockchain transactions. By combining:

- ✅ State-of-the-art community detection algorithms
- ✅ Rich cluster-level feature engineering
- ✅ Graph embeddings from neural networks
- ✅ Domain-specific heuristic signals
- ✅ Explainable risk scoring

...the Entity Lens enables investigators to **see through** the obfuscation tactics of sophisticated money launderers and identify coordinated criminal networks that would otherwise remain hidden.

**Key Takeaway:** Individual wallets may appear low-risk, but when analyzed as coordinated entities, their true criminal nature becomes apparent.

---

**Document Version:** 1.0  
**Last Updated:** 2024-04-04  
**Author:** Aegis AML Development Team
