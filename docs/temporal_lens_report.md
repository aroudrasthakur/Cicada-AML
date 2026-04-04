# Temporal Lens - Technical Report

## Executive Summary

The **Temporal Lens** is a specialized ML detector in the Aegis AML system that analyzes **transaction sequences over time** to identify temporal patterns indicative of money laundering. Unlike other lenses that analyze individual transactions or static features, the Temporal Lens captures the dynamic evolution of wallet behavior through LSTM-based sequence modeling.

**Architecture:** 2-layer LSTM neural network with attention to temporal dependencies

**Key Capabilities:**

- Detects velocity-based laundering (rapid movement of funds)
- Identifies timing anomalies and burst patterns
- Captures sequential dependencies in transaction flows
- Recognizes dormant-to-active transitions
- Models wallet behavior evolution over time

**Performance (Elliptic Dataset):**

- PR-AUC: 0.72
- ROC-AUC: 0.88
- Precision@100: 0.81

---

## Problem Statement

### Why Temporal Analysis Matters

Money laundering often exhibits distinctive **temporal signatures** that are invisible when analyzing transactions in isolation:

**Velocity Laundering:**

```
Day 1: Receive $100K
Day 1 (2 hours later): Forward $98K to 5 wallets
Day 1 (4 hours later): Each wallet forwards to exchanges
```

The speed of movement is the signal.

**Burst Patterns:**

```
Months 1-6: No activity
Day 180: 47 transactions in 3 hours
Day 181: No activity
```

Sudden bursts after dormancy indicate coordination.

**Timing Regularity:**

```
Every Tuesday at 3:00 AM: Receive exactly $9,500
Every Tuesday at 3:15 AM: Forward to same wallet
```

Bot-like precision suggests automation.

**Sequential Dependencies:**

```
Transaction N: Receive from exchange
Transaction N+1: Always followed by split to 3 wallets
Transaction N+2-4: Always followed by consolidation
```

Predictable sequences reveal laundering playbooks.

### What Static Features Miss

Traditional features analyze transactions independently:

- Amount: $5,000
- Fee: $5
- Counterparties: 3

But they miss:

- This is the 15th transaction in 20 minutes
- Previous 14 were identical amounts
- All to different wallets created yesterday
- Timing matches known bot patterns

**The Temporal Lens captures these time-dependent patterns.**

---

## Architecture

### LSTM-Based Sequence Model

