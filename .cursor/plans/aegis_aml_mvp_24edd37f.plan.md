---
name: Aegis AML MVP
overview: "Build a production-grade Aegis AML platform from scratch: FastAPI backend with a 185-typology heuristic engine feeding 6 lens-specific ML models (Behavioral, Graph, Entity, Temporal, Document, Off-ramp) stacked under an XGBoost meta-learner, Supabase database, and a React + Vite + Tailwind + Cytoscape.js frontend dashboard. Objective is risk-ranked detection with measurable recall/precision by typology and explicit coverage tiers."
todos:
  - id: scaffolding
    content: "Phase 1: Project scaffolding - backend (FastAPI structure, deps, config) + frontend (Vite + React + Tailwind + routing) + root files (docker-compose, .gitignore, Makefile, README)"
    status: completed
  - id: database
    content: "Phase 2: Supabase migrations - core + intelligence tables (transactions, wallets, edges, heuristic_results, transaction_scores, wallet_scores, network_cases, reports, document_events, entity_links, address_tags, model_metrics, threshold_policies, RLS) + seed data"
    status: completed
  - id: ingestion
    content: "Phase 3: Data ingestion pipeline - CSV upload, Elliptic loader, normalization, cleaning, wallet creation, Supabase persistence"
    status: completed
  - id: graph
    content: "Phase 4: Graph construction - NetworkX directed temporal graph, node/edge features, k-hop expansion, subgraph extraction"
    status: completed
  - id: features
    content: "Phase 5: Feature engineering - transaction features, wallet/neighborhood features, subgraph/sequence features, combined feature matrix"
    status: completed
  - id: heuristics
    content: "Phase 6: Heuristic engine - 185 typology-specific rule checks (traditional 1-90, blockchain 91-142, AI-enabled 156-175, hybrid 143-155/176-185), each returning triggered/confidence/explanation + applicability + evidence"
    status: completed
  - id: lens-models
    content: "Phase 7: 6 Lens models - Behavioral (XGBoost+Autoencoder), Graph (GAT), Entity (Louvain/Leiden+clustering), Temporal (LSTM), Document (XGBoost+NLP), Off-ramp (XGBoost+classifier). Each consumes heuristic outputs + lens-specific features."
    status: completed
  - id: training
    content: "Phase 7b: Model training - class imbalance handling, per-lens training procedures, hyperparameter tuning, time-aware cross-validation, training orchestration in dependency order"
    status: completed
  - id: meta-model
    content: "Phase 8: Meta-model - XGBoost meta-learner combining 6 lens scores + anomaly signals + heuristic aggregates + data-availability flags with calibration and policy thresholds"
    status: completed
  - id: inference
    content: "Phase 9: Inference pipeline - heuristics-first then lens models, case assembly, explanation generation, SHAP"
    status: completed
  - id: api-routes
    content: "Phase 10: API routes - all FastAPI endpoints for ingest, transactions, wallets, heuristics, networks, explanations, reports"
    status: completed
  - id: frontend
    content: "Phase 11: Frontend dashboard - 6 pages (Dashboard, Transactions, Wallet, NetworkCases, FlowExplorer, Reports) + 8+ shared components + Cytoscape.js graph + heuristic display"
    status: completed
  - id: integration
    content: "Phase 12: Integration and polish - metrics reporting, report generation, storage service, out-of-time validation, drift monitoring, and end-to-end testing"
    status: completed
isProject: false
---

# Aegis AML: Full Implementation Plan

## Detection Objective and Non-Goal

Primary objective: produce a **risk-ranked queue of suspicious activity** with measurable quality by typology and segment (asset, chain, customer class, jurisdiction).

Explicit non-goal: "identify all money laundering cases." In AML this is not achievable; the system is judged by **coverage, recall, precision, and investigation efficiency** under uncertainty.

Required operating targets (to be tuned per deployment cohort):

- Typology-level recall floor and precision floor for high-priority typologies
- False positives per 1,000 transactions ceiling by segment
- Precision@K for analyst queue quality
- Time-to-detection and time-to-investigate reduction

## Architecture Overview

```mermaid
flowchart TB
    subgraph frontend ["Frontend (React + Vite + Tailwind)"]
        DashboardPage --> APIClient
        TransactionsPage --> APIClient
        WalletPage --> APIClient
        NetworkCasesPage --> APIClient
        FlowExplorerPage --> APIClient
        ReportsPage --> APIClient
    end

    subgraph backend ["Backend (FastAPI)"]
        APIClient --> Routes
        Routes --> Services
        Services --> Repos
        Services --> MLPipeline
        Repos --> SupabaseClient
    end

    subgraph ml ["ML Pipeline"]
        MLPipeline --> FeatureEng["Feature Engineering"]
        FeatureEng --> HeuristicEngine["Heuristic Engine (185 typologies)"]
        HeuristicEngine --> LensModels
        subgraph LensModels ["Layer A: 6 Lens Models"]
            BehavioralModel["Behavioral (XGBoost + Autoencoder)"]
            GraphModel["Graph (GAT)"]
            EntityModel["Entity (Louvain/Leiden + clustering)"]
            TemporalModel["Temporal (LSTM)"]
            DocumentModel["Document (XGBoost + NLP)"]
            OfframpModel["Off-ramp (XGBoost + classifier)"]
        end
        LensModels --> MetaModel["Layer B: XGBoost Meta-Learner"]
        MetaModel --> CaseAssembly["Case Assembly + Explanation"]
    end

    subgraph data ["Data Layer"]
        SupabaseClient --> SupabaseDB["Supabase PostgreSQL"]
        SupabaseClient --> SupabaseBuckets["Supabase Storage"]
    end
```

## Data Flow (Heuristics-First Pipeline)

```mermaid
flowchart LR
    CSV["CSV Upload / Elliptic"] --> Ingest["Ingest and Clean"]
    Ingest --> GraphBuild["Graph Construction"]
    GraphBuild --> Features["Feature Engineering"]
    Features --> Heuristics["185 Typology Heuristics"]
    Heuristics --> BehavioralLens["Behavioral Lens"]
    Heuristics --> GraphLens["Graph Lens"]
    Heuristics --> EntityLens["Entity Lens"]
    Heuristics --> TemporalLens["Temporal Lens"]
    Heuristics --> DocumentLens["Document Lens"]
    Heuristics --> OfframpLens["Off-ramp Lens"]
    BehavioralLens --> Meta["XGBoost Meta-Learner"]
    GraphLens --> Meta
    GraphLens -.-> EntityLens
    EntityLens --> Meta
    TemporalLens --> Meta
    DocumentLens --> Meta
    OfframpLens --> Meta
    Meta --> FinalRisk["Final Risk Score"]
    FinalRisk --> CaseGen["Network Case Assembly"]
    CaseGen --> Explain["Explanation Generation"]
    Explain --> Dashboard["Dashboard"]
```

## Key Design Principle: Heuristics First, Models Second

The pipeline enforces a strict ordering:

1. **Heuristics run first**: 185 typology-specific rules each check for one known laundering pattern and output a triggered flag, confidence score, applicability status, and explanation string. These are deterministic and explainable.
2. **Lens models run second**: Each of the 6 lens models receives the heuristic output vector (185 scores) as additional input features alongside its own lens-specific features. This lets the models learn correlations between known patterns and also detect **novel patterns** not covered by the 185 heuristics.
3. **Meta-model combines**: The 6 lens scores + aggregated heuristic signals feed the final XGBoost meta-learner.

The 185 typologies are treated as a **known-pattern floor**, not a ceiling. The ML models exist specifically to catch what the heuristics miss.

