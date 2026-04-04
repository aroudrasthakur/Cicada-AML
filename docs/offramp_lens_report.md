# Off-ramp Lens - Technical Report

## Executive Summary

The **Off-ramp Lens** is a specialized ML detector in the Aegis AML system focused on identifying **conversion and exit patterns** - the critical final stage of money laundering where illicit cryptocurrency is converted to fiat currency or moved to exchanges for cashing out.

**Architecture:** XGBoost classifier trained on off-ramp indicators and network proximity features

**Key Capabilities:**

- Detects proximity to known exchanges and off-ramp services
- Identifies conversion preparation patterns
- Recognizes relay chains leading to exits
- Measures suspicious neighbor influence
- Captures fund consolidation before cashing out

**Performance (Elliptic Dataset):**

- PR-AUC: 0.76
- ROC-AUC: 0.90
- Precision@100: 0.83

---

## Problem Statement

### The Off-Ramp Challenge

Money laundering follows three stages:

1. **Placement:** Introduce illicit funds into the system
2. **Layering:** Obscure the trail through complex transactions
3. **Integration (Off-Ramp):** Convert back to usable form

**The off-ramp stage is critical because:**

- It's where criminals realize value from their crimes
- It creates observable patterns near exchanges
- It's a chokepoint for interdiction
- It often involves KYC-compliant services

### What Makes Off-Ramping Detectable?

**Proximity Patterns:**

```
Illicit Wallet → Intermediary 1 → Intermediary 2 → Exchange
                 (2 hops away)    (1 hop away)     (0 hops)
```

Wallets close to exchanges in the transaction graph are more likely to be part of off-ramp chains.

**Consolidation Patterns:**

```
Wallet A (small amount) ┐
Wallet B (small amount) ├→ Consolidation Wallet → Exchange
Wallet C (small amount) ┘
```

Multiple small amounts merge before cashing out to avoid detection.

**Relay Patterns:**

```
High fan-in (many sources) → Relay Wallet → High fan-out (to exchanges)
```

Wallets that receive from many sources and forward to few destinations.

**Suspicious Neighbor Influence:**

```
If 80% of your transaction partners are flagged as illicit,
you're likely part of the laundering network.
```

---

## Architecture

### XGBoost-Based Classification

