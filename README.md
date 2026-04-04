# Cicada AML

**AI-Powered Blockchain Anti-Money Laundering Platform**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Tailwind v4](https://img.shields.io/badge/Tailwind-4-06B6D4.svg)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Production-grade AML detection combining **185 rule-based heuristics** with **5 ML lens models** and a calibrated **meta-learner** to score, cluster, and explain suspicious activity on blockchain networks.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Environment Variables](#environment-variables)
5. [Database Migrations](#database-migrations)
6. [Pipeline Runs](#pipeline-runs)
7. [Dataset Support](#dataset-support)
8. [Heuristic Engine (185 Rules)](#heuristic-engine-185-rules)
9. [ML Lens Models](#ml-lens-models)
10. [Training Pipeline](#training-pipeline)
11. [Dashboard](#dashboard)
12. [API Reference](#api-reference)
13. [Testing](#testing)
14. [Project Structure](#project-structure)
15. [Security and Compliance](#security-and-compliance)
16. [Technology Stack](#technology-stack)
17. [Contributing](#contributing)
18. [License](#license)
19. [Roadmap](#roadmap)

---

## Overview

Cicada AML is a full-stack anti-money laundering detection system for blockchain transaction data. It follows a **heuristics-first, ML-second** architecture:

1. **185 heuristics** match known typologies (structuring, peel chains, fan-out, mixer usage, etc.) and produce explainable triggers.
2. **5 specialized ML lenses** (Behavioral, Graph, Entity, Temporal, Off-ramp) each score every transaction from a different analytical perspective.
3. A calibrated **XGBoost meta-learner** stacks all signals into a single 0-1 risk probability.
4. Threshold policies assign risk levels; suspicious transactions are grouped into **wallet clusters** for investigation.
5. The **React dashboard** surfaces risk queues, interactive flow graphs, heuristic badges, AI-generated report summaries, and full SAR-ready reports.

---

## Architecture

```
                         CICADA AML PIPELINE
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CSV Upload ──► Data Cleaning ──► Graph Construction (NetworkX)
                                          │
                     ┌────────────────────┤
                     ▼                    ▼
             Feature Engineering   Wallet Profiles
                     │                    │
                     ▼                    ▼
             ┌───────────────┐   Heuristic Engine (185 rules)
             │  ML Lenses    │    per-tx sequential evaluation
             │  ┌──────────┐ │            │
             │  │Behavioral│ │            ▼
             │  │ Graph    │ │   triggered_ids + confidence vector
             │  │ Temporal │ │            │
             │  │ Off-ramp │ │   ┌────────┘
             │  │ Entity   │ │   │
             │  └──────────┘ │   │
             └───────┬───────┘   │
                     │           │
                     ▼           ▼
               Meta-Learner (XGBoost stacking)
                     │
                     ▼
              Threshold Policy ──► Risk Level (high/medium/medium-low/low)
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   Suspicious Tx List    Cluster Detection
          │                     │
          ▼                     ▼
   run_suspicious_txns   run_clusters + Cytoscape graph snapshots
          │                     │
          └──────────┬──────────┘
                     ▼
              Structured Report + AI Summary
```

### Key Design Decisions

- **Heuristics first**: Every transaction is evaluated against all 185 rules before ML. Heuristic confidence scores feed into the meta-learner as features alongside lens outputs, so the model benefits from domain knowledge without being constrained by it.
- **Batch inference**: All lenses run in a single batched pass (one XGBoost/PyTorch call per lens), keeping wall-clock time proportional to the graph size, not the number of rules.
- **Threshold consistency**: A single `RiskTierConfig` (`lowRiskCeiling`, `decisionThreshold`, `highRiskThreshold`) drives risk labels everywhere -- backend scoring, frontend badges, Flow Explorer, and reports.
- **Supabase + RLS**: Row-level security scopes every pipeline run, score, cluster, and report to the owning user.

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | 3.12 recommended |
| Node.js | 18+ | LTS preferred |
| Supabase | any | Free tier works; or self-hosted PostgreSQL |
| RAM | 8 GB+ | 16 GB recommended if training models |
| GPU | optional | CUDA 12.x or Apple MPS for faster training |

### 1. Clone

```bash
git clone https://github.com/yourusername/cicada-aml.git
cd cicada-aml
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then fill in Supabase credentials
```

**GPU note**: for NVIDIA CUDA, install PyTorch with the matching CUDA index *before* `pip install -r requirements.txt`:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

### 3. Frontend

```bash
cd ../frontend
npm install
cp .env.example .env       # set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
```

### 4. Database Migrations

Apply every `.sql` file in `supabase/migrations/` in order (`018_*` through `023_*`) via the Supabase SQL editor or `psql`.

### 5. Run

**Terminal 1** -- backend:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2** -- frontend:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to the backend.

### 6. Auth Setup

In Supabase **Authentication > URL Configuration**, add these redirect URLs:

- `http://localhost:5173/login`
- `http://localhost:5173/reset-password`

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | yes | Supabase project URL |
| `SUPABASE_KEY` | yes | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | yes | Service role key (server-side only) |
| `SUPABASE_JWT_SECRET` | no | Only for legacy HS256 tokens |
| `FALLBACK_RISK_THRESHOLD` | no | Default decision threshold when no trained model exists (default `0.75`) |
| `ML_USE_GPU` | no | `true` to enable CUDA/MPS (default `false`) |
| `OPENAI_API_KEY` | no | Enables LLM-generated report summaries; falls back to deterministic narrative |
| `OPENAI_MODEL` | no | Model name (default `gpt-4o-mini`) |
| `OPENAI_BASE_URL` | no | Override for Azure OpenAI or compatible endpoints |

Model paths default to `models/` at the repo root and rarely need overriding.

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | yes | Same project URL |
| `VITE_SUPABASE_ANON_KEY` | yes | Same anon key |
| `VITE_API_PROXY_TARGET` | no | Override backend URL for dev proxy (default `http://127.0.0.1:8000`) |

---

## Database Migrations

Migrations live in `supabase/migrations/` and must be applied in filename order:

| Migration | Purpose |
|-----------|---------|
| `018_create_pipeline_runs.sql` | Core tables: `pipeline_runs`, `run_transactions`, `run_scores`, `run_suspicious_txns`, `run_clusters`, `run_cluster_members`, `run_reports`, `run_graph_snapshots` |
| `019_pipeline_runs_user_scoping.sql` | Adds `user_id` FK, enables RLS on all run tables |
| `020_add_report_summaries.sql` | `summary_text`, `summary_model`, `summary_generated_at` on `run_reports`; `report_ai_summaries` polymorphic table |
| `021_pipeline_runs_progress.sql` | `current_step`, `progress_log`, `scoring_tx_done`, `scoring_tx_total`, `lenses_completed` |
| `022_run_scores_heuristic_triggered_count.sql` | `heuristic_triggered_count` integer column |
| `023_run_scores_heuristic_explanations.sql` | `heuristic_explanations` JSONB column |

---

## Pipeline Runs

The primary workflow is **pipeline runs** -- upload CSVs, run scoring, review results:

1. **Upload**: `POST /api/runs` with CSV files.
2. **Start**: `POST /api/runs/{id}/start` -- kicks off the async pipeline.
3. **Monitor**: poll `GET /api/runs/{id}` for `progress_pct`, `current_step`, `lenses_completed`.
4. **Results**: `GET /api/runs/{id}/suspicious`, `/scores`, `/clusters`, `/report`.
5. **AI Summary**: `POST /api/runs/{id}/report/summary` generates a concise narrative.

The pipeline persists every intermediate result to Supabase, so the dashboard is populated in real time as scoring progresses.

---

## Dataset Support

### Elliptic Bitcoin Dataset

Pre-configured for the [Elliptic Bitcoin Dataset](https://www.kaggle.com/datasets/ellipticco/elliptic-data-set) (203,769 transactions, 234,355 edges):

```bash
curl -X POST http://localhost:8000/api/ingest/elliptic
```

### Custom CSV Upload

Upload transaction CSVs via the dashboard or `POST /api/runs`.

**Required columns**: `transaction_id`, `sender_wallet`, `receiver_wallet`, `amount`, `timestamp`

**Optional columns**: `tx_hash`, `asset_type`, `chain_id`, `fee`, `label`, `label_source`

---

## Heuristic Engine (185 Rules)

Every transaction is evaluated against all 185 rules. Each returns a confidence score (0-1) and, when triggered, an explanation string. The runner considers a heuristic **fired** if `triggered == True` or `confidence > 0`.

| Range | Environment | Count | Examples |
|-------|-------------|-------|----------|
| 1--90 | Traditional | 90 | Cash structuring, round-dollar deposits, rapid cash-in/wire-out, funnel accounts, mirror transfers, dormant activation |
| 91--142 | Blockchain | 52 | Peel chains, fan-out dispersal, fan-in aggregation, dusting, self-transfer chains, CoinJoin, mixer usage, bridge hopping, DEX wash trading, NFT wash sales |
| 143--155, 176--185 | Hybrid | 23 | KYC-borrowed account cashout, P2P exchange laundering, crypto ATM patterns, sanctions evasion, ransomware layering, darknet settlement |
| 156--175 | AI-Enabled | 20 | Automated scheduling, RL threshold avoidance, graph-aware routing, botnet orchestration, adversarial model drift |

Heuristics that require off-chain data still register (so IDs are contiguous) but are marked **inapplicable** when context is missing.

Fired heuristic IDs, count, top typology, top confidence, and per-ID explanations are stored in `run_scores` and surfaced in the Flow Explorer sidebar and reports.

---

## ML Lens Models

| Lens | Architecture | Purpose |
|------|-------------|---------|
| **Behavioral** | XGBoost + Autoencoder | Detect economically unnecessary activity (burstiness, amount deviations, relay scores) |
| **Graph** | Graph Attention Network (GAT) | Structural anomaly detection (centrality, PageRank, suspicious neighbor ratios) |
| **Entity** | Louvain/Leiden + DBSCAN + XGBoost | Common control detection (cluster density, shared counterparties, timing sync) |
| **Temporal** | 2-Layer LSTM | Sequence anomalies (timing intervals, burst detection) |
| **Off-ramp** | XGBoost | Exit and conversion detection (exchange proximity, cash-out patterns) |
| **Meta-Learner** | Calibrated XGBoost | Stacks 5 lens scores + heuristic aggregates + data-availability flags into a calibrated 0-1 risk probability |

Platt sigmoid calibration is applied to the meta-learner so scores are interpretable as probabilities.

---

## Training Pipeline

```bash
cd backend

# 1. Prepare features
python -m scripts.prepare_features --output data/processed

# 2. Train lenses (any order; entity needs graph embeddings)
python -m app.ml.training.train_behavioral --data-dir data/processed
python -m app.ml.training.train_graph --data-dir data/processed
python -m app.ml.training.train_temporal --data-dir data/processed
python -m app.ml.training.train_offramp --data-dir data/processed
python -m app.ml.training.train_entity --data-dir data/processed

# 3. Prepare meta features (stacked lens + heuristic outputs)
python -m scripts.prepare_meta_features

# 4. Train meta-learner
python -m app.ml.training.train_meta --data-dir data/processed
```

- Optuna-based hyperparameter search (50 trials, TPE sampler).
- Primary metric: **PR-AUC** (robust to class imbalance). Secondary: **Precision@100** (analyst queue quality).
- Time-aware splits prevent future leakage.

Trained artifacts are saved under `models/` and loaded automatically at server startup.

---

## Dashboard

| Page | Route | Description |
|------|-------|-------------|
| Landing | `/` | Marketing / overview |
| Login | `/login` | Supabase auth (email OTP + password) |
| Dashboard | `/dashboard` | Risk summary cards, model performance chart, suspicious queue |
| Transactions | `/dashboard/transactions` | Paginated risk-scored table with lens radar charts |
| Flow Explorer | `/dashboard/flow-explorer` | Canvas graph per cluster, heuristic sidebar, node inspect panel |
| Network Cases | `/dashboard/network-cases` | Cytoscape.js case graphs |
| Wallets | `/dashboard/wallets/:address` | Wallet-level risk, k-hop subgraph |
| Reports | `/dashboard/reports` | Per-run structured report + AI summary panel |
| Reset Password | `/reset-password` | Password reset flow |

Risk tier badges, colors, and labels are driven by the centralized `RiskTierConfig` from `GET /api/runs/model/threshold`, ensuring consistency across every page.

---

## API Reference

All endpoints are prefixed with `/api`. Authentication is via Supabase JWT in the `Authorization: Bearer <token>` header. The backend validates the token and scopes results to the owning user.

### Pipeline Runs (`/api/runs`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/runs/dashboard/stats` | Aggregate dashboard statistics |
| `GET` | `/runs/model/metrics` | Trained model PR-AUC, ROC-AUC, feature importance |
| `GET` | `/runs/model/threshold` | Active threshold policy (`decision_threshold`, `high_risk_threshold`, `low_risk_ceiling`) |
| `POST` | `/runs` | Create a new run (multipart CSV upload) |
| `GET` | `/runs` | List runs for the current user |
| `POST` | `/runs/{run_id}/start` | Start async pipeline execution |
| `GET` | `/runs/{run_id}` | Run status and progress |
| `GET` | `/runs/{run_id}/scores` | All score rows |
| `GET` | `/runs/{run_id}/suspicious` | Enriched suspicious transactions (joined with `run_transactions` + `run_scores`) |
| `GET` | `/runs/{run_id}/wallets` | Wallet-level aggregated view |
| `GET` | `/runs/{run_id}/clusters` | Cluster list |
| `GET` | `/runs/{run_id}/clusters/{cluster_id}/graph` | Cytoscape graph snapshot |
| `GET` | `/runs/{run_id}/clusters/{cluster_id}/members` | Cluster wallet members |
| `GET` | `/runs/{run_id}/report` | Structured JSON report |
| `GET` | `/runs/{run_id}/report/summary` | Cached AI summary |
| `POST` | `/runs/{run_id}/report/summary` | Generate AI summary (idempotent; `?force=true` to regenerate) |

### Ingestion (`/api/ingest`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest/csv` | Upload CSV for legacy scoring path |
| `POST` | `/ingest/elliptic` | Load Elliptic Bitcoin dataset |

### Transactions (`/api/transactions`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/transactions` | Paginated list |
| `GET` | `/transactions/{id}` | Single transaction |
| `POST` | `/transactions/score` | Score all transactions (legacy) |

### Wallets (`/api/wallets`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/wallets` | List wallets |
| `GET` | `/wallets/{address}` | Wallet detail |
| `GET` | `/wallets/{address}/graph` | k-hop subgraph (Cytoscape JSON) |

### Heuristics (`/api/heuristics`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/heuristics/registry` | Full 185-heuristic catalog |
| `GET` | `/heuristics/stats` | Aggregate trigger statistics |
| `GET` | `/heuristics/{transaction_id}` | Per-transaction heuristic results |

### Network Cases (`/api/networks`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/networks` | List cases |
| `GET` | `/networks/{case_id}` | Case detail |
| `GET` | `/networks/{case_id}/graph` | Case graph |
| `POST` | `/networks/detect` | Detect new cases |

### Explanations (`/api/explanations`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/explanations/{transaction_id}` | SHAP-based transaction explanation |
| `GET` | `/explanations/case/{case_id}` | Case explanation |

### Reports (`/api/reports`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/reports` | List reports |
| `POST` | `/reports/generate/{case_id}` | Generate case report |
| `GET` | `/reports/{report_id}` | Report detail |
| `GET` | `/reports/{report_id}/download` | Download report |

### Metrics and Policies (`/api/metrics`, `/api/policies`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/metrics/typology` | Typology-level precision/recall |
| `GET` | `/metrics/cohort` | Cohort metrics |
| `GET` | `/metrics/drift` | Feature and score drift (PSI) |
| `GET` | `/policies/thresholds` | Current threshold policies |
| `PUT` | `/policies/thresholds/{cohort_key}` | Update a threshold policy |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |

---

## Testing

```bash
cd backend
pytest                                  # all tests
pytest tests/test_heuristics.py         # 185-heuristic engine
pytest tests/test_lenses.py             # ML lens models
pytest tests/test_scoring.py            # end-to-end pipeline
pytest tests/test_enriched_suspicious.py # enrichment + heuristic labels
pytest tests/test_summary_service.py    # AI summary generation
pytest tests/test_leakage.py            # data leakage checks
pytest tests/test_drift_monitoring.py   # drift detection
pytest tests/test_threshold_policy.py   # threshold policies
pytest tests/test_typology_taxonomy.py  # typology mapping
pytest tests/test_audit_observability.py # observability instrumentation
```

Frontend type checks:

```bash
cd frontend
npx tsc --noEmit
npm run lint
```

---

## Project Structure

```
cicada-aml/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI route modules
│   │   │   ├── routes_runs.py      # Pipeline run lifecycle + dashboard stats
│   │   │   ├── routes_ingest.py    # CSV / Elliptic ingestion
│   │   │   ├── routes_transactions.py
│   │   │   ├── routes_wallets.py
│   │   │   ├── routes_heuristics.py
│   │   │   ├── routes_networks.py
│   │   │   ├── routes_explanations.py
│   │   │   ├── routes_reports.py
│   │   │   ├── routes_metrics.py
│   │   │   └── routes_policies.py
│   │   ├── ml/
│   │   │   ├── heuristics/         # 185 typology rules
│   │   │   │   ├── base.py         # BaseHeuristic, HeuristicResult, Applicability
│   │   │   │   ├── traditional.py  # IDs 1-90
│   │   │   │   ├── blockchain.py   # IDs 91-142
│   │   │   │   ├── hybrid.py       # IDs 143-155, 176-185
│   │   │   │   ├── ai_enabled.py   # IDs 156-175
│   │   │   │   ├── common_red_flags.py
│   │   │   │   ├── registry.py     # Central ID → class map
│   │   │   │   └── runner.py       # run_all() orchestrator
│   │   │   ├── lenses/             # 5 ML scoring models
│   │   │   │   ├── behavioral_model.py
│   │   │   │   ├── graph_model.py
│   │   │   │   ├── entity_model.py
│   │   │   │   ├── temporal_model.py
│   │   │   │   └── offramp_model.py
│   │   │   ├── training/           # Training scripts per lens + meta
│   │   │   ├── infer_pipeline.py   # InferencePipeline orchestrator
│   │   │   ├── explainers.py       # SHAP + plain-English explanations
│   │   │   ├── typology_taxonomy.py # Heuristic→typology mapping
│   │   │   └── platt_calibrator.py
│   │   ├── services/               # Business logic
│   │   │   ├── pipeline_run_service.py  # Async run orchestrator
│   │   │   ├── summary_service.py       # LLM / deterministic report summary
│   │   │   ├── scoring_service.py
│   │   │   ├── graph_service.py
│   │   │   ├── clustering_service.py
│   │   │   ├── explanation_service.py
│   │   │   └── report_service.py
│   │   ├── repositories/           # Supabase data access
│   │   ├── schemas/                # Pydantic models
│   │   ├── utils/                  # Logger, graph helpers, device detection
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   ├── main.py                 # FastAPI app + router registration
│   │   └── supabase_client.py
│   ├── scripts/                    # Data prep and meta-feature generation
│   ├── tests/                      # 18 test modules + conftest
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                  # 10 route pages
│   │   ├── components/             # Reusable UI (TransactionTable, FlowCanvas, etc.)
│   │   ├── contexts/               # AuthContext, RunProvider, ThresholdProvider, ScoringModeProvider
│   │   ├── api/                    # Axios client + typed API functions
│   │   ├── types/                  # TypeScript interfaces
│   │   ├── utils/                  # riskTiers, flowExplorerFromRun, suspiciousQueueRow
│   │   └── layouts/                # DashboardLayout
│   └── package.json
├── models/                         # Trained model artifacts (gitignored)
│   ├── behavioral/
│   ├── graph/
│   ├── entity/
│   ├── temporal/
│   ├── offramp/
│   ├── meta/
│   └── artifacts/                  # threshold_config.json, feature_names.pkl
├── supabase/
│   └── migrations/                 # 018-023 SQL migrations
├── data/                           # Raw/processed datasets (gitignored)
├── docs/                           # Lens reports, pipeline audit
└── README.md
```

---

## Security and Compliance

### Authentication and Authorization

- Supabase Auth with JWT validation on every API request.
- Row-level security (RLS) on all run-scoped tables; users can only access their own data.
- Service role key is server-side only and never exposed to the browser.

### Explainability

- SHAP values for all XGBoost-based models.
- Plain-English explanations generated per transaction by `generate_explanation_text`.
- Per-heuristic explanation strings stored in `run_scores.heuristic_explanations` JSONB.
- Typology mapping from heuristic names to user-facing labels via `typology_taxonomy.py`.

### Data Handling

- No PII in heuristic or model outputs -- only wallet addresses and transaction IDs.
- Configurable data retention via Supabase policies.
- Audit logging for pipeline runs (`progress_log` with timestamped entries).

### Model Governance

- Typology-level precision/recall tracking (`GET /api/metrics/typology`).
- Feature and score drift monitoring via PSI (`GET /api/metrics/drift`).
- Cohort-based threshold policies (`GET/PUT /api/policies/thresholds`).
- Model versioning through artifact paths; rollback by swapping files.
- Time-aware validation splits prevent future-data leakage (tested in `test_leakage.py`).

---

## Technology Stack

### Backend

| Library | Role |
|---------|------|
| FastAPI 0.115+ | Async web framework with automatic OpenAPI docs |
| Supabase (supabase-py) | PostgreSQL database, auth, and storage |
| NetworkX 3.3+ | Directed graph construction and analysis |
| PyTorch 2.4+ | Deep learning (GAT, LSTM, Autoencoder) |
| PyTorch Geometric 2.6+ | Graph neural networks |
| XGBoost 2.1+ | Gradient boosting for tabular scoring |
| scikit-learn 1.5+ | Preprocessing, evaluation, and calibration |
| SHAP 0.46+ | Model explainability |
| Optuna 4.1+ | Hyperparameter optimization |
| python-louvain / leidenalg | Community detection |

### Frontend

| Library | Role |
|---------|------|
| React 19 | UI framework |
| Vite + Tailwind CSS v4 | Build tool and utility-first styling |
| React Router 7 | Client-side routing |
| Cytoscape.js | Network graph visualization |
| Plotly.js | Charts and analytics |
| Lucide React | Icon library |
| Axios | HTTP client |
| Supabase JS | Auth and real-time (client-side) |

---

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Backend linting and formatting
cd backend
ruff check .
ruff format .

# Frontend linting and type checking
cd frontend
npm run lint
npx tsc --noEmit
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Roadmap

- [ ] Real-time streaming inference via WebSocket
- [ ] Multi-chain support (Ethereum, Solana, Tron)
- [ ] Federated learning for privacy-preserving cross-institution training
- [ ] SAR (Suspicious Activity Report) PDF/DOCX export
- [ ] Blockchain explorer API integration for live enrichment
- [ ] Webhook / Slack alerts on high-risk detections
- [ ] Role-based access control (analyst vs. supervisor views)

---

<div align="center">

**Built for the fight against financial crime.**

</div>