Critical guardrail: if required data for a heuristic is missing, the heuristic must return `applicability=inapplicable_missing_data` (never silent `false`). This prevents false confidence and preserves auditability.

---

## Phase 1: Project Scaffolding

### Backend (`backend/`)

- Initialize FastAPI app with the full folder structure from the spec
- `backend/requirements.txt` with pinned deps: `fastapi`, `uvicorn`, `supabase`, `pandas`, `numpy`, `scikit-learn`, `xgboost`, `lightgbm`, `torch`, `torch-geometric`, `networkx`, `python-louvain`, `shap`, `pydantic`, `python-multipart`, `python-dotenv`, `joblib`, `leidenalg`, `igraph`, `optuna`
- `backend/app/main.py` - FastAPI app with CORS, router registration
- `backend/app/config.py` - Pydantic Settings loading from `.env`
- `backend/app/supabase_client.py` - Supabase client singleton
- `backend/app/dependencies.py` - FastAPI dependency injection (get_db, get_graph, get_models)
- `backend/app/utils/logger.py` - Structured logging setup
- `backend/app/utils/time_utils.py` - Timestamp parsing, time-window helpers
- `backend/app/utils/file_utils.py` - CSV reading, model path resolution
- `backend/.env.example` with all vars:
  ```
  APP_ENV=development
  API_PORT=8000
  FRONTEND_PORT=5173
  SUPABASE_URL=
  SUPABASE_KEY=
  SUPABASE_SERVICE_ROLE_KEY=
  SUPABASE_BUCKET_RAW=raw-datasets
  SUPABASE_BUCKET_REPORTS=reports
  SUPABASE_BUCKET_MODELS=model-artifacts
  MODEL_DIR=./models
  BEHAVIORAL_MODEL_PATH=./models/behavioral/xgboost_behavioral.pkl
  BEHAVIORAL_AE_PATH=./models/behavioral/autoencoder_behavioral.pt
  GRAPH_MODEL_PATH=./models/graph/gat_model.pt
  ENTITY_MODEL_PATH=./models/entity/entity_classifier.pkl
  TEMPORAL_MODEL_PATH=./models/temporal/lstm_model.pt
  DOCUMENT_MODEL_PATH=./models/document/document_classifier.pkl
  OFFRAMP_MODEL_PATH=./models/offramp/offramp_classifier.pkl
  META_MODEL_PATH=./models/meta/meta_model.pkl
  THRESHOLD_POLICY_PATH=./models/artifacts/threshold_config.json
  FALLBACK_RISK_THRESHOLD=0.75
  NETWORK_HOPS=3
  ```

### Frontend (`frontend/`)

- Scaffold with `npm create vite@latest` (React + TypeScript)
- Install: `tailwindcss`, `@tailwindcss/vite`, `react-router-dom`, `cytoscape`, `react-cytoscapejs`, `plotly.js`, `react-plotly.js`, `@supabase/supabase-js`, `axios`, `lucide-react`
- Set up routing in `App.tsx` with 6 pages
- Create `frontend/src/api/client.ts` with Axios base config
- Create `frontend/src/api/supabase.ts` with Supabase client
- Create `frontend/src/utils/formatters.ts` - Number, date, risk-level formatters
- Create `frontend/src/utils/graphTransform.ts` - Transform API graph data to Cytoscape elements

### Root

- `docker-compose.yml` for backend + frontend
- `.gitignore` (Python, Node, .env, models/, data/, **pycache**, .venv, node_modules)
- `Makefile` with common commands (dev, train, ingest, test, lint)
- `README.md`

### Empty directory stubs

- `data/raw/`, `data/processed/`, `data/external/` (with `.gitkeep`)
- `models/behavioral/`, `models/graph/`, `models/entity/`, `models/temporal/`, `models/document/`, `models/offramp/`, `models/meta/`, `models/artifacts/` (with `.gitkeep`)
- `notebooks/`, `scripts/`, `docs/`

---

## Phase 2: Database (Supabase Migrations)

Create `supabase/config.toml` with project config.

Create SQL migration files in `supabase/migrations/`:

- **001_create_transactions.sql**: `transactions` table (id UUID PK, transaction_id TEXT UNIQUE, tx_hash TEXT, sender_wallet TEXT NOT NULL, receiver_wallet TEXT NOT NULL, amount NUMERIC NOT NULL, asset_type TEXT, chain_id TEXT, timestamp TIMESTAMPTZ NOT NULL, fee NUMERIC, label TEXT, label_source TEXT, created_at TIMESTAMPTZ DEFAULT now()). Indexes on sender_wallet, receiver_wallet, timestamp, label.
- **002_create_wallets.sql**: `wallets` table (id UUID PK, wallet_address TEXT UNIQUE NOT NULL, chain_id TEXT, first_seen TIMESTAMPTZ, last_seen TIMESTAMPTZ, total_in NUMERIC DEFAULT 0, total_out NUMERIC DEFAULT 0, created_at TIMESTAMPTZ DEFAULT now()). Index on wallet_address.
- **003_create_edges.sql**: `edges` table (id UUID PK, sender_wallet TEXT NOT NULL, receiver_wallet TEXT NOT NULL, transaction_id TEXT REFERENCES transactions(transaction_id), amount NUMERIC, timestamp TIMESTAMPTZ). Indexes on sender_wallet, receiver_wallet.
- **004_create_heuristic_results.sql**: `heuristic_results` table (id UUID PK, transaction_id TEXT REFERENCES transactions(transaction_id), heuristic_vector JSONB NOT NULL, applicability_vector JSONB NOT NULL, triggered_ids JSONB NOT NULL, triggered_count INT, top_typology TEXT, top_confidence FLOAT, explanations JSONB, scored_at TIMESTAMPTZ DEFAULT now()). UNIQUE on transaction_id. Index on triggered_count, top_typology. `heuristic_vector` stores 185 scores; `applicability_vector` stores per-typology applicability status.
- **005_create_transaction_scores.sql**: `transaction_scores` (id UUID PK, transaction_id TEXT UNIQUE REFERENCES transactions(transaction_id), behavioral_score FLOAT, behavioral_anomaly_score FLOAT, graph_score FLOAT, entity_score FLOAT, temporal_score FLOAT, document_score FLOAT, offramp_score FLOAT, meta_score FLOAT, predicted_label TEXT, explanation_summary TEXT, scored_at TIMESTAMPTZ DEFAULT now()).
- **006_create_wallet_scores.sql**: `wallet_scores` (id UUID PK, wallet_address TEXT UNIQUE REFERENCES wallets(wallet_address), risk_score FLOAT, fan_in_score FLOAT, fan_out_score FLOAT, velocity_score FLOAT, exposure_score FLOAT, scored_at TIMESTAMPTZ DEFAULT now())
- **007_create_network_cases.sql**: `network_cases` (id UUID PK, case_name TEXT, typology TEXT, risk_score FLOAT, total_amount NUMERIC, start_time TIMESTAMPTZ, end_time TIMESTAMPTZ, explanation TEXT, graph_snapshot_path TEXT, created_at TIMESTAMPTZ DEFAULT now()) + junction table `network_case_wallets` (case_id UUID FK, wallet_address TEXT FK)
- **008_create_reports.sql**: `reports` (id UUID PK, case_id UUID REFERENCES network_cases(id), title TEXT, report_path TEXT, generated_at TIMESTAMPTZ DEFAULT now())
- **009_create_document_events.sql**: `document_events` (id UUID PK, entity_id TEXT, transaction_id TEXT NULL, doc_type TEXT, parsed_fields JSONB, quality_score FLOAT, created_at TIMESTAMPTZ DEFAULT now())
- **010_create_entity_links.sql**: `entity_links` (id UUID PK, wallet_address TEXT, entity_id TEXT, link_type TEXT, link_strength FLOAT, source TEXT, created_at TIMESTAMPTZ DEFAULT now())
- **011_create_address_tags.sql**: `address_tags` (id UUID PK, wallet_address TEXT, tag TEXT, tag_source TEXT, confidence FLOAT, valid_from TIMESTAMPTZ, valid_to TIMESTAMPTZ NULL)
- **012_create_model_metrics.sql**: `model_metrics` (id UUID PK, model_name TEXT, cohort_key TEXT, metric_name TEXT, metric_value FLOAT, window_start TIMESTAMPTZ, window_end TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT now())
- **013_create_threshold_policies.sql**: `threshold_policies` (id UUID PK, cohort_key TEXT UNIQUE, alert_threshold FLOAT, case_threshold FLOAT, created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now())
- **014_create_rls_policies.sql**: RLS policies for all tables (enable RLS, create policies for authenticated read/write)
- **seed.sql**: Sample seed data for development (10-20 transactions, 5-10 wallets, sample heuristic results, sample scores, sample tags and entity links)

