.PHONY: dev dev-backend dev-frontend install install-backend install-frontend \
       train train-all features subset-processed prepare-meta-features \
       score-training-data \
       heuristics-train train-lenses-parallel train-entity train-meta \
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

# Full pipeline from Elliptic CSVs → repo-root models/ (see scripts/train_all_models.py)
train: train-all

train-all:
	python scripts/train_all_models.py

# Legacy granular targets (cwd backend; pass data paths relative to repo, e.g. ../data/processed)
features:
	cd backend && python -m scripts.prepare_features --input ../data/external --output ../data/processed

# Smaller graph/tabular data for faster iteration (see backend/scripts/subset_processed_data.py)
subset-processed:
	cd backend && python -m scripts.subset_processed_data --input-dir ../data/processed --output-dir ../data/processed_subset --max-nodes 10000

# meta_features.csv from train_features (lens scores default to 0 unless columns exist)
prepare-meta-features:
	cd backend && python -m scripts.prepare_meta_features --data-dir ../data/processed

score-training-data:
	cd backend && python -m scripts.score_training_data --data-dir ../data/processed

prepare-meta-features-subset:
	cd backend && python -m scripts.prepare_meta_features --data-dir ../data/processed_subset

heuristics-train:
	@echo "Heuristic scoring is invoked at inference; no separate train step."

train-lenses-parallel:
	cd backend && \
	python -m app.ml.training.train_behavioral --data-dir ../data/processed & \
	python -m app.ml.training.train_graph --data-dir ../data/processed & \
	python -m app.ml.training.train_temporal --data-dir ../data/processed & \
	python -m app.ml.training.train_offramp --data-dir ../data/processed & \
	wait

train-entity:
	cd backend && python -m app.ml.training.train_entity --data-dir ../data/processed

train-meta:
	cd backend && python -m app.ml.training.train_meta --data-dir ../data/processed

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