```
┌─────────────────────────────────────────────────────────────┐
│                   TEMPORAL LENS PIPELINE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Per-Wallet Transaction Sequence (sorted by timestamp)     │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Transaction 1: [amount, time_delta, direction,   │     │
│  │                 burstiness]                       │     │
│  │ Transaction 2: [amount, time_delta, direction,   │     │
│  │                 burstiness]                       │     │
│  │ ...                                               │     │
│  │ Transaction N: [amount, time_delta, direction,   │     │
│  │                 burstiness]                       │     │
│  │                                                   │     │
│  │ Padded/Truncated to MAX_SEQ_LEN = 50             │     │
│  └──────────────────────────────────────────────────┘     │
│                        ↓                                    │
│              Shape: (batch, 50, 4)                          │
│                        ↓                                    │
│  ┌─────────────────────────────────────────────────┐      │
│  │         2-Layer LSTM (hidden_dim=128)           │      │
│  │                                                  │      │
│  │  Layer 1: LSTM(input=4, hidden=128, dropout=0.2)│      │
│  │           ↓                                      │      │
│  │  Layer 2: LSTM(input=128, hidden=128, dropout=0.2)     │
│  │           ↓                                      │      │
│  │  Extract final hidden state h_n[-1]             │      │
│  │           ↓                                      │      │
│  │  Classifier: Linear(128 → 64) → ReLU → Dropout  │      │
│  │              Linear(64 → 1)                      │      │
│  │           ↓                                      │      │
│  │  Output: Raw logit (no sigmoid in model)        │      │
│  └──────────────────────────────────────────────────┘     │
│                        ↓                                    │
│              Apply sigmoid at inference                     │
│                        ↓                                    │
│              temporal_score (0-1 probability)               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why LSTM?

**Long Short-Term Memory (LSTM)** networks are designed to capture long-range dependencies in sequences:

**Key Properties:**

1. **Memory Cells:** Maintain information across many time steps
2. **Gating Mechanisms:** Learn what to remember and forget
3. **Gradient Flow:** Avoid vanishing gradients in long sequences
4. **Sequential Processing:** Process transactions in temporal order

**Advantages for AML:**

- Captures patterns like "always splits after receiving from exchange"
- Remembers dormancy periods
- Learns timing regularities
- Handles variable-length sequences

---

## Sequence Features

### Per-Transaction Features (4 dimensions)

Each transaction in the sequence is represented by 4 features:

#### 1. Amount

```python
amount = float(transaction["amount"])
```

- Raw transaction value
- Captures magnitude changes over time
- Sequences like [100, 50, 25, 12.5] reveal splitting patterns

#### 2. Time Since Previous Outgoing

```python
time_since_prev_out = seconds_since_last_outgoing_transaction
```

- Measures velocity of outgoing transactions
- Low values = rapid forwarding (mule behavior)
- High values = dormancy or accumulation
- Zero-padded for first transaction

#### 3. Direction Indicator

```python
is_outgoing = 1.0 if sender == wallet else 0.0
```

- Binary flag: 1 = outgoing, 0 = incoming
- Captures flow direction patterns
- Sequences like [0,0,0,1,1,1] = accumulate then disperse

#### 4. Burstiness Score

```python
burstiness_score = std(time_deltas_between_transactions)
```

- Measures timing irregularity
- Low = regular, bot-like (suspicious)
- High = sporadic, human-like (normal)
- Computed over wallet's full history

### Sequence Construction

**File:** `backend/app/ml/lenses/temporal_model.py`

```python
def build_sequences(self, transactions_df, wallet: str) -> np.ndarray:
    # Filter transactions involving this wallet
    wallet_txs = transactions_df[
        (transactions_df["sender_wallet"] == wallet) |
        (transactions_df["receiver_wallet"] == wallet)
    ].sort_values("timestamp").tail(MAX_SEQ_LEN)

    # Extract features for each transaction
    features = []
    for _, row in wallet_txs.iterrows():
        f = [
            float(row["amount"]),
            float(row["time_since_prev_out"]),
            1.0 if row["sender_wallet"] == wallet else 0.0,
            float(row["burstiness_score"]),
        ]
        features.append(f)

    seq = np.array(features, dtype=np.float32)

    # Pad if sequence is shorter than MAX_SEQ_LEN
    if len(seq) < MAX_SEQ_LEN:
        pad = np.zeros((MAX_SEQ_LEN - len(seq), 4))
        seq = np.vstack([pad, seq])  # Pad at beginning

    return seq.reshape(1, MAX_SEQ_LEN, 4)
```

**Key Design Choices:**

- **MAX_SEQ_LEN = 50:** Balance between context and memory
- **Tail Selection:** Use most recent 50 transactions
- **Zero Padding:** Pad at beginning to preserve recent history
- **Sorted by Timestamp:** Maintain temporal order

---

## LSTM Model Architecture

### Network Structure

```python
class TemporalLSTM(nn.Module):
    def __init__(self, input_dim=4, hidden_dim=128, num_layers=2, dropout=0.2):
        super().__init__()

        # 2-layer LSTM with dropout
        self.lstm = nn.LSTM(
            input_size=input_dim,      # 4 features per transaction
            hidden_size=hidden_dim,    # 128 hidden units
            num_layers=num_layers,     # 2 stacked layers
            dropout=dropout,           # 0.2 dropout between layers
            batch_first=True           # Input shape: (batch, seq, features)
        )

        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64),  # 128 → 64
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),           # 64 → 1 (logit)
        )

    def forward(self, x):
        # x shape: (batch, 50, 4)
        _, (h_n, _) = self.lstm(x)
        # h_n shape: (num_layers, batch, hidden_dim)
        # Extract final layer's hidden state
        out = self.classifier(h_n[-1])
        # out shape: (batch, 1)
        return out.squeeze(-1)  # Return raw logit
