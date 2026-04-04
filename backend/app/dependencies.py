from functools import lru_cache
from supabase import Client
from app.supabase_client import get_supabase
from app.config import Settings, settings


def get_db() -> Client:
    return get_supabase()


@lru_cache
def get_settings() -> Settings:
    return settings
