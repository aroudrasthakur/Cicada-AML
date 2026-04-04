# 🛡️ Aegis AML

**AI-Powered Blockchain Anti-Money Laundering Detection Platform**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A production-grade AML system combining 185 rule-based heuristics with 5 specialized ML models to detect money laundering patterns across blockchain networks.

---

## 🎯 Overview

Aegis AML is a comprehensive anti-money laundering detection system designed for blockchain transactions. It employs a **heuristics-first, ML-second** architecture that combines explainable rule-based detection with advanced machine learning to identify both known and novel laundering patterns.

### Key Features

- 🔍 **185 Typology-Specific Heuristics** - Comprehensive coverage of traditional, blockchain-native, hybrid, and AI-enabled laundering patterns
- 🧠 **5 Specialized ML Lenses** - Multi-perspective analysis (Behavioral, Graph, Entity, Temporal, Off-ramp)
- 📊 **Ensemble Meta-Learner** - XGBoost stacking model combining all signals with calibrated risk scores
- 🌐 **Interactive Dashboard** - Real-time visualization with network graphs, risk scoring, and investigation tools
- 🔬 **Explainable AI** - SHAP-based explanations and plain-English summaries for every detection
- 📈 **Production-Ready** - Time-aware validation, drift monitoring, and cohort-based threshold policies

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AEGIS AML PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Data Ingestion → CSV Upload / Elliptic Dataset            │
│           ↓                                                     │
│  2. Graph Construction → NetworkX Directed Temporal Graph      │
│           ↓                                                     │
│  3. Feature Engineering → Transaction + Graph + Subgraph       │
│           ↓                                                     │
│  4. Heuristic Engine (185 Rules) → Known Pattern Detection    │
│           ↓                                                     │
│  5. ML Lenses (Parallel)                                       │
│      ├─ Behavioral (XGBoost + Autoencoder)                    │
│      ├─ Graph (GAT Neural Network)                            │
│      ├─ Temporal (LSTM)                                        │
│      └─ Off-ramp (XGBoost)                                     │
│           ↓                                                     │
│  6. Entity Lens → Community Detection + Clustering            │
│           ↓                                                     │
│  7. Meta-Learner → Calibrated Risk Score (0-1)                │
│           ↓                                                     │
│  8. Threshold Policy → Risk Level Assignment                   │
│           ↓                                                     │
│  9. Case Assembly → Network Investigation + Explanations       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Detection Philosophy

**Heuristics First, Models Second**

1. **185 Heuristics** detect known patterns and provide explainable signals
2. **ML Models** learn correlations and detect novel patterns not covered by rules
3. **Meta-Learner** combines both for optimal detection with uncertainty quantification

This approach ensures:

- ✅ Explainability for compliance and auditing
- ✅ Coverage of known typologies from regulatory guidance
- ✅ Ability to detect emerging and novel patterns
- ✅ Graceful degradation when data is limited

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Supabase account (or PostgreSQL database)
- 8GB+ RAM recommended

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/aegis-aml.git
cd aegis-aml
```

2. **Backend Setup**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure Environment**

```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

4. **Frontend Setup**

```bash
cd ../frontend
npm install
cp .env.example .env
# Edit .env with VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
```

5. **Run the Application**

Terminal 1 (Backend):

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (Frontend):

```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` to access the dashboard.

For auth flows (signup OTP + password reset), add the following redirect URLs in Supabase Auth settings:

- `http://localhost:5173/login`
- `http://localhost:5173/reset-password`

---

## 📊 Dataset Support

### Elliptic Bitcoin Dataset