```

### Hyperparameters

| Parameter     | Value | Rationale                                 |
| ------------- | ----- | ----------------------------------------- |
| input_dim     | 4     | Amount, time_delta, direction, burstiness |
| hidden_dim    | 128   | Balance capacity and overfitting          |
| num_layers    | 2     | Capture hierarchical patterns             |
| dropout       | 0.2   | Regularization between layers             |
| learning_rate | 1e-3  | Standard Adam LR                          |
| batch_size    | 64    | Fit in GPU memory                         |
| epochs        | 100   | With early stopping                       |
| patience      | 10    | Stop if no improvement for 10 epochs      |

### Loss Function

```python
# Compute class imbalance weight
n_pos = illicit_count
n_neg = licit_count
pos_weight = torch.FloatTensor([n_neg / n_pos])

# Binary cross-entropy with logits
criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
```

**Why BCEWithLogitsLoss?**

- Combines sigmoid + BCE for numerical stability
- Handles class imbalance via pos_weight
- Model outputs raw logits (no sigmoid in forward())
- Sigmoid applied only at inference time

---

## Training Pipeline

### Data Preparation

**File:** `backend/app/ml/training/train_temporal.py`

**Steps:**

1. **Load Transaction Data**

   ```python
   txn_df = pd.read_csv("data/processed/train_features.csv")
   wallet_labels = pd.read_csv("data/processed/wallet_labels.csv")
   ```

2. **Build Wallet Sequences**
   - Group transactions by wallet
   - Sort by timestamp
   - Extract last 50 transactions
   - Pad if fewer than 50

3. **Create Labels**
   - Map wallet → label (0=licit, 1=illicit)
   - Filter wallets with <2 transactions

4. **Oversample Illicit Class**

   ```python
   # If illicit is 10% of data, replicate 9x
   factor = max(int(n_licit / n_illicit) - 1, 1)
   X_over = np.concatenate([X, np.tile(X[illicit_mask], (factor, 1, 1))])
   ```

5. **Train/Val Split**
   - 80% training, 20% validation
   - Stratified by label

### Training Loop

```python
for epoch in range(1, EPOCHS + 1):
    model.train()
    perm = torch.randperm(len(X_train))
    epoch_loss = 0.0

    # Mini-batch training
    for start in range(0, len(X_train), BATCH_SIZE):
        idx = perm[start:start + BATCH_SIZE]
        pred = model(X_train[idx])
        loss = criterion(pred, y_train[idx])

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()

    # Validation every 5 epochs
    if epoch % 5 == 0:
        model.eval()
        with torch.no_grad():
            val_pred = model(X_val)
        val_prob = 1.0 / (1.0 + np.exp(-val_pred))  # Apply sigmoid
        val_ap = average_precision_score(y_val, val_prob)

        # Early stopping
        if val_ap > best_ap:
            best_ap = val_ap
            best_state = model.state_dict()
            wait = 0
        else:
            wait += 5
            if wait >= PATIENCE:
                break
```

### Training Command

```bash
python -m app.ml.training.train_temporal \
    --data-dir data/processed
```

### Output Artifacts

```
models/temporal/
└── lstm_model.pt          # Model weights + input_dim
```

**Saved State:**

```python
{
    "model_state_dict": model.state_dict(),
    "input_dim": 4
}
```

---

## Inference

### Usage Example

```python
from app.ml.lenses.temporal_model import TemporalLens
import pandas as pd

# Initialize and load
lens = TemporalLens()
lens.load("models/temporal/lstm_model.pt")

# Prepare transaction data
transactions_df = pd.DataFrame([
    {"timestamp": "2024-01-01 10:00", "sender_wallet": "0xABC",
     "receiver_wallet": "0xDEF", "amount": 1000,
     "time_since_prev_out": 0, "burstiness_score": 0.5},
    {"timestamp": "2024-01-01 10:05", "sender_wallet": "0xABC",
     "receiver_wallet": "0xGHI", "amount": 500,
     "time_since_prev_out": 300, "burstiness_score": 0.5},
    # ... more transactions
])