---

## Phase 3: Data Ingestion Pipeline

### Files to create:

- `backend/app/api/routes_ingest.py` - POST `/api/ingest/csv` (upload CSV), POST `/api/ingest/elliptic` (load Elliptic dataset)
- `backend/app/services/ingest_service.py` - Parse CSV, validate schema, normalize columns, deduplicate, create wallet records, time-sort, time-aware train/val/test split
- `backend/app/services/cleaning_service.py` - Handle missing values, type coercion, outlier capping
- `backend/app/schemas/transaction.py` - Pydantic models for transaction input/output
- `backend/app/schemas/wallet.py` - Pydantic models for wallet input/output
- `backend/app/schemas/network_case.py` - Pydantic models for network case
- `backend/app/schemas/explanation.py` - Pydantic models for explanation responses
- `backend/app/schemas/report.py` - Pydantic models for report
- `backend/app/repositories/transactions_repo.py` - Supabase CRUD for transactions table
- `backend/app/repositories/wallets_repo.py` - Supabase CRUD for wallets table
- `backend/app/repositories/scores_repo.py` - Supabase CRUD for transaction_scores and wallet_scores
- `backend/app/repositories/network_cases_repo.py` - Supabase CRUD for network_cases and junction table
- `backend/app/repositories/reports_repo.py` - Supabase CRUD for reports table

### Elliptic dataset loader:

- Download/load `elliptic_txs_features.csv`, `elliptic_txs_edgelist.csv`, `elliptic_txs_classes.csv`
- Map Elliptic columns to our schema (166 features -> our feature set, classes -> labels)
- Store in Supabase and local `data/` folder

### Elliptic dataset realities (must be accounted for)

The Elliptic Bitcoin Dataset is the primary training and evaluation dataset. Its properties directly constrain what the MVP can demonstrate:

- **Scale**: ~203,769 transactions across 49 time steps with ~234,355 directed edges.
- **Anonymized features**: All 166 features are opaque. 94 are transaction-local features (derived from transaction metadata) and 72 are 1-hop neighborhood aggregates computed by the dataset authors. There are no real wallet addresses, amounts, or timestamps — only integer node IDs and float feature vectors.
- **Label distribution**: class 1 = illicit (~4,545 nodes, ~2.2%), class 2 = licit (~42,019, ~20.6%), unknown (~157,205, ~77.2%). This extreme imbalance and large unknown fraction must be handled explicitly (see Phase 7b: Model Training Strategy).
- **Unknown labels are NOT "clean"**: During training, exclude unknowns from supervised loss. During inference, score them normally. Never treat unknown as a negative label.
- **Heuristic coverage on Elliptic**: Because features are anonymized, heuristics that require real-world signals (round-amount detection, time-delay analysis, exchange-proximity scoring, document metadata) cannot compute on raw Elliptic data. These heuristics should return `applicability=inapplicable_missing_data` for Elliptic records, which is correct behavior and validates the applicability system. Approximately 40-60% of the 185 heuristics will fire as inapplicable on Elliptic — this is expected and is surfaced transparently in the applicability summary.
- **Lens coverage on Elliptic**: The Graph Lens and Behavioral Lens carry the most weight on Elliptic because the anonymized feature vectors still encode structural and behavioral signals. The Temporal Lens can partially operate using the 49 time-step ordering. The Document and Off-ramp Lenses will operate in limited/reduced mode on Elliptic. This is an inherent limitation of the dataset, not of the architecture.
- **Custom CSV uploads**: Real transaction data with actual amounts, timestamps, and addresses will activate the full heuristic and lens coverage, demonstrating the system's full capability.

### Data contract and coverage tiers (required)

- Implement `backend/app/schemas/data_contract.py` with required/optional fields per lens:
  - Tier 0 (on-chain only): transactions, wallets, edges, tags
  - Tier 1 (on-chain + intelligence): + address tags, sanctions/exchange/ransomware lists
  - Tier 2 (full hybrid): + KYC/entity links + document events
- Implement `backend/app/services/data_availability_service.py` to emit per-record flags used in scoring.
- Every inference result must include:
  - `coverage_tier` (`tier0`, `tier1`, `tier2`)
  - `applicability_summary` (how many of 185 rules were applicable vs inapplicable)
  - `confidence_cap_reason` when key data is missing
- Label governance in ingestion:
  - store `label_source` (`elliptic`, `internal_sar`, `analyst_review`, `external_partner`)
  - store `label_timestamp`
  - block future-leaking labels during training split generation

---

## Phase 4: Graph Construction

### Files:

- `backend/app/services/graph_service.py` - Build directed temporal graph with NetworkX
  - Wallet graph (nodes=wallets, edges=transfers)
  - Transaction graph (nodes=txs, edges=flows)
  - Edge attrs: amount, token, timestamp, tx_hash
  - Node features: degree, amount stats, timing stats, neighborhood risk, centrality
- `backend/app/utils/graph_utils.py` - Helpers for k-hop expansion, subgraph extraction, motif detection
- `backend/app/ml/graph_features.py` - Compute graph-level features for each node (centrality scores, clustering coefficient, etc.)

---

## Phase 5: Feature Engineering

Three feature families, implemented in:

- `backend/app/ml/transaction_features.py` - **Transaction features**: amount, log(amount), fee, token type, time deltas, sender/receiver repeat counts, round-number indicator, burstiness, deviation from historical pattern
- `backend/app/ml/graph_features.py` - **Wallet/neighborhood features**: in/out degree, weighted volume, fan-in/fan-out ratio, unique counterparties, centrality, 1-hop/2-hop risky neighbor ratio, clustering coefficient, relay pattern score
- `backend/app/ml/subgraph_features.py` - **Subgraph/sequence features**: hop count in time window, fragmentation/reconvergence/peel-chain/circularity/synchronized transfer/velocity scores, entropy of fund splitting
- `backend/app/services/feature_service.py` - Orchestrator that calls all three and produces combined feature matrix

---

## Phase 6: Heuristic Engine (185 Typology Rules)

The heuristic engine is a structured rule system where each of the 185 known typologies from the Money Laundering Typologies Atlas gets its own detection function. Heuristics run **before** the ML models and produce a 185-dimensional score vector per transaction/wallet.

### Important: The 185 typologies are NOT exhaustive

The heuristics serve as a known-pattern floor. The lens models (Phase 7) are specifically designed to catch novel, unknown patterns that fall outside these 185. Every heuristic also feeds the models as input features, so the ML learns correlations between known signals.