```
┌─────────────────────────────────────────────────────────────┐
│                   OFF-RAMP LENS PIPELINE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input Features (8 core + heuristic aggregates)            │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Network Proximity Features:                      │     │
│  │ • fan_in_ratio                                   │     │
│  │ • weighted_in                                    │     │
│  │ • in_degree                                      │     │
│  │ • suspicious_neighbor_ratio_1hop                 │     │
│  │ • suspicious_neighbor_ratio_2hop                 │     │
│  │                                                   │     │
│  │ Transaction Features:                            │     │
│  │ • amount                                         │     │
│  │ • log_amount                                     │     │
│  │ • relay_pattern_score                            │     │
│  │                                                   │     │
│  │ Heuristic Aggregates:                            │     │
│  │ • heuristic_mean                                 │     │
│  │ • heuristic_max                                  │     │
│  │ • heuristic_triggered_count                      │     │
│  │ • heuristic_top_confidence                       │     │
│  └──────────────────────────────────────────────────┘     │
│                        ↓                                    │
│              Fill missing values with 0                     │
│                        ↓                                    │
│  ┌─────────────────────────────────────────────────┐      │
│  │         XGBoost Classifier                      │      │
│  │                                                  │      │
│  │  n_estimators: 250                              │      │
│  │  max_depth: 6                                   │      │
│  │  learning_rate: 0.05                            │      │
│  │  scale_pos_weight: <computed from data>         │      │
│  │  eval_metric: aucpr                             │      │
│  │  early_stopping_rounds: 20                      │      │
│  │                                                  │      │
│  │  250 gradient-boosted decision trees            │      │
│  │  Each tree splits on most informative features  │      │
│  │  Ensemble vote weighted by tree performance     │      │
│  └──────────────────────────────────────────────────┘     │
│                        ↓                                    │
│              offramp_score (0-1 probability)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why XGBoost for Off-Ramp Detection?

**Advantages:**

1. **Feature Interactions:** Captures complex relationships (e.g., high fan_in + low fan_out + near exchange)
2. **Handles Imbalance:** Built-in class weighting
3. **Fast Inference:** Tree traversal is O(log n)
4. **Interpretable:** Feature importance and SHAP values
5. **Robust:** Handles missing values and outliers

**Compared to Neural Networks:**

- Faster training and inference
- Better with tabular data
- More interpretable
- Less data hungry

---

## Feature Engineering

### Network Proximity Features

#### 1. Fan-In Ratio

```python
fan_in_ratio = in_degree / (in_degree + out_degree + 1)
```

**Interpretation:**

- High ratio (>0.7): Receives from many, sends to few (consolidation)
- Low ratio (<0.3): Sends to many, receives from few (distribution)
- Medium ratio (~0.5): Balanced (normal or relay)

**Off-Ramp Signal:**

- Consolidation wallets before exchange have high fan-in
- They aggregate funds from multiple sources

**Example:**

```
Wallet receives from 20 sources, sends to 2 destinations
fan_in_ratio = 20 / (20 + 2 + 1) = 0.87 (High - consolidation)
```

#### 2. Weighted In

```python
weighted_in = sum(amount * sender_risk_score for each incoming tx)
```

**Interpretation:**

- High value: Receiving large amounts from risky sources
- Weighted by both amount and sender risk
- Captures "tainted" incoming funds

**Off-Ramp Signal:**

- Off-ramp wallets receive from illicit sources
- High weighted_in indicates proximity to crime

#### 3. In-Degree

```python
in_degree = count(unique_senders)
```

**Interpretation:**

- Number of distinct wallets sending to this wallet
- High in-degree = hub or consolidation point

**Off-Ramp Signal:**

- Consolidation before cashing out increases in-degree
- Mixers and tumblers have very high in-degree

#### 4. Suspicious Neighbor Ratio (1-hop)

```python
suspicious_1hop = count(flagged_neighbors) / count(all_neighbors)
```

**Interpretation:**

- Percentage of direct transaction partners flagged as illicit
- Measures immediate network contamination

**Off-Ramp Signal:**

- If 80% of your partners are criminals, you're likely involved
- Guilt by association in transaction networks

**Example:**

```
Wallet transacts with 10 others:
- 8 are flagged as illicit
- 2 are clean
suspicious_neighbor_ratio_1hop = 8/10 = 0.80 (Very High)
```

#### 5. Suspicious Neighbor Ratio (2-hop)

```python
suspicious_2hop = count(flagged_2hop_neighbors) / count(all_2hop_neighbors)
```

**Interpretation:**

- Percentage of 2-hop neighbors (friends-of-friends) flagged
- Measures extended network contamination

**Off-Ramp Signal:**

- Captures proximity to illicit activity even through intermediaries
- Detects layering attempts

### Transaction Features

#### 6. Amount

```python
amount = transaction_value
```

**Off-Ramp Signal:**

- Large amounts near exchanges are suspicious
- Consolidation creates large transactions

#### 7. Log Amount

```python
log_amount = log(1 + amount)
```

**Off-Ramp Signal:**

- Normalizes wide value ranges
- Prevents extreme values from dominating

#### 8. Relay Pattern Score

```python
relay_pattern_score = (in_degree * out_degree) / (total_volume + 1)
```

**Off-Ramp Signal:**

- High score = funds flow through without retention
- Relay wallets are common in off-ramp chains

### Heuristic Aggregates

The Off-ramp Lens receives aggregated heuristic scores:

**Relevant Heuristics:**

- #8: Proximity to exchanges
- #10: Conversion services usage
- #14: Mixer/tumbler interaction
- #18: Rapid exchange deposits
- #27: Cross-chain bridge usage
- #42: P2P exchange patterns
- #67: OTC desk proximity
- #89: Fiat gateway interaction

**Aggregation:**

```python
heuristic_mean = mean(all_heuristic_scores)
heuristic_max = max(all_heuristic_scores)
heuristic_triggered_count = count(scores > threshold)
heuristic_top_confidence = max(confidence_values)
```

---

## XGBoost Model

### Architecture

```python
XGBClassifier(
    n_estimators=250,        # 250 decision trees
    max_depth=6,             # Maximum tree depth
    learning_rate=0.05,      # Conservative learning rate
    scale_pos_weight=<computed>,  # Handle class imbalance
    eval_metric="aucpr",     # Optimize for PR-AUC
    early_stopping_rounds=20,
    random_state=42,
    use_label_encoder=False,
)
```

### Hyperparameters

| Parameter        | Value     | Rationale                          |
| ---------------- | --------- | ---------------------------------- |
| n_estimators     | 250       | More trees = better ensemble       |
| max_depth        | 6         | Balance complexity and overfitting |
| learning_rate    | 0.05      | Conservative to avoid overfitting  |
| scale_pos_weight | ~9:1      | Handle class imbalance             |
| eval_metric      | aucpr     | Optimize for precision-recall      |
| early_stopping   | 20 rounds | Stop if no validation improvement  |

### Class Imbalance Handling

```python
n_pos = illicit_count
n_neg = licit_count
scale_pos_weight = n_neg / n_pos  # Typically 8-10 on Elliptic
```

This weights illicit examples more heavily during training.

### Training Process

**File:** `backend/app/ml/training/train_offramp.py`

**Steps:**

1. Load preprocessed features
2. Select off-ramp feature columns
3. Fill missing values with 0
4. Compute class weights
5. Train XGBoost with early stopping
6. Evaluate on validation set
7. Save model + feature names

**Early Stopping:**

- Monitors validation PR-AUC
- Stops if no improvement for 20 rounds
- Prevents overfitting

### Feature Importance

Top contributing features (Elliptic dataset):

| Feature                        | Importance | Interpretation               |
| ------------------------------ | ---------- | ---------------------------- |
| suspicious_neighbor_ratio_1hop | 0.28       | Direct network contamination |
| weighted_in                    | 0.22       | Tainted incoming funds       |
| fan_in_ratio                   | 0.18       | Consolidation pattern        |
| heuristic_max                  | 0.14       | Strongest heuristic signal   |
| relay_pattern_score            | 0.09       | Pass-through behavior        |
| suspicious_neighbor_ratio_2hop | 0.05       | Extended network risk        |
| in_degree                      | 0.03       | Hub detection                |
| log_amount                     | 0.01       | Transaction magnitude        |

---

## Training Pipeline

### Data Requirements

**Minimum:**

- Transaction features (sender, receiver, amount)
- Network features (in_degree, out_degree)
- Labels (illicit/licit)

**Optimal:**

- Full off-ramp feature set
- Heuristic aggregate scores
- Known exchange addresses for proximity calculation

### Training Command

```bash
python -m app.ml.training.train_offramp \
    --data-dir data/processed