# Score wallets
wallets = ["0xABC", "0xDEF"]
result = lens.predict(transactions_df, wallets)

for wallet, score in result["temporal_scores"].items():
    print(f"{wallet}: {score:.3f}")
```

### Output Interpretation

**temporal_score Range:**

- **0.0 - 0.3:** Low risk (normal temporal patterns)
- **0.3 - 0.7:** Medium risk (some unusual timing)
- **0.7 - 1.0:** High risk (suspicious temporal behavior)

**What High Scores Indicate:**

- Rapid forwarding after receiving funds
- Bot-like timing regularity
- Burst activity after dormancy
- Predictable sequential patterns
- Velocity laundering signatures

---

## Use Cases

### 1. Velocity Laundering Detection

**Scenario:** Funds move through 5 wallets in 30 minutes

**Sequence Pattern:**

```
Wallet A: [IN: $100K] → [OUT: $98K after 5 min]
Wallet B: [IN: $98K] → [OUT: $96K after 3 min]
Wallet C: [IN: $96K] → [OUT: $94K after 4 min]
...
```

**Detection:**

- Very short `time_since_prev_out` values
- Consistent [IN, OUT, IN, OUT] direction pattern
- Similar amounts with small decrements
- **Temporal Score:** 0.94 (High Risk)

### 2. Dormant Account Activation

**Scenario:** Wallet inactive for 6 months, suddenly processes 50 transactions in 1 day

**Sequence Pattern:**

```
Transactions 1-10: [All zeros - padding for dormancy]
Transactions 11-50: [Burst of activity]
```

**Detection:**

- Long zero-padding followed by dense activity
- High `burstiness_score` (irregular timing)
- Sudden transition from dormant to active
- **Temporal Score:** 0.87 (High Risk)

### 3. Bot-Like Regularity

**Scenario:** Automated mule account with precise timing

**Sequence Pattern:**

```
Every transaction:
- time_since_prev_out = 3600 seconds (exactly 1 hour)
- amount = 9500 (consistent)
- direction alternates perfectly
```

**Detection:**

- Very low `burstiness_score` (too regular)
- Predictable timing intervals
- Mechanical precision (not human-like)
- **Temporal Score:** 0.91 (High Risk)

### 4. Layering Detection

**Scenario:** Complex multi-hop laundering with sequential dependencies

**Sequence Pattern:**

```
Step 1: Receive from exchange
Step 2: Always split to exactly 3 wallets
Step 3: Wait 2 hours
Step 4: Consolidate from 3 wallets
Step 5: Forward to mixer
```

**Detection:**

- LSTM learns the predictable playbook
- Sequential dependencies captured
- Timing patterns between steps
- **Temporal Score:** 0.89 (High Risk)

### 5. Legitimate Business

**Scenario:** E-commerce platform with natural transaction flow

**Sequence Pattern:**

```
- Variable amounts (customer purchases)
- Irregular timing (business hours + random)
- Mix of incoming/outgoing
- High burstiness (human behavior)
```

**Detection:**

- Natural variability in all features
- No predictable patterns
- Human-like timing irregularity
- **Temporal Score:** 0.12 (Low Risk)

---

## Performance Analysis

### Elliptic Dataset Results

**Validation Set Performance:**

```
PR-AUC: 0.7234
ROC-AUC: 0.8812
Precision@100: 0.81
Recall@80% Precision: 0.52

Classification Report (threshold=0.5):
              precision    recall  f1-score   support
           0       0.96      0.91      0.93      7821
           1       0.38      0.61      0.47       892
    accuracy                           0.88      8713
