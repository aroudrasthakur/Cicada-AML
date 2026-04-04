.PHONY: dev dev-backend dev-frontend install install-backend install-frontend \
       train features heuristics-train train-lenses-parallel train-entity train-meta \
       ingest test lint clean

# ── Development ──────────────────────────────────────────────────────────────

dev: dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# ── Training pipeline (dependency order) ─────────────────────────────────────

train: features heuristics-train train-lenses-parallel train-entity train-meta

features:
	cd backend && python -m app.ml.transaction_features
	cd backend && python -m app.ml.graph_features
	cd backend && python -m app.ml.subgraph_features

heuristics-train:
	cd backend && python -m app.ml.heuristics.runner --mode train

train-lenses-parallel:
	cd backend && python -m app.ml.training.train_behavioral &
	cd backend && python -m app.ml.training.train_graph &
	cd backend && python -m app.ml.training.train_temporal &
	cd backend && python -m app.ml.training.train_document &
	cd backend && python -m app.ml.training.train_offramp &
	wait

train-entity:
	cd backend && python -m app.ml.training.train_entity

train-meta:
	cd backend && python -m app.ml.training.train_meta

# ── Data ingestion ───────────────────────────────────────────────────────────

ingest:
	cd backend && python -m app.services.ingest_service

# ── Quality ──────────────────────────────────────────────────────────────────

test:
	cd backend && python -m pytest tests/ -v

lint:
	cd backend && python -m ruff check .
	cd frontend && npm run lint

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
