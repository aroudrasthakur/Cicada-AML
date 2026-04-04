from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ml.model_paths import MODELS_DIR


class Settings(BaseSettings):
    app_env: str = "development"
    api_port: int = 8000
    frontend_port: int = 5173

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""
    # Legacy HS256 user access tokens only (optional if you use JWT signing keys + JWKS)
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"

    model_dir: str = str(MODELS_DIR)
    behavioral_model_path: str = str(MODELS_DIR / "behavioral" / "xgboost_behavioral.pkl")
    behavioral_ae_path: str = str(MODELS_DIR / "behavioral" / "autoencoder_behavioral.pt")
    graph_model_path: str = str(MODELS_DIR / "graph" / "gat_model.pt")
    entity_model_path: str = str(MODELS_DIR / "entity" / "entity_classifier.pkl")
    temporal_model_path: str = str(MODELS_DIR / "temporal" / "lstm_model.pt")
    offramp_model_path: str = str(MODELS_DIR / "offramp" / "offramp_classifier.pkl")
    meta_model_path: str = str(MODELS_DIR / "meta" / "meta_model.pkl")
    threshold_policy_path: str = str(MODELS_DIR / "artifacts" / "threshold_config.json")

    fallback_risk_threshold: float = 0.75
    network_hops: int = 3

    # When true, use CUDA (XGBoost + PyTorch) or MPS (PyTorch only) when available; else CPU
    ml_use_gpu: bool = False

    # Inference: graphs with more nodes skip PageRank/betweenness/clustering (can take minutes).
    # Set to 0 to never skip. Training still uses full metrics when you run training code paths.
    infer_skip_graph_global_metrics_above_nodes: int = 4000

    @property
    def model_dir_path(self) -> Path:
        return Path(self.model_dir)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