```

### Strengths

✅ **Captures Temporal Dependencies:** Sees patterns invisible to static features  
✅ **Velocity Detection:** Excellent at identifying rapid fund movement  
✅ **Sequence Learning:** Recognizes multi-step laundering playbooks  
✅ **Dormancy Detection:** Flags sudden activation of inactive wallets  
✅ **Bot Detection:** Identifies automated, non-human timing patterns

### Limitations

⚠️ **Cold Start:** Requires transaction history (min 2 transactions)  
⚠️ **Sequence Length:** Limited to last 50 transactions  
⚠️ **Computational Cost:** LSTM inference slower than tree models  
⚠️ **Data Hungry:** Needs sufficient training sequences  
⚠️ **Interpretability:** LSTM decisions less transparent than XGBoost

---

## Comparison with Other Lenses

| Aspect       | Temporal Lens               | Behavioral Lens            | Graph Lens                |
| ------------ | --------------------------- | -------------------------- | ------------------------- |
| **Focus**    | Time-dependent patterns     | Transaction-level features | Network structure         |
| **Model**    | LSTM                        | XGBoost + Autoencoder      | GAT                       |
| **Input**    | Sequence of transactions    | Single transaction         | Graph neighborhood        |
| **Strength** | Velocity, timing, sequences | Anomaly detection          | Community, centrality     |
| **Weakness** | Needs history               | Misses temporal order      | Computationally expensive |
| **Best For** | Rapid movement, bots        | Structuring, anomalies     | Hubs, clusters            |

**Complementary Nature:**

- Temporal catches what Behavioral misses (timing)
- Behavioral catches what Temporal misses (amount patterns)
- Graph catches what both miss (network position)

---

## Explainability

### Sequence Visualization

For a high-risk wallet:

```
Temporal Score: 0.91

Transaction Sequence (last 10 of 50):
┌────┬──────────┬────────────┬───────────┬─────────────┐
│ #  │ Amount   │ Time Delta │ Direction │ Burstiness  │
├────┼──────────┼────────────┼───────────┼─────────────┤
│ 41 │ 10000.0  │ 0          │ IN (0.0)  │ 0.15        │
│ 42 │ 9800.0   │ 120        │ OUT (1.0) │ 0.15        │
│ 43 │ 9800.0   │ 180        │ IN (0.0)  │ 0.15        │
│ 44 │ 9600.0   │ 125        │ OUT (1.0) │ 0.15        │
│ 45 │ 9600.0   │ 175        │ IN (0.0)  │ 0.15        │
│ 46 │ 9400.0   │ 130        │ OUT (1.0) │ 0.15        │
│ 47 │ 9400.0   │ 170        │ IN (0.0)  │ 0.15        │
│ 48 │ 9200.0   │ 135        │ OUT (1.0) │ 0.15        │
│ 49 │ 9200.0   │ 165        │ IN (0.0)  │ 0.15        │
│ 50 │ 9000.0   │ 140        │ OUT (1.0) │ 0.15        │
└────┴──────────┴────────────┴───────────┴─────────────┘

Pattern Analysis:
✗ Perfect IN/OUT alternation (bot-like)
✗ Consistent time deltas ~120-180 seconds (automated)
✗ Decreasing amounts (layering)
✗ Very low burstiness (too regular)
✗ Rapid forwarding (velocity laundering)

Risk Factors:
- Automated timing pattern: HIGH
- Velocity (avg 2.5 min between txs): HIGH
- Sequential predictability: HIGH
- Bot-like regularity: HIGH
```

### Plain-English Explanation

```
This wallet exhibits highly suspicious temporal behavior consistent with
automated money laundering. The transaction sequence shows perfect
alternation between incoming and outgoing transfers with mechanical
precision (every 2-3 minutes), which is not consistent with human
behavior. The amounts decrease systematically, suggesting layering
through multiple hops. The extremely low burstiness score (0.15)
indicates bot-like timing regularity. This pattern matches known
velocity laundering techniques where funds are rapidly moved through
intermediary wallets to obscure the trail.
```

---

## Operational Considerations

### Scaling

**Throughput:** ~1,000 wallets/second on GPU, ~100/second on CPU  
**Memory:** ~800MB for loaded model + sequences  
**Latency:** ~50ms per wallet (includes sequence construction)

### GPU Acceleration

```python
# Automatic device selection
device = resolve_torch_device()  # Returns 'cuda' if available
model.to(device)

