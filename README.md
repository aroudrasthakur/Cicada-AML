# Aegis AML

**AI-Powered Blockchain Laundering Detection and Investigation Dashboard**

A hybrid demo platform that scores transactions with a **heuristics-first, models-second** pipeline: **185 typology rules** (Money Laundering Typologies Atlas–style IDs) run before **six lens models** (behavioral, graph, entity, temporal, document, off-ramp) and an **XGBoost meta-learner**. The UI surfaces risk, heuristic triggers, lens breakdowns, graphs (Cytoscape), and timelines (Plotly).

---

## What’s in this repo

| Area | Technology |
|------|------------|
| API | FastAPI (`backend/app/main.py`), CORS enabled |
| Database | **Supabase Postgres only** — tables via SQL migrations under `supabase/migrations/`. **No Supabase Storage**; CSVs, reports JSON, and model files live on disk (`data/`, `models/`). |
| Frontend | React 19, Vite 6, TypeScript, Tailwind CSS v4, React Router 7 |
| ML / graph | Python 3.11+, XGBoost, PyTorch, PyTorch Geometric (GAT), NetworkX, heuristics in `backend/app/ml/heuristics/` |
| Viz | `react-cytoscapejs`, `react-plotly.js` |

**Backend route prefixes** (all under `http://localhost:8000`):

- `/health` — liveness  
- `/api/ingest` — CSV / Elliptic ingestion  
- `/api/transactions`, `/api/wallets`, `/api/heuristics`, `/api/networks`, `/api/explanations`, `/api/reports`, `/api/metrics`, `/api/policies`

The Vite dev server proxies **`/api` → `http://localhost:8000`** (see `frontend/vite.config.ts`), so the browser can call `/api/...` on port **5173** without extra CORS setup.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** and npm
- A **Supabase project** (for Postgres): Project URL, **anon** key, and **service role** key (backend uses the service role for server-side writes)
- **Git**
- Optional: **Docker** + Docker Compose (see below)