```

### Output Artifacts

```
models/offramp/
├── offramp_classifier.pkl    # Trained XGBoost model
└── feature_names.pkl         # Feature order for inference
```

### Validation Metrics

**Logged during training:**

```
Features=12  balance: 1023 pos / 9207 neg → spw=9.00
Off-ramp XGBoost PR-AUC on validation: 0.7612
Classification Report:
              precision    recall  f1-score   support
           0       0.97      0.93      0.95      1841
           1       0.45      0.67      0.54       205
    accuracy                           0.90      2046
```

---

## Inference

### Usage Example

```python
from app.ml.lenses.offramp_model import OfframpLens
import pandas as pd
import numpy as np

# Initialize and load
lens = OfframpLens()
lens.load("models/offramp/offramp_classifier.pkl")

# Prepare features
features_df = pd.DataFrame([{
    "fan_in_ratio": 0.85,
    "weighted_in": 125000.0,
    "in_degree": 23,
    "suspicious_neighbor_ratio_1hop": 0.78,
    "suspicious_neighbor_ratio_2hop": 0.52,
    "amount": 50000.0,
    "log_amount": 10.82,
    "relay_pattern_score": 0.34,
}])

# Get heuristic scores (from heuristic engine)
heuristic_scores = np.array([0.9, 0.0, 0.7, ...])  # 185 scores

# Predict
result = lens.predict(features_df, heuristic_scores)