### Heuristic output per transaction

Each heuristic returns:

- `triggered`: bool (did this pattern fire?)
- `confidence`: float 0.0-1.0 (how strongly does the evidence match?)
- `explanation`: string (plain-English reason, e.g. "14 sub-threshold transfers in 8 minutes")
- `lens_tags`: list of which lenses this heuristic is relevant to (for routing to lens models)
- `applicability`: enum (`applicable`, `inapplicable_missing_data`, `inapplicable_out_of_scope`)
- `evidence`: structured dict with values used by the rule (counts, amounts, time windows, counterparties)

### File structure: `backend/app/ml/heuristics/`

- `base.py` - Abstract `BaseHeuristic` class with `evaluate(tx, wallet, graph, features) -> HeuristicResult`
- `registry.py` - Central registry that maps heuristic ID (1-185) to class, name, environment, lens tags, data requirements, and supported coverage tiers. Also supports registering custom heuristics beyond 185 for extensibility.
- `runner.py` - Execute all registered heuristics for a transaction/wallet, produce the full 185-score vector + triggered list + explanations dict. Handles parallelism and error isolation.
- `completeness.py` - Validation contract: exactly 185 unique IDs, no overlap, no missing IDs, and environment mapping checksum.

### Heuristic modules by environment

**`traditional.py`** - Patterns 1-90 (adapted for on-chain analogs where applicable)

On-chain detectable examples:

- #1 Cash structuring / smurfing -> Detect repeated sub-threshold transfers, many branches, same beneficiary
- #5 Round-dollar deposits -> Detect repeated fixed-amount transfers
- #6 Rapid cash in then wire out -> Short holding periods, near-zero ending balance
- #17 Loan-back scheme -> Circular funding patterns
- #21 Nested personal accounts -> Frequent transfers among related parties
- #22 Funnel accounts -> Deposits from many sources, single receiver
- #23 Pass-through accounts -> Large gross flows, low average balance
- #26 Mirror transfers -> Near-simultaneous mirrored amounts
- #31 Dormant account activation -> Behavioral break from account history
- #35 ACH micro-splitting -> High count low-value transfers to related endpoints

Patterns requiring off-chain data (implemented as stubs that activate when external data is provided):

- #2 Cash-intensive front business, #28 Shell-company invoice payments, #41-58 Trade-based patterns, etc.

**`blockchain.py`** - Patterns 91-142 (fully implementable on-chain)

All have direct on-chain detection logic:

- #91 Peel chain - sequential transfers with residual balance pattern
- #92 Fan-out dispersal - high out-degree burst detection
- #93 Fan-in aggregation - high in-degree concentration
- #94 Layered hops across fresh wallets - young address age + one-time use
- #95 Dusting and mixed inflows - many small UTXOs
- #96 Self-transfer chain - common control heuristics
- #97 Address hopping around blacklists - repeated novel addresses
- #98 Time-delay layering - consistent timed gaps
- #99 Micro-splitting around thresholds - clustered near-threshold sizes
- #100 Consolidation after obfuscation - many relays converge
- #101-119 Change abuse, CoinJoin, mixers, privacy coins, bridges, DEX, etc.
- #120-142 DEX wash pathing, flash loans, NFT wash sales, L2 hopping, DAO abuse, etc.

**`hybrid.py`** - Patterns 143-155, 176-185

Cross-rail patterns where on-chain components are detectable:

- #143 KYC-borrowed account cashout - identity mismatch patterns
- #144 P2P exchange laundering - many counterparties
- #145 Crypto ATM cashout - frequent kiosk-linked patterns
- #176 Sanctions-evasion stablecoin corridor - exposure to sanctioned jurisdictions
- #179 Ransomware proceeds layering - exposure to known ransomware wallets
- #181 Darknet marketplace settlement - darknet cluster exposure
- #180 Pig-butchering scam treasury - known scam cluster interactions + fiat cashout behavior
- #184 Terror-finance micro-transfer webs - sparse but coordinated micro flows

**`ai_enabled.py`** - Patterns 156-175

Detect the behavioral signatures that AI-enabled laundering creates:

- #161 Automated transaction scheduling - clockwork timing, 24/7 consistency
- #162 Reinforcement-learned threshold avoidance - dynamic near-threshold behavior
- #163 Graph-aware route optimization - routing avoids screened clusters
- #164 Botnet wallet orchestration - synchronized activity across wallets
- #165 Autonomous cross-chain execution - complex multi-step flows with inhuman latency
- #172 Adversarial behavior against AML models - behavioral drift after review events
- #175 Multi-agent laundering workflow - distributed but coordinated indicators

### Typology ownership contract (airtight mapping)

- Traditional: 1-90
- Blockchain: 91-142
- Hybrid: 143-155 and 176-185
- AI-enabled: 156-175

No typology ID may belong to more than one environment module. Enforce this in CI via `completeness.py`.

### Common red flags (cross-cutting, Section 6 of atlas)

Implemented as 10 additional utility functions in `backend/app/ml/heuristics/common_red_flags.py` that are used as building blocks by many heuristics:

1. Fragmented transactions just below thresholds
2. Rapid movement with minimal retained balances
3. Circular or self-referential flows
4. Many-to-one or one-to-many patterns
5. Mismatch between documents and reality
6. High-risk counterparty exposure
7. New entities handling high-value flows instantly
8. Proxy/nominee/mule account patterns
9. Profits without coherent economics
10. Short jump from tainted inflows to cash-out

---

## Phase 7: 6 Lens Models (Layer A)

Each lens model receives two categories of input:

1. **Heuristic features**: The 185-score vector from Phase 6 (filtered to typologies tagged for this lens)
2. **Lens-specific engineered features**: From Phase 5 feature engineering

Each lens model is designed to catch **both** known patterns (boosted by heuristic signals) **and** novel patterns (learned from feature distributions).
Each lens also receives `data_availability_flags` so missing off-chain data does not masquerade as "clean" behavior.

### Lens-to-Heuristic Tag Mapping

Each of the 185 heuristics is tagged with one or more lenses it's relevant to. The lens model receives the subset of heuristic scores tagged for it, plus the full feature vector.

### Lens Execution Ordering

The 6 lenses are NOT fully independent. The Entity Lens consumes graph embeddings produced by the Graph Lens. Therefore the execution order during both training and inference is:

1. **Parallel group 1**: Behavioral, Graph, Temporal, Document, Off-ramp (these are independent of each other)
2. **Sequential after group 1**: Entity (requires graph embeddings from Graph Lens)

This dependency is intentional: entity resolution benefits from the learned structural representations. During training, the Graph Lens must be trained first so its embeddings can be used as Entity Lens input features.

### 1. Behavioral Lens Model

**Goal**: Detect economically unnecessary activity - too many hops, too many entities, sudden changes, circular flows, transfers without business purpose.

**Architecture**: XGBoost classifier + Autoencoder for novelty detection

**Inputs**:

- Heuristic scores tagged "behavioral" (e.g. #1 structuring, #5 round amounts, #17 loan-back, #23 pass-through, #96 self-transfer chains, #105 cross-wallet loops)
- Transaction features: amount, log(amount), fee, round-number indicator, burstiness, deviation from historical pattern
- Wallet features: total_in/total_out ratio, unique counterparties, average path depth

**Outputs**: behavioral_score (float), behavioral_anomaly_score (float from autoencoder)

**Files**:

- `backend/app/ml/lenses/behavioral_model.py` - Model definition + inference
- `backend/app/ml/training/train_behavioral.py` - Training script
- `models/behavioral/xgboost_behavioral.pkl`, `models/behavioral/autoencoder_behavioral.pt`

### 2. Graph Lens Model

**Goal**: Detect structural graph anomalies - fan-out, fan-in, relays, loops, clusters with synchronized timing, bridges between separate communities.

**Architecture**: GAT (Graph Attention Network) via PyTorch Geometric

**Inputs**:

- Heuristic scores tagged "graph" (e.g. #91 peel chain, #92 fan-out, #93 fan-in, #100 consolidation, #102 CoinJoin, #119 wallet cluster fragmentation)
- Graph features: in/out degree, weighted volume, fan-in/fan-out ratio, centrality scores, 1-hop/2-hop suspicious neighbor ratio, clustering coefficient, relay pattern score
- Node features from graph construction

**Outputs**: graph_score (float), node embeddings (for clustering and Entity Lens consumption)

**Files**:

- `backend/app/ml/lenses/graph_model.py` - GAT definition + inference
- `backend/app/ml/training/train_graph.py` - Training script
- Convert NetworkX to PyG Data objects
- 2-layer GAT with multi-head attention
- `models/graph/gat_model.pt`, `models/graph/graph_config.json`, `models/graph/node_mapping.json`, `models/graph/node_embeddings.npy`

### 3. Entity Lens Model

**Goal**: Resolve common control and identify cooperating wallet clusters using devices, IPs, KYC overlaps, shared gas sponsors, shared counterparties.

**Architecture**: Louvain/Leiden community detection + DBSCAN on graph embeddings + entity resolution classifier

**Inputs**:

- Heuristic scores tagged "entity" (e.g. #96 self-transfer, #110 gas sponsorship distancing, #119 wallet cluster fragmentation, #135 airdrop farming/sybil, #141 exchange mule ring, #164 botnet orchestration)
- Entity features: shared counterparty count, gas sponsor overlap, timing synchronization, device/IP overlap (when available)
- Graph embeddings from Graph Lens (dependency: Graph Lens must run first)

**Outputs**: entity_score (float), cluster_id, cluster_risk_score

Fallback policy: if KYC/device/IP signals are missing, model emits `entity_score` with downgraded confidence and sets `entity_lens_mode=limited`.

**Files**:

- `backend/app/ml/lenses/entity_model.py` - Model definition + inference
- `backend/app/ml/training/train_entity.py` - Training script
- `backend/app/services/clustering_service.py` - Louvain/Leiden + DBSCAN
- `models/entity/entity_classifier.pkl`

### 4. Temporal Lens Model

**Goal**: Detect temporal anomalies - bursts, repeat intervals, overnight processing, rapid movement, short holding periods, bot-like cadence.

**Architecture**: LSTM sequence model

**Inputs**:

- Heuristic scores tagged "temporal" (e.g. #6 rapid in/out, #31 dormant activation, #98 time-delay layering, #161 automated scheduling, #162 threshold avoidance, #165 autonomous execution)
- Temporal features per wallet: ordered transaction sequences with (amount, time_delta, direction, counterparty_risk)
- Subgraph features: velocity score, synchronized transfer score, burstiness

**Outputs**: temporal_score (float)

**Files**:

- `backend/app/ml/lenses/temporal_model.py` - LSTM definition + inference
- `backend/app/ml/training/train_temporal.py` - Training script
- `models/temporal/lstm_model.pt`

### 5. Document Lens Model

**Goal**: Compare metadata, invoices, contracts, source-of-funds narratives against external facts. In blockchain context: detect mismatches between stated purpose and on-chain behavior, flag synthetic/AI-generated document indicators.

**Architecture**: XGBoost classifier + optional NLP for narrative analysis

**Inputs**:

- Heuristic scores tagged "document" (e.g. #28 shell-company invoices, #41-55 trade-based patterns, #156 synthetic identity, #160 AI-written invoices, #168 document laundering via image models, #171 synthetic beneficial-owner narratives)
- Document features: metadata consistency scores, narrative complexity metrics, template repetition detection
- Note: This lens activates fully when off-chain document data is provided. With on-chain only data, it operates in reduced mode using transaction metadata patterns.
- In reduced mode, cap document contribution in the meta-model and expose `document_lens_mode=limited` in explanations.

**Outputs**: document_score (float)

**Files**:

- `backend/app/ml/lenses/document_model.py` - Model definition + inference
- `backend/app/ml/training/train_document.py` - Training script
- `models/document/document_classifier.pkl`

### 6. Off-ramp Lens Model

**Goal**: Detect conversion signals near exchanges, OTC desks, property, luxury goods, payroll, business revenue. The highest-value signals often appear near the point of integration.

**Architecture**: XGBoost classifier focused on exit/conversion patterns

**Inputs**:

- Heuristic scores tagged "offramp" (e.g. #93 fan-in aggregation, #106 OTC broker layering, #120 tokenized gift-card cashout, #141 exchange mule ring, #143-155 hybrid off-ramp patterns, #145 crypto ATM cashout, #146 prepaid debit off-ramp)
- Off-ramp features: proximity to known exchange addresses, cash-out pattern scores, conversion timing, exit concentration, exposure to tagged entities, inbound suspicious score

**Outputs**: offramp_score (float)

**Files**:

- `backend/app/ml/lenses/offramp_model.py` - Model definition + inference
- `backend/app/ml/training/train_offramp.py` - Training script
- `models/offramp/offramp_classifier.pkl`

### Lens-to-Typology Coverage Matrix

Each typology maps to one or more lenses. Examples:

- #91 Peel chain -> Graph + Temporal + Behavioral
- #92 Fan-out dispersal -> Graph + Temporal
- #107 Bridge hop obfuscation -> Graph + Off-ramp
- #132 NFT wash sale -> Behavioral + Entity + Off-ramp
- #161 Automated scheduling -> Temporal + Behavioral
- #164 Botnet orchestration -> Entity + Temporal + Graph
- #176 Sanctions stablecoin corridor -> Off-ramp + Graph + Entity

---

## Phase 7b: Model Training Strategy

This section covers how every model in the pipeline is trained. Training is a prerequisite for inference (Phase 9) and must be completed before the system can score live data.

### Training Data Preparation

- **Primary dataset**: Elliptic Bitcoin Dataset (203,769 transactions, 234,355 edges, 49 time steps)
- **Labeled subset**: Only the ~46,564 labeled records (illicit + licit) enter the supervised training set. The ~157,205 unknown records are excluded from supervised loss but are used for unsupervised components (autoencoder reconstruction, community detection, graph construction).
- **Time-aware split**: Use Elliptic's built-in temporal structure to prevent future leakage:
  - Training: time steps 1-34 (~70% of timeline)
  - Validation: time steps 35-42 (~16% of timeline)
  - Test: time steps 43-49 (~14% of timeline)
- **No entity leakage**: Wallets that appear in both training and test windows must have their test-window labels masked during training. This is enforced in `ingest_service.py` during split generation.
- **Feature computation on training data**: Heuristic scores are computed on training data using only information available at that time step. No future features may leak into the heuristic computation (e.g., "total lifetime volume" must be computed up to the current time step only).

### Class Imbalance Handling

AML data is severely imbalanced (~2.2% illicit in Elliptic, often <1% in production). Every supervised model must account for this:

- **XGBoost models** (Behavioral, Document, Off-ramp, Meta): Set `scale_pos_weight = count(licit) / count(illicit)` to rebalance the loss function. On Elliptic training data, this is approximately 9:1 within labeled records. Alternatively, use `sample_weight` with inverse-frequency weights per class if per-cohort rebalancing is needed.
- **GAT (Graph Lens)**: Use weighted cross-entropy loss with class weights inversely proportional to label frequency. If standard weighting under-performs on validation PR-AUC, apply focal loss (gamma=2, alpha=0.75) to further down-weight easy negatives.
- **LSTM (Temporal Lens)**: Same weighted cross-entropy approach. Additionally, oversample illicit sequences during batch construction so each mini-batch contains at least ~20% positive examples, preventing gradient domination by the majority class.
- **Autoencoder (Behavioral anomaly)**: Train exclusively on licit transactions. At inference, reconstruction error on illicit transactions will be systematically higher because the autoencoder has only learned to reconstruct normal behavior. This produces the anomaly score without needing class labels at inference time.
- **Community detection (Entity Lens)**: Louvain/Leiden is unsupervised — no labels needed. The downstream entity classifier uses the same `scale_pos_weight` strategy as the other XGBoost models.
- **Meta-model**: Same `scale_pos_weight` on the stacked features. Additionally, apply Platt scaling or isotonic calibration on the validation set so the final risk probabilities are well-calibrated (critical for threshold policies to work correctly across cohorts).

### Per-Model Training Procedures

**Behavioral Lens** (`backend/app/ml/training/train_behavioral.py`):

1. Assemble input: transaction features + heuristic scores tagged "behavioral" + data availability flags
2. XGBoost classifier: `scale_pos_weight`, `max_depth=6`, `learning_rate=0.05`, `n_estimators=500`, early stopping on validation PR-AUC (patience=50 rounds)
3. Autoencoder: train on licit-only transactions. Architecture: 3-layer encoder (input_dim→128→64→32) and symmetric decoder (32→64→128→input_dim). MSE reconstruction loss. Adam optimizer lr=1e-3, 100 epochs, early stopping on validation reconstruction error (patience=15)
4. Output artifacts: `xgboost_behavioral.pkl`, `autoencoder_behavioral.pt`

**Graph Lens** (`backend/app/ml/training/train_graph.py`):

1. Convert NetworkX graph to PyG Data object. Node feature vector = graph features + heuristic scores tagged "graph". Edge index from edge list.
2. GAT: 2-layer GAT, 8 attention heads per layer, hidden_dim=64, dropout=0.3, weighted cross-entropy loss
3. Train: Adam optimizer lr=5e-4, 200 epochs, early stopping on validation F1 (patience=30)
4. After training, run a forward pass on all nodes and extract the penultimate-layer embeddings (before the classification head). Persist these as `node_embeddings.npy` for Entity Lens consumption.
5. Output artifacts: `gat_model.pt`, `graph_config.json`, `node_mapping.json`, `node_embeddings.npy`

**Entity Lens** (`backend/app/ml/training/train_entity.py`):

1. Run Louvain/Leiden community detection on the full graph (unsupervised, uses all nodes including unknowns)
2. Load graph embeddings from `node_embeddings.npy` (produced by Graph Lens training — dependency)
3. Compute cluster-level features: cluster size, internal edge density, mean node embedding distance, shared counterparty count, timing synchronization score
4. Run DBSCAN on graph embeddings (eps tuned on validation silhouette score) to identify dense suspicious clusters
5. Train XGBoost entity classifier: cluster features + per-node heuristic scores tagged "entity" → binary risk label. A cluster is labeled suspicious if ≥ 30% of its labeled members are illicit (threshold tunable).
6. Output artifacts: `entity_classifier.pkl`, `community_assignments.json`

**Temporal Lens** (`backend/app/ml/training/train_temporal.py`):

1. Build per-wallet ordered transaction sequences. Each time step in the sequence = (feature vector + heuristic scores tagged "temporal"). Pad/truncate to fixed length (50 most recent transactions per wallet).
2. LSTM: 2-layer, hidden_dim=128, dropout=0.2, followed by a fully connected classification head (128→64→1, sigmoid)
3. Train: Adam optimizer lr=1e-3, weighted cross-entropy with oversampled illicit sequences, 100 epochs, early stopping on validation PR-AUC (patience=20)
4. Output artifacts: `lstm_model.pt`

**Document Lens** (`backend/app/ml/training/train_document.py`):

1. On Elliptic (no document data available): train in reduced mode using only heuristic scores tagged "document" + transaction metadata features. This lens will have minimal discriminative power on Elliptic — expected behavior.
2. On custom CSV with document_events data: train XGBoost on metadata consistency scores, narrative complexity features, template repetition detection signals
3. Output artifacts: `document_classifier.pkl`

**Off-ramp Lens** (`backend/app/ml/training/train_offramp.py`):

1. Assemble input: off-ramp features (proximity to tagged exchange/OTC addresses, exit concentration, conversion timing, inbound suspicious score) + heuristic scores tagged "offramp"
2. XGBoost classifier with same hyperparameter strategy as Behavioral Lens
3. Output artifacts: `offramp_classifier.pkl`

**Meta-Model** (`backend/app/ml/training/train_meta.py`):

1. Requires all 6 lens models to be trained first. Run inference on validation set to produce lens scores.
2. Train on stacked features (see Phase 8 for full input spec)
3. Apply calibration (Platt scaling or isotonic — choose whichever produces lower ECE on validation)
4. Learn per-cohort thresholds and write to `threshold_config.json`
5. Output artifacts: `meta_model.pkl`, `threshold_config.json`, `metrics_report.json`, `feature_importance.json`

### Hyperparameter Tuning

- Use Optuna with TPE sampler on the validation set (time steps 35-42). Budget: 50 trials per model for MVP.
- Key search spaces per model:
  - XGBoost (all): `max_depth` [4,8], `learning_rate` [0.01,0.1] log-uniform, `n_estimators` [200,1000], `min_child_weight` [1,10], `subsample` [0.7,1.0], `colsample_bytree` [0.6,1.0]
  - GAT: `num_heads` {4,8}, `hidden_dim` {32,64,128}, `dropout` [0.1,0.5], `learning_rate` [1e-4,1e-3] log-uniform
  - LSTM: `hidden_dim` {64,128,256}, `num_layers` {1,2,3}, `dropout` [0.1,0.4], `sequence_length` {20,50,100}
  - Autoencoder: `latent_dim` {16,32,64}, `learning_rate` [1e-4,1e-3] log-uniform
- **Primary tuning metric**: PR-AUC (preferred over ROC-AUC because ROC-AUC can be misleadingly optimistic on imbalanced data). **Secondary**: Precision@100 (top-100 analyst queue quality).
- All tuning respects the time-aware split: validation data is strictly from future time steps relative to training.

### Training Orchestration

The `Makefile` target `make train` runs the full training pipeline in dependency order:

1. `make features` — Feature engineering on training data (Phase 5)
2. `make heuristics-train` — Heuristic scoring on training data (Phase 6)
3. `make train-lenses-parallel` — Behavioral, Graph, Temporal, Document, Off-ramp (parallel, no inter-dependencies)
4. `make train-entity` — Entity lens (after Graph lens completes, needs `node_embeddings.npy`)
5. `make train-meta` — Meta-model (after all 6 lenses complete, needs lens scores on validation set)

Each training script:

- Logs all metrics (PR-AUC, F1, Precision@K, calibration error) to the `model_metrics` table
- Saves model artifacts to the `models/` directory
- Writes a training manifest (hyperparameters used, data split stats, runtime) to `models/artifacts/training_manifest.json`
- Is idempotent: re-running overwrites previous artifacts only after validation gates pass

---

## Phase 8: Meta-Model (Layer B)

- `backend/app/ml/training/train_meta.py` - XGBoost meta-learner
  - Inputs (19 features):
    - 6 lens scores: behavioral_score, graph_score, entity_score, temporal_score, document_score, offramp_score
    - 1 anomaly signal: behavioral_anomaly_score
    - Heuristic aggregates: total_triggered_count, max_heuristic_confidence, behavioral_heuristic_mean, graph_heuristic_mean, entity_heuristic_mean, temporal_heuristic_mean, document_heuristic_mean, offramp_heuristic_mean
    - Applicability aggregates: applicable_rule_count, inapplicable_rule_count
    - Data availability flags: has_entity_intel, has_document_intel
  - Class imbalance: use `scale_pos_weight` consistent with the training label distribution
  - Output: final risk probability + predicted label
  - Calibration with Platt scaling or isotonic calibration (choose best on validation by ECE)
  - Threshold policy learned per cohort (chain, asset, customer segment) and written to threshold policy artifact/table
  - Save artifacts:
    - `models/meta/meta_model.pkl` - trained meta-model
    - `models/artifacts/threshold_config.json` - risk threshold configuration
    - `models/artifacts/metrics_report.json` - evaluation metrics from training
    - `models/artifacts/feature_importance.json` - SHAP / XGBoost feature importances

---

## Phase 9: Inference Pipeline + Case Assembly

- `backend/app/ml/infer_pipeline.py` - End-to-end scoring with strict ordering:
  1. Load all models + heuristic registry
  2. Compute features for new data + data availability flags
  3. **Step 1**: Run all 185 heuristics -> produce heuristic vector, triggered list, explanations
  4. **Step 2**: Run lens models in dependency order: Behavioral, Graph, Temporal, Document, Off-ramp (parallel) then Entity (needs graph embeddings)
  5. **Step 3**: Stack lens outputs into meta-model
  6. **Step 4**: Apply threshold policy by cohort (`threshold_policies` table, fallback to artifact, final fallback env value)
  7. Output: transaction risk, wallet risk, cluster risk, full heuristic report, coverage tier, uncertainty flags

- `backend/app/services/scoring_service.py` - Orchestrate inference, write heuristic results + scores to Supabase
- `backend/app/services/investigation_service.py` - Network case assembly:
  - Expand k-hops from high-risk nodes
  - Search shared neighbors, detect motifs
  - Identify cluster boundaries
  - Generate "case" record with attached heuristic evidence + explicit rationale for why policy threshold was crossed

- `backend/app/services/explanation_service.py` - For each case:
  - Which heuristics fired and with what confidence
  - Which lenses contributed most to the score
  - Suspicious pattern type (mapped to typology atlas categories)
  - Likely laundering stage (placement / layering / integration)
  - Plain-English explanation using template system + SHAP values
- `backend/app/ml/explainers.py` - SHAP explanations for XGBoost models (behavioral, off-ramp, meta)

---

## Phase 10: API Routes

All routes in `backend/app/api/`:

- **routes_ingest.py**: `POST /api/ingest/csv`, `POST /api/ingest/elliptic`
- **routes_transactions.py**: `GET /api/transactions` (paginated, filterable), `GET /api/transactions/{id}`, `POST /api/transactions/score`
- **routes_wallets.py**: `GET /api/wallets`, `GET /api/wallets/{address}`, `GET /api/wallets/{address}/graph`
- **routes_heuristics.py** (new): `GET /api/heuristics/registry` (list all 185 with metadata), `GET /api/heuristics/{transaction_id}` (heuristic results for a tx), `GET /api/heuristics/stats` (aggregate stats: most-triggered heuristics, distribution by environment/lens)
- **routes_networks.py**: `GET /api/networks`, `GET /api/networks/{id}`, `GET /api/networks/{id}/graph`, `POST /api/networks/detect`
- **routes_explanations.py**: `GET /api/explanations/{transaction_id}`, `GET /api/explanations/case/{case_id}`
- **routes_reports.py**: `GET /api/reports`, `POST /api/reports/generate/{case_id}`, `GET /api/reports/{id}/download`
- **routes_metrics.py** (new): `GET /api/metrics/typology`, `GET /api/metrics/cohort`, `GET /api/metrics/drift`
- **routes_policies.py** (new): `GET /api/policies/thresholds`, `PUT /api/policies/thresholds/{cohort_key}`

Pydantic schemas in `backend/app/schemas/` for all request/response models. Add `heuristic.py` schema for heuristic results.
Repository layer in `backend/app/repositories/` for Supabase queries. Add `heuristics_repo.py`.

---

## Phase 11: Frontend Dashboard

### Shared Components (`frontend/src/components/`)

- `RiskSummaryCards.tsx` - Stat cards (suspicious tx count, wallets, cases, confidence)
- `TransactionTable.tsx` - Sortable, filterable table with risk badges + heuristic trigger count column
- `NetworkGraph.tsx` - Cytoscape.js graph component (color by risk, edge thickness by amount)
- `FlowTimeline.tsx` - Plotly timeline of fund movement
- `ExplanationPanel.tsx` - Collapsible panel showing plain-English reasons, heuristic evidence, lens contributions
- `HeuristicBadges.tsx` (new) - Display which of the 185 heuristics triggered for a transaction, grouped by environment (Traditional/Blockchain/Hybrid/AI-enabled) and tagged by lens
- `LensRadarChart.tsx` (new) - Radar/spider chart showing the 6 lens scores for a transaction or wallet
- `FiltersBar.tsx` - Date range, risk threshold, typology filter, environment filter, lens filter
- `WalletDetailPanel.tsx` - Wallet summary sidebar
- `CaseReportCard.tsx` - Case summary card with typology atlas references

### Pages (`frontend/src/pages/`)

- **DashboardPage.tsx**: Overview stats, top triggered heuristics chart, top risk typologies, lens score distribution, recent suspicious activity feed
- **TransactionsPage.tsx**: Full transaction table, risk score column, 6 lens scores, heuristic trigger count, click to expand heuristic detail + SHAP explanation
- **WalletPage.tsx**: Wallet detail view, in/out graph mini-view, related suspicious paths, entity cluster membership
- **NetworkCasesPage.tsx**: List of detected cases, typology tags (linked to atlas), amount involved, heuristic evidence summary, click to expand
- **FlowExplorerPage.tsx**: Full Cytoscape.js interactive graph, expand nodes, time slider, path trace, risk heatmap overlay, heuristic overlay mode (color nodes by which heuristics triggered)
- **ReportsPage.tsx**: Generated case reports, download PDF, summary for presentation, heuristic evidence appendix

### API Layer (`frontend/src/api/`)

- `client.ts`, `transactions.ts`, `wallets.ts`, `networks.ts`, `reports.ts`, `heuristics.ts` (new)

### Types (`frontend/src/types/`)

- `transaction.ts`, `wallet.ts`, `network.ts`, `report.ts`, `heuristic.ts` (new)

### Hooks (`frontend/src/hooks/`)

- `useTransactions.ts`, `useWallet.ts`, `useNetworkCases.ts`, `useHeuristics.ts` (new)

---

## Phase 12: Integration, Metrics, and Polish

### Metrics (`backend/app/utils/metrics.py`)

Classification metrics:

- Precision, Recall, F1, PR-AUC, ROC-AUC, confusion matrix, balanced accuracy, MCC
- Precision/Recall with confidence intervals (bootstrap)

Ranking metrics:

- Precision@K, Recall@K, Top-K hit rate

Graph/case metrics:

- Suspicious cluster purity, suspicious cluster recall, path detection success, mean suspicious path length, time-to-detection, false positives per 1,000 transactions

Investigation usefulness metrics (for demo reporting):

- Number of risky cases surfaced, average explanation coverage, reduction in analyst search space, percentage of cases with traceable source-to-destination path

Governance metrics (required for production posture):

- Typology-level recall and precision table (all 185 IDs; explicit N/A when inapplicable)
- Segment/cohort metrics (by chain, asset type, customer type, jurisdiction)
- Calibration error (ECE/Brier) and threshold stability by cohort
- Drift metrics (PSI/feature drift, label drift) with alert thresholds

Performance gates (must pass before promoting models):

- High-priority typology recall floor met
- False positives per 1,000 transactions below cohort policy ceiling
- Calibration error below target
- No critical regression against previous champion model

Hackathon emphasis: Precision, Recall, F1, PR-AUC, Precision@K, and measurable time-to-investigate improvement with explicit uncertainty disclosure.

### Services

- `backend/app/services/report_service.py` - Generate downloadable case reports (JSON + optional PDF)
- `backend/app/services/storage_service.py` - Upload/download from Supabase storage buckets (raw-datasets, reports, model-artifacts)

### Backend tests (`backend/tests/`)

- `test_ingest.py` - CSV parsing, schema validation, deduplication
- `test_features.py` - Feature computation correctness
- `test_graph.py` - Graph construction, k-hop expansion
- `test_heuristics.py` - All 185 heuristic rules trigger correctly on known patterns, registry completeness, runner error isolation, no duplicated/missing typology IDs
- `test_lenses.py` - Each lens model produces valid scores, accepts heuristic input correctly
- `test_scoring.py` - Full pipeline inference (heuristics -> lenses -> meta), meta-model stacking
- `test_api.py` - API endpoint integration tests including heuristic endpoints
- `test_data_contract.py` - Coverage tier assignment and missing-data applicability behavior
- `test_threshold_policy.py` - Policy precedence (`threshold_policies` -> artifact -> fallback env)
- `test_leakage.py` - Time-split integrity, no future feature leakage, no target leakage in engineered features
- `test_eval_protocol.py` - Out-of-time and out-of-entity validation pipeline correctness
- `test_drift_monitoring.py` - Drift detection and alerting path
- `test_training.py` - Training scripts run end-to-end on small sample data, produce valid artifacts, respect dependency ordering

### Integration

- Connect all frontend pages to live API endpoints
- End-to-end test: CSV upload -> scoring -> case generation -> visualization
- Verify Supabase storage bucket operations (upload raw CSV, download report)
- Champion/challenger run: compare current production model vs new candidate on the same holdout and produce promotion decision report

---

## Key Technical Decisions

- **Backend framework**: FastAPI (async, good for ML serving)
- **Frontend**: React 18 + Vite + TypeScript + Tailwind CSS v4
- **Graph viz**: Cytoscape.js via `react-cytoscapejs`
- **Charts**: Plotly.js via `react-plotly.js`
- **Database**: Supabase PostgreSQL (existing project)
- **Graph library**: NetworkX (Python) for construction, PyTorch Geometric for GAT
- **ML stack**: XGBoost (behavioral + offramp + document + meta), PyTorch (GAT for graph lens, LSTM for temporal lens, Autoencoder for behavioral anomaly), scikit-learn (preprocessing, calibration)
- **Community detection**: python-louvain + leidenalg (entity lens)
- **Hyperparameter tuning**: Optuna with TPE sampler, PR-AUC as primary metric
- **Class imbalance**: scale_pos_weight (XGBoost), weighted cross-entropy (GAT/LSTM), licit-only training (autoencoder), focal loss fallback
- **Heuristic engine**: 185 typology-specific rules from Money Laundering Typologies Atlas, extensible registry
- **Explainability**: SHAP for XGBoost models, template-based for heuristics, lens contribution breakdown
- **Detection target**: risk-ranked suspicious activity, not exhaustive laundering capture
- **Threshold governance**: cohort-based threshold policies with explicit fallback chain and audit trail
- **Validation protocol**: out-of-time + out-of-entity evaluation, typology-level scorecards, drift monitoring
- **Dataset**: Elliptic Bitcoin Dataset (anonymized features, ~2% illicit, 49 time steps) + custom CSV support

---

## Complete File Manifest

Total files to create: ~125+

**Backend** (75+ files):

- `backend/app/`: main.py, config.py, supabase_client.py, dependencies.py
- `backend/app/api/`: routes_ingest.py, routes_transactions.py, routes_wallets.py, routes_heuristics.py, routes_networks.py, routes_explanations.py, routes_reports.py, routes_metrics.py, routes_policies.py
- `backend/app/schemas/`: transaction.py, wallet.py, heuristic.py, network_case.py, explanation.py, report.py, data_contract.py
- `backend/app/services/`: ingest_service.py, cleaning_service.py, feature_service.py, graph_service.py, scoring_service.py, explanation_service.py, clustering_service.py, investigation_service.py, report_service.py, storage_service.py, data_availability_service.py
- `backend/app/repositories/`: transactions_repo.py, wallets_repo.py, heuristics_repo.py, scores_repo.py, network_cases_repo.py, reports_repo.py
- `backend/app/ml/heuristics/`: base.py, registry.py, runner.py, completeness.py, traditional.py, blockchain.py, hybrid.py, ai_enabled.py, common_red_flags.py
- `backend/app/ml/lenses/`: behavioral_model.py, graph_model.py, entity_model.py, temporal_model.py, document_model.py, offramp_model.py
- `backend/app/ml/training/`: train_behavioral.py, train_graph.py, train_entity.py, train_temporal.py, train_document.py, train_offramp.py, train_meta.py
- `backend/app/ml/`: infer_pipeline.py, graph_features.py, transaction_features.py, subgraph_features.py, explainers.py
- `backend/app/utils/`: logger.py, time_utils.py, graph_utils.py, file_utils.py, metrics.py
- `backend/tests/`: test_ingest.py, test_features.py, test_graph.py, test_heuristics.py, test_scoring.py, test_api.py, test_lenses.py, test_data_contract.py, test_threshold_policy.py, test_leakage.py, test_eval_protocol.py, test_drift_monitoring.py, test_training.py
- `backend/`: requirements.txt, Dockerfile, .env.example

**Frontend** (30+ files):

- `frontend/src/`: main.tsx, App.tsx
- `frontend/src/pages/`: DashboardPage.tsx, TransactionsPage.tsx, WalletPage.tsx, NetworkCasesPage.tsx, FlowExplorerPage.tsx, ReportsPage.tsx
- `frontend/src/components/`: RiskSummaryCards.tsx, TransactionTable.tsx, WalletDetailPanel.tsx, NetworkGraph.tsx, FlowTimeline.tsx, ExplanationPanel.tsx, HeuristicBadges.tsx, LensRadarChart.tsx, FiltersBar.tsx, CaseReportCard.tsx
- `frontend/src/api/`: client.ts, transactions.ts, wallets.ts, heuristics.ts, networks.ts, reports.ts, supabase.ts
- `frontend/src/types/`: transaction.ts, wallet.ts, heuristic.ts, network.ts, report.ts
- `frontend/src/hooks/`: useTransactions.ts, useWallet.ts, useNetworkCases.ts, useHeuristics.ts
- `frontend/src/utils/`: formatters.ts, graphTransform.ts
- `frontend/`: package.json, vite.config.ts, tailwind.config.js, tsconfig.json

**Supabase** (16 files):

- `supabase/`: config.toml, seed.sql
- `supabase/migrations/`: 001 through 014 .sql files

**Model directories** (with .gitkeep):

- `models/behavioral/`, `models/graph/`, `models/entity/`, `models/temporal/`, `models/document/`, `models/offramp/`, `models/meta/`, `models/artifacts/`

**Root** (5 files):

- docker-compose.yml, .gitignore, Makefile, README.md