On Windows, use **PowerShell** or **Git Bash**. The root `Makefile` uses Unix-style `cd … &&` commands; if you don’t have `make`, run the equivalent commands manually (see [Run the API](#run-the-api)).

---

## 1. Clone and install dependencies

```bash
git clone <your-fork-url> Aegis-AML
cd Aegis-AML
```

### Backend

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cd ..
```

PyTorch / PyTorch Geometric can be environment-specific. If `pip install -r requirements.txt` fails on the graph stack, install PyTorch from the [official guide](https://pytorch.org/get-started/locally/), then install `torch-geometric` per [PyG docs](https://pytorch-geometric.readthedocs.io/en/latest/install/installation.html).

### Frontend

```bash
cd frontend
npm install
cd ..
```

---

## 2. Configure environment variables

Copy the example file and fill in real values:

```bash
cp backend/.env.example backend/.env
```

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Anon key (optional for server; some code paths may expect it) |
| `SUPABASE_SERVICE_ROLE_KEY` | **Required for backend** inserts/updates via `supabase-py` |
| `MODEL_DIR`, `*_MODEL_PATH`, `THRESHOLD_POLICY_PATH` | Where trained artifacts are loaded during inference (defaults under `./models` relative to **`backend/`** when you run uvicorn from `backend/`) |
| `FALLBACK_RISK_THRESHOLD`, `NETWORK_HOPS` | Scoring / graph exploration defaults |

**Frontend (optional):** if pages use the Supabase JS client directly, create `frontend/.env.local`:

```env
VITE_SUPABASE_URL=https://xxxx.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

API calls from the UI already go through **`/api`** → FastAPI; Supabase in the browser is only needed if you wire real-time or direct table access.

---

## 3. Database: apply migrations and seed

1. In the Supabase dashboard (**SQL Editor**), run each file in order:

   `supabase/migrations/001_create_transactions.sql`  
   → … → `014_create_rls_policies.sql`

2. Run `supabase/seed.sql` for demo rows (transactions, wallets, sample scores, etc.).

Alternatively, use the [Supabase CLI](https://supabase.com/docs/guides/cli):

```bash
supabase link --project-ref <your-project-ref>
supabase db push   # if your local folder is wired as migration source
```

**RLS:** Migration `014` enables RLS. For a quick local demo you may need policies aligned with how you authenticate (e.g. service role bypasses RLS when using the backend; browser clients using the anon key need matching policies).

---

## 4. Run the API

From the **`backend`** directory (so `app` imports and `./models` paths resolve correctly):

```bash
cd backend
.\.venv\Scripts\activate   # Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or from the repo root with Make (Unix-like shell):

```bash
make dev-backend
```

Verify: open [http://localhost:8000/health](http://localhost:8000/health) — expect `{"status":"ok"}`.

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 5. Run the frontend

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The app talks to the API via the **`/api` proxy** to port 8000.

---

## 6. Load data (demo)

**Minimum CSV columns** for `POST /api/ingest/csv`:

`transaction_id`, `sender_wallet`, `receiver_wallet`, `amount`, `timestamp`

Optional: `tx_hash`, `asset_type`, `chain_id`, `fee`, `label`, `label_source`

**Elliptic Bitcoin Dataset:** place the three CSVs (`elliptic_txs_features.csv`, `elliptic_txs_edgelist.csv`, `elliptic_txs_classes.csv`) in a folder whose default path is **`data/external` relative to the process working directory**. If you start uvicorn from **`backend/`**, use `backend/data/external/`. With **Docker Compose**, `./data` from the repo root is mounted at `/app/data`, so use **`data/external/`** at the repo root on the host. Call `POST /api/ingest/elliptic` with optional query param `data_dir` (default `data/external`).

Ingestion persists to **Postgres** via repositories in `backend/app/repositories/` — not to object storage.

---

## 7. Training models (advanced)

Training scripts live in `backend/app/ml/training/`. They expect prepared CSVs under **`backend/data/processed/`** by default (`--data-dir` to override):

| Script | Typical inputs |
|--------|----------------|
| `train_behavioral.py` | `train_features.csv` (+ optional `val_features.csv`), column **`label`** for supervised learning |
| `train_graph.py` | `edges.csv`, `node_labels.csv` |
| `train_entity.py` | same edge/label inputs + **`models/graph/node_embeddings.npy`** from graph training |
| `train_temporal.py` | `train_features.csv`, optional `wallet_labels.csv` |
| `train_document.py` | `document_features.csv` or fallback `train_features.csv` |
| `train_offramp.py` | `offramp_features.csv` or `train_features.csv` |
| `train_meta.py` | `meta_features.csv` (stacked lens + heuristic aggregates) |

**Suggested order:** graph → entity → (behavioral, temporal, document, off-ramp in parallel) → build `meta_features.csv` from lens outputs → meta.

Example (from `backend/`):

```bash
python -m app.ml.training.train_graph --data-dir data/processed
python -m app.ml.training.train_entity --data-dir data/processed
python -m app.ml.training.train_behavioral --data-dir data/processed
# … etc.
```

The root **`make train`** target is a **placeholder orchestration**: the feature modules are libraries (no CLI that writes `train_features.csv`), and the heuristics runner has no `--mode train` entry point. For a full pipeline you still need an ETL step (notebook or script) that builds the CSVs above from ingested transactions.

Artifacts are written under **`backend/models/`** (e.g. `behavioral/`, `graph/`, `meta/`, `artifacts/`).

---

## 8. Tests and lint

From repo root:

```bash
make test
make lint
```

Or manually:

```bash
cd backend
pytest tests/ -v
ruff check .
```

```bash
cd frontend
npm run lint
```

---

## 9. Docker Compose (optional)

```bash
docker compose up --build
```

Ensure `backend/.env` is present and mounted; compose maps `./models` and `./data` into the backend container for local artifacts and datasets.

---

## Repository layout (high level)

```text
Aegis-AML/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── ml/               # heuristics/, lenses/, training/, infer_pipeline, features
│   │   ├── repositories/     # Supabase table access
│   │   ├── schemas/          # Pydantic models
│   │   ├── services/         # ingest, graph, scoring, explanations, …
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/                  # pages, components, api, hooks, types
├── supabase/
│   ├── migrations/
│   └── seed.sql
├── data/                     # raw, processed, external (gitignored content)
├── models/                   # trained artifacts (gitignored binaries)
├── docker-compose.yml
└── Makefile
```

---

## License / demo notice

This project is intended for **research and demonstration**. Risk scores are not legal or compliance advice; tune and validate any production deployment separately.
