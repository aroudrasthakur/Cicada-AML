# Aegis AML

AI-Powered Blockchain Laundering Detection and Investigation Dashboard.

A hybrid system that classifies transactions and wallet clusters as suspicious, detects broader laundering networks, explains why they were flagged, and visualizes fund movement for investigators.

## Architecture

- **Backend**: FastAPI (Python) with stacked ML pipeline
- **Frontend**: React + Vite + TypeScript + Tailwind CSS + Cytoscape.js
- **Database**: Supabase (PostgreSQL)
- **ML Pipeline**: 185-typology heuristic engine → 6 lens-specific models → XGBoost meta-learner

## Quick Start

```bash
# Install dependencies
make install

# Copy env files and fill in your Supabase credentials
cp backend/.env.example backend/.env

# Start backend
make dev-backend

# Start frontend (separate terminal)
make dev-frontend
```

## Training Pipeline

```bash
# Run the full training pipeline in dependency order
make train
```

## Project Structure

```
backend/          FastAPI backend + ML pipeline
frontend/         React dashboard
supabase/         Database migrations and seed data
models/           Trained model artifacts
data/             Raw and processed datasets
notebooks/        Jupyter notebooks for exploration
scripts/          Utility scripts
docs/             Documentation
```

## Detection Pipeline

1. **Data Ingestion** — CSV upload or Elliptic dataset loader
2. **Graph Construction** — Directed temporal graph via NetworkX
3. **Feature Engineering** — Transaction, wallet, and subgraph features
4. **Heuristic Engine** — 185 typology-specific rules run first
5. **Lens Models** — 6 specialized models (Behavioral, Graph, Entity, Temporal, Document, Off-ramp)
6. **Meta-Model** — XGBoost stacking learner combines all signals
7. **Case Assembly** — Suspicious networks identified and explained
8. **Dashboard** — Interactive visualization for investigators
