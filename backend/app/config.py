from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_port: int = 8000
    frontend_port: int = 5173

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""

    model_dir: str = "./models"
    behavioral_model_path: str = "./models/behavioral/xgboost_behavioral.pkl"
    behavioral_ae_path: str = "./models/behavioral/autoencoder_behavioral.pt"
    graph_model_path: str = "./models/graph/gat_model.pt"
    entity_model_path: str = "./models/entity/entity_classifier.pkl"
    temporal_model_path: str = "./models/temporal/lstm_model.pt"
    document_model_path: str = "./models/document/document_classifier.pkl"
    offramp_model_path: str = "./models/offramp/offramp_classifier.pkl"
    meta_model_path: str = "./models/meta/meta_model.pkl"
    threshold_policy_path: str = "./models/artifacts/threshold_config.json"

    fallback_risk_threshold: float = 0.75
    network_hops: int = 3

    # When true, use CUDA (XGBoost + PyTorch) or MPS (PyTorch only) when available; else CPU
    ml_use_gpu: bool = False

    @property
    def model_dir_path(self) -> Path:
        return Path(self.model_dir)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
