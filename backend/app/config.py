"""Configuration applicative centralisée (Pydantic Settings v2).

Toutes les valeurs proviennent de variables d'environnement (cf. `.env.example`).
Importer l'instance partagée via `from app.config import settings`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Général ---
    env: str = "local"
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "change-me"

    # --- Auth / JWT ---
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # Mots de passe des comptes de démo (seed). À changer hors local.
    seed_admin_password: str = "admin"
    seed_merchant_password: str = "merchant"

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_v1_prefix: str = "/api/v1"

    # --- Rate limiting ---
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120  # par client (IP ou utilisateur)

    # --- Observabilité / tracing ---
    otel_enabled: bool = False  # active l'export OpenTelemetry (console) si dispo
    service_name: str = "myhanout-api"

    # --- RAG ---
    rag_vector_store: str = "memory"  # memory | pgvector
    embedding_provider: str = "mock"  # mock | mistral
    rag_top_k: int = 4
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Base de données ---
    postgres_user: str = "myhanout"
    postgres_password: str = "myhanout"
    postgres_db: str = "myhanout"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    database_url: str | None = None

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # --- Providers ---
    ocr_provider: str = "mock"
    mistral_api_key: str = ""
    llm_provider: str = "mock"  # mock | claude | mistral | huggingface
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-4-8"

    # --- HuggingFace (LLM + embeddings + images via Inference API) ---
    huggingface_api_key: str = ""
    hf_llm_model: str = "mistralai/Mistral-7B-Instruct-v0.3"
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_image_model: str = "stabilityai/stable-diffusion-xl-base-1.0"

    # --- Génération de visuels (text-to-image) ---
    image_provider: str = "mock"  # mock | huggingface

    # --- Couche financière ---
    finance_classifier: str = "mock"  # mock | llm (réutilise LLM_PROVIDER)
    # Seuil d'écart de prix fournisseur déclenchant une alerte (ex. 0.20 = +20%).
    finance_price_anomaly_pct: float = 0.20

    # --- Import factures par email (IMAP) ---
    email_provider: str = "mock"  # mock | imap
    email_imap_host: str = ""
    email_imap_port: int = 993
    email_imap_user: str = ""
    email_imap_password: str = ""
    email_imap_folder: str = "INBOX"

    # --- Entrepôt de données (DWH) / export ---
    dwh_target: str = "mock"  # mock | http
    dwh_url: str = ""

    # --- Telegram (Bot API) ---
    telegram_provider: str = "mock"  # mock | bot
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    # --- Forecasting ---
    forecast_model: str = "naive"
    forecast_horizon_days: int = 14

    # --- Seeds ---
    # Répertoire des données de seed. /data en docker (volume monté),
    # sinon résolu relativement à la racine du repo.
    seed_dir: str = "/data/seeds"

    # --- WhatsApp ---
    whatsapp_provider: str = "mock"  # mock | business
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = "local-verify-token"
    # Secret d'app Meta pour vérifier la signature des webhooks (X-Hub-Signature-256).
    whatsapp_app_secret: str = ""
    graph_api_version: str = "v20.0"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def sqlalchemy_url(self) -> str:
        """URL async finale (asyncpg), construite si `DATABASE_URL` absent."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