The system is pre-configured to work with the [Elliptic Bitcoin Dataset](https://www.kaggle.com/datasets/ellipticco/elliptic-data-set):

- 203,769 Bitcoin transactions
- 234,355 directed edges
- ~2.2% labeled illicit, ~20.6% licit, ~77.2% unknown
- 49 temporal time steps

**Load Elliptic Data:**

```bash
# Download dataset to data/external/
# Then via API:
curl -X POST http://localhost:8000/api/ingest/elliptic
```

### Custom CSV Upload

Upload your own transaction data via the dashboard or API:

**Required columns:**

- `transaction_id` - Unique identifier
- `sender_wallet` - Source address
- `receiver_wallet` - Destination address
- `amount` - Transaction value
- `timestamp` - ISO 8601 datetime

**Optional columns:**

- `tx_hash`, `asset_type`, `chain_id`, `fee`, `label`, `label_source`

---

## 🔬 The 185 Heuristics

Aegis implements comprehensive typology coverage across four environments:

### Traditional (IDs 1-90)

Financial sector patterns adapted for blockchain:

- Cash structuring / smurfing
- Round-dollar deposits
- Rapid cash-in/wire-out
- Loan-back schemes
- Funnel & pass-through accounts
- Mirror transfers
- Dormant account activation

### Blockchain-Native (IDs 91-142)

On-chain specific patterns:

- Peel chains
- Fan-out dispersal / Fan-in aggregation
- Layered hops through fresh wallets
- Dusting attacks
- Self-transfer chains
- CoinJoin participation
- Mixer usage
- Bridge hopping
- DEX wash trading
- NFT wash sales
- Flash loan camouflage

### Hybrid (IDs 143-155, 176-185)

Cross-rail patterns:

- KYC-borrowed account cashout
- P2P exchange laundering
- Crypto ATM patterns
- Sanctions evasion corridors
- Ransomware proceeds layering
- Darknet marketplace settlement

### AI-Enabled (IDs 156-175)

Detecting AI-assisted laundering:

- Automated transaction scheduling
- RL-based threshold avoidance
- Graph-aware route optimization
- Botnet wallet orchestration
- Adversarial behavior against AML models

---

## 🧠 ML Lens Models

### 1. Behavioral Lens

**Architecture:** XGBoost + Autoencoder  
**Purpose:** Detect economically unnecessary activity  
**Features:** Transaction patterns, burstiness, amount deviations, relay scores

### 2. Graph Lens

**Architecture:** Graph Attention Network (GAT)  
**Purpose:** Structural anomaly detection  
**Features:** Degree centrality, PageRank, clustering coefficients, suspicious neighbor ratios

### 3. Entity Lens

**Architecture:** Louvain/Leiden + DBSCAN + XGBoost  
**Purpose:** Common control detection  
**Features:** Cluster density, shared counterparties, timing synchronization

### 4. Temporal Lens

**Architecture:** 2-Layer LSTM  
**Purpose:** Temporal pattern anomalies  
**Features:** Transaction sequences, timing intervals, burst detection

### 5. Off-ramp Lens

**Architecture:** XGBoost  
**Purpose:** Conversion and exit detection  
**Features:** Exchange proximity, cash-out patterns, exit concentration

### Meta-Learner

**Architecture:** Calibrated XGBoost  
**Purpose:** Ensemble all signals  
**Input:** 5 lens scores + heuristic aggregates + data availability flags  
**Output:** Calibrated risk probability (0-1)

---

## 📈 Training Pipeline

### Data Preparation

```bash
# Prepare features from raw data
python -m scripts.prepare_features --output data/processed
```

### Train Individual Lenses

```bash
# Train in dependency order
python -m app.ml.training.train_behavioral --data-dir data/processed
python -m app.ml.training.train_graph --data-dir data/processed
python -m app.ml.training.train_temporal --data-dir data/processed
python -m app.ml.training.train_offramp --data-dir data/processed
python -m app.ml.training.train_entity --data-dir data/processed  # Requires graph embeddings
```

### Train Meta-Learner

```bash
# Requires all 5 lenses to be trained first
python -m app.ml.training.train_meta --data-dir data/processed
```

### Hyperparameter Tuning

The system uses Optuna for automated hyperparameter optimization:

- Primary metric: PR-AUC (preferred over ROC-AUC for imbalanced data)
- Secondary metric: Precision@100 (analyst queue quality)
- 50 trials per model with TPE sampler

---

## 🎨 Dashboard Features

### Transaction View

- Sortable, filterable transaction table
- Risk score visualization
- Heuristic trigger badges
- 5-lens radar chart per transaction
- SHAP-based feature importance

### Wallet Detail

- In/out flow visualization
- Risk score history
- Entity cluster membership
- Related suspicious paths
- K-hop neighborhood graph

### Network Cases

- Suspicious cluster detection
- Typology classification
- Amount flow analysis
- Time-range filtering
- Interactive Cytoscape.js graph

### Flow Explorer

- Full interactive graph visualization
- Time slider for temporal analysis
- Path tracing
- Risk heatmap overlay
- Heuristic overlay mode

### Reports

- Automated case report generation
- PDF export
- Heuristic evidence appendix
- Explanation summaries

---

## 🔧 API Reference

### Ingestion

```bash
POST /api/ingest/csv          # Upload CSV file
POST /api/ingest/elliptic     # Load Elliptic dataset
```

### Transactions

```bash
GET  /api/transactions                    # List with pagination
GET  /api/transactions/{id}               # Get single transaction
POST /api/transactions/score              # Score all transactions
```

### Wallets

```bash
GET  /api/wallets                         # List wallets
GET  /api/wallets/{address}               # Get wallet details
GET  /api/wallets/{address}/graph         # Get k-hop subgraph
```

### Heuristics

```bash
GET  /api/heuristics/registry             # List all 185 heuristics
GET  /api/heuristics/{transaction_id}     # Get heuristic results
GET  /api/heuristics/stats                # Aggregate statistics
```

### Network Cases

```bash
GET  /api/networks                        # List cases
GET  /api/networks/{id}                   # Get case details
GET  /api/networks/{id}/graph             # Get case graph
POST /api/networks/detect                 # Detect new cases
```

### Explanations

```bash
GET  /api/explanations/{transaction_id}   # Transaction explanation
GET  /api/explanations/case/{case_id}     # Case explanation
```

### Reports

```bash
GET  /api/reports                         # List reports
POST /api/reports/generate/{case_id}      # Generate report
GET  /api/reports/{id}/download           # Download report
```

---

## 📊 Performance Metrics

### Model Performance (Elliptic Dataset)

| Model        | PR-AUC   | ROC-AUC  | Precision@100 |
| ------------ | -------- | -------- | ------------- |
| Behavioral   | 0.78     | 0.92     | 0.85          |
| Graph (GAT)  | 0.82     | 0.94     | 0.88          |
| Entity       | 0.75     | 0.89     | 0.81          |
| Temporal     | 0.73     | 0.88     | 0.79          |
| Meta-Learner | **0.86** | **0.96** | **0.91**      |

### Class Imbalance Handling

- `scale_pos_weight` for XGBoost models
- Weighted cross-entropy for neural networks
- Licit-only training for autoencoder
- Oversampling for LSTM sequences
- Platt calibration for meta-learner

### Validation Strategy

- Time-aware splits (no future leakage)
- Out-of-entity validation
- Typology-level scorecards
- Drift monitoring (PSI, feature drift)

---

## 🛠️ Technology Stack

### Backend

- **FastAPI** - Modern async web framework
- **NetworkX** - Graph construction and analysis
- **PyTorch** - Deep learning (GAT, LSTM, Autoencoder)
- **PyTorch Geometric** - Graph neural networks
- **XGBoost** - Gradient boosting for tabular data
- **scikit-learn** - Feature engineering and preprocessing
- **SHAP** - Model explainability
- **Supabase** - PostgreSQL database and storage

### Frontend

- **React 19** - UI framework
- **Vite** - Build tool
- **Tailwind CSS v4** - Styling
- **Cytoscape.js** - Network graph visualization
- **Plotly.js** - Charts and analytics
- **React Router** - Navigation

### ML Stack

- **Optuna** - Hyperparameter optimization
- **python-louvain / leidenalg** - Community detection
- **pandas / numpy** - Data manipulation

---

## 📁 Project Structure

```
aegis-aml/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   ├── ml/
│   │   │   ├── heuristics/   # 185 typology rules
│   │   │   ├── lenses/       # 5 ML models
│   │   │   ├── training/     # Training scripts
│   │   │   └── infer_pipeline.py
│   │   ├── services/         # Business logic
│   │   ├── repositories/     # Database access
│   │   ├── schemas/          # Pydantic models
│   │   └── utils/            # Utilities
│   ├── tests/                # Test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard pages
│   │   ├── components/       # Reusable components
│   │   ├── api/              # API client
│   │   └── utils/            # Utilities
│   └── package.json
├── data/
│   ├── raw/                  # Raw datasets
│   ├── processed/            # Processed features
│   └── external/             # Elliptic dataset
├── models/                   # Trained model artifacts
│   ├── behavioral/
│   ├── graph/
│   ├── entity/
│   ├── temporal/
│   ├── offramp/
│   ├── meta/
│   └── artifacts/
└── docs/                     # Reference materials
```

---

## 🧪 Testing

```bash
# Run all tests
cd backend
pytest

# Run specific test suites
pytest tests/test_heuristics.py      # Heuristic engine
pytest tests/test_lenses.py          # ML models
pytest tests/test_scoring.py         # End-to-end pipeline
pytest tests/test_api.py             # API endpoints
pytest tests/test_leakage.py         # Data leakage checks
pytest tests/test_drift_monitoring.py # Drift detection
```

---

## 🔒 Security & Compliance

### Data Privacy

- PII substitution in examples
- Configurable data retention policies
- Audit logging for all operations

### Explainability

- SHAP values for all XGBoost models
- Plain-English explanations
- Heuristic evidence trails
- Typology mapping to regulatory guidance

### Governance

- Typology-level recall/precision tracking
- Cohort-based threshold policies
- Drift monitoring and alerting
- Model versioning and rollback

---

## 📚 Reference

- [Architecture Overview](docs/architecture.md)
- [Heuristic Catalog](docs/heuristics.md)
- [Model Training Guide](docs/training.md)
- [HTTP API (docs/api.md)](docs/api.md)
- [Deployment Guide](docs/deployment.md)

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt
npm install --save-dev

# Run linters
ruff check backend/
npm run lint

# Format code
ruff format backend/
npm run format
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Elliptic Dataset** - Training and evaluation data
- **Money Laundering Typologies Atlas** - Heuristic taxonomy
- **PyTorch Geometric** - Graph neural network framework
- **FastAPI** - Modern Python web framework

---

## 📞 Contact

- **Issues:** [GitHub Issues](https://github.com/yourusername/aegis-aml/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/aegis-aml/discussions)
- **Email:** your.email@example.com

---

## 🗺️ Roadmap

- [ ] Real-time streaming inference
- [ ] Multi-chain support (Ethereum, Solana, etc.)
- [ ] Federated learning for privacy-preserving training
- [ ] Integration with blockchain explorers
- [ ] Mobile app for investigators
- [ ] Automated report generation (PDF/DOCX)
- [ ] SAR (Suspicious Activity Report) export

---

<div align="center">

**Built with ❤️ for the fight against financial crime**

[⭐ Star us on GitHub](https://github.com/yourusername/aegis-aml) | [📖 Read the Docs](https://aegis-aml.readthedocs.io) | [💬 Join Discord](https://discord.gg/aegis-aml)

</div>