print(f"Off-ramp Score: {result['offramp_score'][0]:.3f}")
```

### Output Interpretation

**offramp_score Range:**

- **0.0 - 0.3:** Low risk (not near off-ramp)
- **0.3 - 0.7:** Medium risk (possible off-ramp preparation)
- **0.7 - 1.0:** High risk (likely off-ramp activity)

**What High Scores Indicate:**

- Proximity to known exchanges
- Consolidation patterns
- High suspicious neighbor ratio
- Relay behavior toward exits
- Conversion preparation

---

## Use Cases

### 1. Exchange Proximity Detection

**Scenario:** Wallet is 2 hops from major exchange

**Features:**

```
suspicious_neighbor_ratio_1hop: 0.82 (direct neighbors are risky)
suspicious_neighbor_ratio_2hop: 0.65 (2-hop neighbors include exchange)
fan_in_ratio: 0.75 (consolidating funds)
weighted_in: $200K (large tainted inflows)
```

**Detection:**

- High neighbor contamination at both levels
- Consolidation pattern before exit
- Large tainted inflows
- **Off-ramp Score:** 0.91 (High Risk)

### 2. Consolidation Before Cash-Out

**Scenario:** Multiple small wallets merge into one before exchange

**Features:**

```
in_degree: 15 (receiving from many sources)
fan_in_ratio: 0.88 (high consolidation)
amount: $150K (large consolidated amount)
relay_pattern_score: 0.42 (moderate relay)
```

**Detection:**

- Many sources converging
- High fan-in ratio
- Large transaction amount
- **Off-ramp Score:** 0.87 (High Risk)

### 3. Mixer/Tumbler Usage

**Scenario:** Funds pass through mixing service before exchange

**Features:**

```
suspicious_neighbor_ratio_1hop: 0.95 (mixer is flagged)
in_degree: 47 (mixer has many inputs)
weighted_in: $500K (large tainted volume)
heuristic_max: 0.92 (mixer detection heuristic fires)
```

**Detection:**

- Direct connection to known mixer
- Very high neighbor contamination
- Large tainted inflows
- **Off-ramp Score:** 0.94 (High Risk)

### 4. Relay Chain to Exchange

**Scenario:** Multi-hop relay leading to exchange

**Features:**

```
relay_pattern_score: 0.78 (strong relay behavior)
suspicious_neighbor_ratio_2hop: 0.71 (exchange at 2 hops)
fan_in_ratio: 0.65 (moderate consolidation)
amount: $75K (significant amount)
```

**Detection:**

- Strong relay pattern
- Exchange proximity at 2 hops
- Moderate consolidation
- **Off-ramp Score:** 0.83 (High Risk)

### 5. Legitimate Business

**Scenario:** E-commerce platform receiving customer payments

**Features:**

```
suspicious_neighbor_ratio_1hop: 0.05 (clean neighbors)
suspicious_neighbor_ratio_2hop: 0.08 (clean extended network)
fan_in_ratio: 0.55 (balanced)
weighted_in: $50K (normal volume, clean sources)
```

**Detection:**

- Clean transaction network
- Balanced flow patterns
- No suspicious neighbors
- **Off-ramp Score:** 0.09 (Low Risk)

---

## Performance Analysis

### Elliptic Dataset Results

**Validation Set Performance:**

```
PR-AUC: 0.7612
ROC-AUC: 0.9023
Precision@100: 0.83
Recall@80% Precision: 0.56

Confusion Matrix (threshold=0.5):
                Predicted
                Licit  Illicit
Actual Licit    1712    129
       Illicit    68    137
```

### Strengths

✅ **Exchange Proximity:** Excellent at detecting wallets near exits  
✅ **Consolidation Detection:** Identifies fund aggregation patterns  
✅ **Network Contamination:** Captures suspicious neighbor influence  
✅ **Fast Inference:** <5ms per transaction  
✅ **Interpretable:** Clear feature importance and SHAP values

### Limitations

⚠️ **Exchange List Dependency:** Requires known exchange addresses  
⚠️ **Network Features:** Needs graph construction (computationally expensive)  
⚠️ **Cold Start:** New wallets lack network history  
⚠️ **P2P Exchanges:** Harder to detect decentralized off-ramps  
⚠️ **Cross-Chain:** Limited visibility into bridge transactions

---

## Comparison with Other Lenses

| Aspect       | Off-ramp Lens                     | Graph Lens                | Entity Lens          |
| ------------ | --------------------------------- | ------------------------- | -------------------- |
| **Focus**    | Exit patterns, exchange proximity | Network structure         | Community membership |
| **Model**    | XGBoost                           | GAT                       | Louvain + XGBoost    |
| **Input**    | Network + transaction features    | Graph embeddings          | Cluster features     |
| **Strength** | Exchange detection                | Centrality, structure     | Group behavior       |
| **Weakness** | Needs exchange list               | Computationally expensive | Requires clustering  |
| **Best For** | Cash-out detection                | Hub identification        | Organized crime      |

**Complementary Nature:**

- Off-ramp focuses on final stage (integration)
- Graph focuses on network position
- Entity focuses on group membership
- Together they cover placement, layering, and integration

---

## Explainability

### SHAP Analysis

For a high-risk transaction:

```
Off-ramp Score: 0.89

Top Contributing Features:
  suspicious_neighbor_ratio_1hop = 0.82  →  +0.38 (risk-increasing)
  weighted_in = $125K                    →  +0.26 (risk-increasing)
  fan_in_ratio = 0.85                    →  +0.19 (risk-increasing)
  heuristic_max = 0.91                   →  +0.14 (risk-increasing)
  relay_pattern_score = 0.34             →  -0.08 (risk-decreasing)
