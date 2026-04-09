# Aegis AML (Cicada AML)

**AI-Powered Blockchain Anti-Money Laundering Platform** — repository root folder is typically `Aegis-AML`.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg)](https://www.python.org/downloads/)
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
| Python | 3.11+ | 3.12 / 3.13 work; use **python.org** or **py launcher** on Windows (avoid broken Store stubs) |
| Node.js | 20+ | Matches Vite 6 / React 19 toolchain |
| Supabase | any | Free tier works; Postgres + Auth + JWT for `/api/runs` |
| RAM | 8 GB+ | 16 GB+ recommended for full Elliptic training |
| GPU | optional | NVIDIA CUDA (see **GPU setup** below) or Apple **MPS** for PyTorch; XGBoost GPU needs a CUDA-capable wheel |

### 1. Clone

```bash
git clone <your-fork-url> Aegis-AML
cd Aegis-AML
```

### 2. Backend

Create a virtualenv at the **repo root** (recommended so one Python is shared by `backend/` and `scripts/`):

```bash
# Windows (PowerShell) — use py launcher if `python` is ambiguous
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r backend/requirements.txt
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt
```

Copy env and add Supabase keys:

```bash
cp backend/.env.example backend/.env
```

**GPU (NVIDIA)**: `backend/requirements.txt` installs **CPU PyTorch** by default. For CUDA (e.g. **RTX 50-series / Blackwell**, use **cu128** wheels — not cu124):

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install -r backend/requirements.txt
```

Verify PyTorch sees CUDA:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Set `ML_USE_GPU=true` in `backend/.env` (it defaults to **on** in code; set `false` to force CPU).

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY (same project as backend; use the anon key, not service role)
```

Restart `npm run dev` after any change to `.env`.

### 4. Database Migrations

Apply **all** SQL files in `supabase/migrations/` in **numeric filename order** (`001_*.sql` … `026_*.sql`, etc.) via the Supabase SQL editor, Supabase CLI, or `psql`. Earlier migrations create core tables (`transactions`, `wallets`, …); `018+` add pipeline runs, RLS, and run-scoped reporting.

### 5. Run

Run uvicorn with **`backend/`** as the working directory so `app` package imports resolve. Trained artifacts are loaded from **`models/`** at the **repository root** (`app.ml.model_paths`), not relative to cwd.

**Terminal 1 — backend**

```bash
cd backend
# If using repo-root venv: activate it first, then:
python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

**Terminal 2 — frontend**

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. Vite proxies **`/api`** to **`http://127.0.0.1:8000`** (see `frontend/vite.config.ts`; override with `VITE_API_PROXY_TARGET` if needed).

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
| `SUPABASE_JWT_SECRET` | no | HS256 JWT verification fallback (optional if using JWKS) |
| `FALLBACK_RISK_THRESHOLD` | no | Default decision threshold when no trained policy exists (default `0.75`) |
| `ML_USE_GPU` | no | `true` (default) uses **CUDA** (PyTorch + XGBoost when available) or **MPS** (Apple, PyTorch only); set `false` to force CPU |
| `OPENAI_API_KEY` | no | Enables LLM-generated report summaries; falls back to deterministic narrative |
| `OPENAI_MODEL` | no | Model name (default `gpt-4o-mini`) |
| `OPENAI_BASE_URL` | no | Override for Azure OpenAI or compatible endpoints |

Model paths default to `models/` at the **repo root** (`app.ml.model_paths.MODELS_DIR`); override via `MODEL_DIR` / `*_MODEL_PATH` if needed.

### Frontend (`frontend/.env` or `frontend/.env.local`)

Vite loads env from the `frontend/` directory (`envDir` in `vite.config.ts`). Use **`.env.local`** for secrets (gitignored).

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | yes | Same project URL as backend |
| `VITE_SUPABASE_ANON_KEY` | yes | **Anon** key (never the service role key) |
| `VITE_API_PROXY_TARGET` | no | Backend URL for the dev proxy (default `http://127.0.0.1:8000`) |

If `VITE_SUPABASE_*` are missing, the app falls back to placeholder values and login requests show `Apikey: invalid` in the browser network tab.

---

## Database Migrations

Migrations live in `supabase/migrations/`. Apply them in **strict numeric order** (`001_…` through `026_…` and any newer files). Highlights:

| Range | Purpose |
|-------|---------|
| `001`–`015` | Core AML schema: transactions, wallets, edges, scores, heuristics, network cases, reports, intel, RLS prep |
| `016`–`017` | Schema hardening, auth profiles |
| `018`–`023` | **Pipeline runs**: run-scoped tables, user scoping, progress, heuristic columns, SAR linkage |
| `024`–`026` | SAR reports and FK relaxations for reporting workflows |

Use the Supabase dashboard SQL editor, `supabase db push`, or `psql` against your project.

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
# bash / Git Bash
curl -X POST "http://localhost:8000/api/ingest/elliptic"
```

```powershell
# Windows PowerShell (curl is Invoke-WebRequest — use curl.exe)
curl.exe -X POST "http://localhost:8000/api/ingest/elliptic"
```

Place Elliptic CSVs under **`data/external/`** at the **repository root**. The ingest handler defaults to `data_dir=data/external` **relative to the server process working directory**. If you start uvicorn with **`cd backend`**, either run from the repo root with `python -m uvicorn ...` and cwd at root, or call:

`POST http://localhost:8000/api/ingest/elliptic?data_dir=../data/external`

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

**Recommended — full pipeline from Elliptic CSVs** (from **repository root**, with `.venv` activated):

```bash
python scripts/train_all_models.py
```

This runs, in order: `scripts.prepare_features` (Elliptic under `data/external/` → `data/processed/`) → parallel lens trainers (behavioral, graph, temporal, off-ramp) → `train_entity` → `scripts.score_training_data` → `scripts.prepare_meta_features` → `train_meta`. Artifacts are written to **`models/`** at the repo root.

Options:

```bash
python scripts/train_all_models.py --skip-features   # reuse existing data/processed
python scripts/train_all_models.py --input /path/to/elliptic_csvs
```

**Makefile** (Unix shell with `make`; on Windows use Git Bash or run the underlying commands):

| Target | Purpose |
|--------|---------|
| `make train` / `make train-all` | Same as `python scripts/train_all_models.py` |
| `make features` | `prepare_features` only |
| `make train-lenses-parallel` | Four lenses in parallel (bash `&` / `wait`) |
| `make train-entity` | Entity lens after graph embeddings exist |
| `make score-training-data` | Score `train_features.csv` with all trained lenses |
| `make prepare-meta-features` | Build `meta_features.csv` |
| `make train-meta` | Train meta-learner |

**Manual steps** (from `backend/`, paths relative to repo):

```bash
cd backend
python -m scripts.prepare_features --input ../data/external --output ../data/processed
python -m app.ml.training.train_graph --data-dir ../data/processed
python -m app.ml.training.train_behavioral --data-dir ../data/processed
python -m app.ml.training.train_temporal --data-dir ../data/processed
python -m app.ml.training.train_offramp --data-dir ../data/processed
python -m app.ml.training.train_entity --data-dir ../data/processed
python -m scripts.score_training_data --data-dir ../data/processed
python -m scripts.prepare_meta_features --data-dir ../data/processed
python -m app.ml.training.train_meta --data-dir ../data/processed
```

**Faster iteration**: `make subset-processed` produces `data/processed_subset/` for quicker training loops.

Training scripts use **Optuna** where configured, emphasize **PR-AUC** under imbalance, and time-aware splits where applicable. Trained weights under `models/` are picked up by the API and pipeline at runtime.

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
| `POST` | `/ingest/elliptic` | Load Elliptic Bitcoin dataset (`?data_dir=` path to CSV folder; default `data/external`) |

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
| `GET` | `/reports/{report_id}/download` | Download report file |
| `POST` | `/reports/{report_id}/generate-sar` | Generate SAR PDF from a report |
| `GET` | `/reports/sar/{sar_id}/download` | Download generated SAR PDF |

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

From the repo root (or `backend/`), run the full suite the same way CI does:

```bash
cd backend
python -m pytest tests/ -v
```

Selected modules (examples):

```bash
python -m pytest tests/test_heuristics.py -v
python -m pytest tests/test_lenses.py -v
python -m pytest tests/test_scoring.py -v
python -m pytest tests/test_enriched_suspicious.py -v
python -m pytest tests/test_summary_service.py -v
python -m pytest tests/test_leakage.py -v
python -m pytest tests/test_drift_monitoring.py -v
python -m pytest tests/test_threshold_policy.py -v
python -m pytest tests/test_typology_taxonomy.py -v
python -m pytest tests/test_audit_observability.py -v
```

SAR PDF and API flows have multiple modules named `tests/test_sar_*.py`; run the full `tests/` tree or invoke those paths explicitly (shell globs differ on Windows vs. bash).

There are **30** `test_*.py` modules under `backend/tests/` (heuristics, lenses, scoring, SAR pipeline, API, drift, etc.).

Frontend type checks:

```bash
cd frontend
npx tsc --noEmit
npm run lint
```

---

## Project Structure

```
Aegis-AML/   # clone directory name may vary
├── scripts/
│   └── train_all_models.py        # Full ML pipeline (features → lenses → score → meta)
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
│   ├── scripts/                    # prepare_features, score_training_data, prepare_meta_features, subset_processed_data
│   ├── tests/                      # pytest modules + conftest
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
│   └── migrations/                 # Ordered SQL (001 … 026; see [Database Migrations](#database-migrations))
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
- [x] SAR (Suspicious Activity Report) PDF generation and download (`/api/reports/.../generate-sar`)
- [ ] Blockchain explorer API integration for live enrichment
- [ ] Webhook / Slack alerts on high-risk detections
- [ ] Role-based access control (analyst vs. supervisor views)

---

<div align="center">

**Built for the fight against financial crime.**

</div>
