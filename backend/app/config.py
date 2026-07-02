"""Configuration applicative centralisée (Pydantic Settings v2).

Toutes les valeurs proviennent de variables d'environnement (cf. `.env.example`).
Importer l'instance partagée via `from app.config import settings`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "change-me"
_PROD_ENVS = {"production", "prod", "staging"}


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
    # Compte opérateur plateforme (backoffice MyHanout) créé par le seed.
    seed_platform_password: str = "platform"

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

    # --- Capteurs de température (chaîne du froid) ---
    sensor_provider: str = "mock"  # mock | http
    sensor_http_url: str = ""

    # --- Connecteur caisse (POS) ---
    pos_connector: str = "mock"  # mock | http
    pos_url: str = ""

    # --- Signaux externes (météo histo, vacances, carburant, foot…) ---
    signals_provider: str = "mock"  # mock | http
    signals_http_url: str = ""
    signals_api_key: str = ""
    # Région par défaut pour les signaux régionalisés (météo/vacances).
    signals_region: str = "FR"
    # Signaux métier propres au commerçant (match local, jour de paie…).
    merchant_signals_source: str = "mock"  # mock (keyless) | … (à brancher)

    # --- Telegram (Bot API) ---
    telegram_provider: str = "mock"  # mock | bot
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    # --- Slack (Web API + Events API) ---
    slack_provider: str = "mock"  # mock | bot
    slack_bot_token: str = ""  # xoxb-…
    slack_signing_secret: str = ""  # vérification de signature (optionnel)
    slack_default_channel: str = ""  # canal par défaut pour les notifications

    # Secret partagé backend ↔ ml-service (auth interne). Vide = ml-service keyless (local).
    ml_internal_key: str = ""

    # --- Forecasting ---
    forecast_model: str = "naive"
    forecast_horizon_days: int = 14
    # Service ML isolé : inprocess (défaut keyless) | http (ml-service/ via docker).
    forecast_service_client: str = "inprocess"  # inprocess | http
    ml_service_url: str = "http://ml-service:8001"
    # Version de modèle exposée par défaut (traçabilité MLOps quand inprocess).
    model_version: str = "v1"
    # MLOps : MAPE au-delà de laquelle un modèle est jugé « dérivé » (alerte + retrain).
    mlops_drift_mape_threshold: float = 0.35

    # --- Recommandations (réassort explicable) ---
    # Tampon de sécurité (fraction de la demande prévue) et seuils des règles.
    reco_safety_buffer_ratio: float = 0.15
    reco_stockout_risk_threshold: float = 0.5  # au-delà → proposer une commande
    reco_overstock_days: int = 21  # stock couvrant plus de N jours → réduire

    # --- Démarque (anti-gaspillage frais, agent Démarque) ---
    # Horizon de scan : on n'examine que les lots périssables périmant sous N jours.
    markdown_horizon_days: int = 5
    # Paliers de démarque proposés (du plus doux au plus fort).
    markdown_tiers: list[int] = [10, 20, 30, 40, 50]
    # Élasticité-prix simplifiée : +1 % de remise → +élasticité % de demande journalière.
    markdown_elasticity: float = 1.5
    # Marge brute par défaut quand le coût d'achat est inconnu (coût = prix × (1 - marge)).
    markdown_default_margin_ratio: float = 0.30

    # --- Effectifs (agent Effectifs) ---
    # Capacité : nombre d'unités vendues qu'une personne absorbe par jour.
    staffing_units_per_staff_day: float = 120.0
    staffing_base_staff: int = 1  # effectif plancher (le commerçant lui-même)
    staffing_horizon_days: int = 7

    # --- Prix (agent Prix) ---
    # Marge brute cible (prix conseillé = coût / (1 - marge)).
    pricing_target_margin_ratio: float = 0.35
    # Arrondi psychologique (charm pricing : terminaisons en ,90/,95/,99).
    pricing_charm_pricing: bool = True
    # Coût par défaut si inconnu (coût = prix × (1 - marge)).
    pricing_default_margin_ratio: float = 0.30

    # --- Contrôles (3-way match factures + démarque inconnue) ---
    # Tolérance d'écart de prix avant signalement (en %).
    control_price_tolerance_pct: float = 5.0
    # Écart de stock minimal (unités) avant de signaler une démarque inconnue.
    shrinkage_min_units: float = 1.0

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

    @model_validator(mode="after")
    def _enforce_prod_secret(self) -> Settings:
        """En prod/staging : refuse une SECRET_KEY par défaut ou trop courte.

        Le JWT ET le chiffrement des connecteurs en dépendent — une clé faible en
        production = tokens forgeables + secrets déchiffrables. En local/CI, aucun
        blocage (mock-first)."""
        if self.env.lower() in _PROD_ENVS and (
            self.secret_key == _DEFAULT_SECRET or len(self.secret_key) < 32
        ):
            raise ValueError(
                "SECRET_KEY faible ou par défaut interdite en production : "
                "définissez une clé aléatoire d'au moins 32 caractères."
            )
        return self

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