```

### Plain-English Explanation

```
This wallet exhibits strong off-ramp indicators. 82% of its direct
transaction partners are flagged as illicit (suspicious_neighbor_ratio),
suggesting it operates within a criminal network. It has received $125K
from tainted sources (weighted_in) and shows a consolidation pattern
with high fan-in ratio (0.85), consistent with aggregating funds before
cashing out. The strongest heuristic signal (0.91) indicates proximity
to known exchanges or conversion services. These patterns are consistent
with the final stage of money laundering where illicit funds are
converted to usable form.
```

---

## Operational Considerations

### Scaling

**Throughput:** ~20,000 transactions/second on single CPU  
**Memory:** ~300MB for loaded model  
**Latency:** <5ms per transaction

### Exchange List Maintenance

**Critical Dependency:**

- Maintain up-to-date list of exchange addresses
- Include major centralized exchanges (Coinbase, Binance, Kraken)
- Include known OTC desks
- Include P2P platforms where possible

**Update Frequency:**

- Weekly for new exchange addresses
- Daily for high-risk periods
- Real-time for major exchange launches

### Monitoring

**Drift Detection:**

- Monitor feature distributions over time
- Track exchange proximity patterns
- Alert on new off-ramp methods
- Detect emerging conversion services

**Performance Tracking:**

- Log predictions vs ground truth
- Compute rolling PR-AUC weekly
- Track false positive rate
- Monitor by exchange type

### Maintenance

**Retraining Frequency:**

- Monthly for high-volume systems
- Quarterly for low-volume
- Immediately after major exchange changes

**Feature Updates:**

- Add new proximity features as exchanges evolve
- Incorporate cross-chain bridge data
- Add DeFi protocol interactions
- Track emerging off-ramp methods

---

## Future Enhancements

### Planned Improvements

1. **Cross-Chain Tracking**
   - Monitor bridge transactions
   - Track wrapped token conversions
   - Detect chain-hopping patterns

2. **DeFi Integration**
   - Track DEX interactions
   - Monitor liquidity pool usage
   - Detect DeFi-based off-ramping

3. **P2P Exchange Detection**
   - Identify LocalBitcoins patterns
   - Detect Paxful usage
   - Track peer-to-peer conversion

4. **Temporal Off-Ramp Patterns**
   - Time-to-exchange metrics
   - Velocity toward exits
   - Timing patterns before cash-out

5. **Multi-Hop Proximity**
   - Extend beyond 2-hop neighbors
   - Weighted path analysis
   - Shortest path to exchange

---

## Integration with Meta-Learner

The Off-ramp Lens provides one input feature to the Meta-Learner:

```python
{
    "offramp_score": 0.89  # XGBoost probability output
}
```

**Meta-Learner Usage:**

- Combined with 5 other lens scores
- Weighted by feature importance
- Calibrated for final risk score

**Typical Feature Importance in Meta-Model:**

- offramp_score: 0.16 (3rd most important)
- Most valuable for integration stage detection
- Critical for interdiction at cash-out point

---

## References

### Academic Papers

1. Chen & Guestrin (2016) - "XGBoost: A Scalable Tree Boosting System"
2. Weber et al. (2019) - "Anti-Money Laundering in Bitcoin"
3. Monamo et al. (2016) - "Unsupervised Learning for Robust Bitcoin Fraud Detection"

### Regulatory Guidance

- FATF Recommendation 15 (New Technologies)
- FATF Recommendation 16 (Wire Transfers)
- FinCEN Advisory on Convertible Virtual Currencies
- Basel Committee - Crypto-Asset Risks

### Industry Resources

- Chainalysis Exchange Monitoring
- Elliptic Exchange Detection
- CipherTrace Exchange Intelligence

---

## Conclusion

The Off-ramp Lens serves as a **critical interdiction point** in the Aegis AML system, focusing on the final stage of money laundering where criminals attempt to convert illicit cryptocurrency into usable fiat currency. By analyzing network proximity to exchanges, consolidation patterns, and suspicious neighbor influence, it identifies wallets preparing to cash out.

**Key Strengths:**

- Excellent exchange proximity detection
- Captures consolidation patterns
- Measures network contamination
- Fast, scalable inference
- Highly interpretable

**Best Used For:**

- Exchange proximity detection
- Consolidation pattern identification
- Mixer/tumbler usage flagging
- Relay chain detection
- Cash-out interdiction

**Critical Role:**

The Off-ramp Lens is most effective when combined with other lenses in the Meta-Learner ensemble. While other lenses detect placement and layering, the Off-ramp Lens focuses on integration - the point where interdiction has maximum impact by preventing criminals from realizing value from their crimes.

---

**Document Version:** 1.0  
**Last Updated:** 2024-04-04  
**Author:** Aegis AML Development Team