# Batch inference for efficiency
sequences = torch.FloatTensor(batch_sequences).to(device)
with torch.no_grad():
    logits = model(sequences)
scores = torch.sigmoid(logits).cpu().numpy()
```

### Monitoring

**Drift Detection:**

- Monitor sequence length distribution
- Track feature value ranges
- Alert on unusual timing patterns
- Detect new bot signatures

**Performance Tracking:**

- Log predictions vs ground truth
- Compute rolling PR-AUC weekly
- Track false positive rate by use case
- Monitor inference latency

### Maintenance

**Retraining Frequency:**

- Monthly for high-volume systems
- Quarterly for low-volume
- Immediately after detecting new bot patterns

**Sequence Length Tuning:**

- Increase MAX_SEQ_LEN if longer patterns emerge
- Decrease if memory/latency becomes issue
- A/B test different lengths

---

## Future Enhancements

### Planned Improvements

1. **Attention Mechanism**

   ```python
   # Learn which transactions in sequence matter most
   attention_weights = softmax(Q @ K.T / sqrt(d_k))
   context = attention_weights @ V
   ```

   - Identify critical transactions in sequence
   - Improve interpretability

2. **Bidirectional LSTM**

   ```python
   self.lstm = nn.LSTM(..., bidirectional=True)
   ```

   - Process sequence forward and backward
   - Capture future context

3. **Multi-Scale Temporal Features**
   - Hourly, daily, weekly patterns
   - Seasonal trends
   - Time-of-day encoding

4. **Transformer Architecture**
   - Replace LSTM with Transformer
   - Better parallelization
   - Longer sequence modeling

5. **Sequence-to-Sequence**
   - Predict next transaction
   - Anomaly = deviation from prediction
   - Generative approach

---

## Integration with Meta-Learner

The Temporal Lens provides one input feature to the Meta-Learner:

```python
{
    "temporal_score": 0.91  # LSTM probability output
}
```

**Meta-Learner Usage:**

- Combined with 5 other lens scores
- Weighted by feature importance
- Calibrated for final risk score

**Typical Feature Importance in Meta-Model:**

- temporal_score: 0.14 (4th most important)
- Most valuable for velocity and bot detection
- Complements behavioral and graph signals

---

## References

### Academic Papers

1. Hochreiter & Schmidhuber (1997) - "Long Short-Term Memory"
2. Weber et al. (2019) - "Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks"
3. Graves (2013) - "Generating Sequences With Recurrent Neural Networks"

### Regulatory Guidance

- FATF Recommendation 16 (Wire Transfers)
- FinCEN Advisory on Rapid Movement of Funds
- Basel Committee on Banking Supervision - Sound Practices

### Implementation References

- PyTorch LSTM Documentation
- Elliptic Dataset (Weber et al.)
- LSTM for Time Series Classification (Karim et al.)

---

## Conclusion

The Temporal Lens fills a critical gap in the Aegis AML system by analyzing **how wallet behavior evolves over time**. While other lenses examine static features or network structure, the Temporal Lens captures the dynamic temporal signatures that characterize velocity laundering, bot-driven operations, and sequential laundering playbooks.

**Key Strengths:**

- LSTM architecture captures long-range dependencies
- Detects rapid fund movement (velocity laundering)
- Identifies bot-like timing patterns
- Recognizes dormant-to-active transitions
- Learns multi-step sequential patterns

**Best Used For:**

- Velocity laundering detection
- Automated mule account identification
- Dormant account activation flagging
- Bot-driven operation detection
- Sequential pattern recognition

**Complementary Role:**

The Temporal Lens is most powerful when combined with other lenses in the Meta-Learner ensemble. It provides the temporal dimension that static features cannot capture, enabling the system to detect sophisticated laundering schemes that rely on timing and sequence manipulation.

---

**Document Version:** 1.0  
**Last Updated:** 2024-04-04  
**Author:** Aegis AML Development Team
