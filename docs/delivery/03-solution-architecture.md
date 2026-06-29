# 3 · Solution Architecture — MyHanout AI

Architecture en 4 couches (ingestion → data → intelligence → applicative), providers
externes derrière des interfaces abstraites mockables.

## C4 — Niveau 1 : Contexte

```mermaid
flowchart TB
    M[👤 Commerçant] -- WhatsApp --> SYS
    A[👤 Comptable] -- Dashboard --> SYS
    SYS[MyHanout AI] -- commandes --> F[🏭 Fournisseur]
    SYS -- OCR --> MISTRAL[(Mistral OCR)]
    SYS -- LLM --> LLM[(Claude / Mistral)]
    SYS -- messages --> WA[(WhatsApp Business API)]
```

## C4 — Niveau 2 : Conteneurs

```mermaid
flowchart TB
    subgraph Cloud
        API[FastAPI API]
        WORKER[Celery workers]
        FE[Frontend React/Vite]
        PG[(PostgreSQL 16 + pgvector)]
        REDIS[(Redis)]
    end
    FE --> API
    API --> PG
    API -- enqueue --> REDIS
    WORKER -- consume --> REDIS
    WORKER --> PG
    API -. OCR/LLM/WhatsApp .-> EXT[(Providers externes)]
```

## C4 — Niveau 3 : Composants (API)

```mermaid
flowchart LR
    subgraph API
        ROUT[Routers v1]
        DEPS[deps: auth + tenant guard]
        SVC[Services]
        REPO[Repositories]
        ING[Ingestion: OCR/parse/validate]
        INT[Intelligence: forecasting/agents/LLM]
        MSG[Messaging: WhatsApp]
    end
    ROUT --> DEPS --> SVC
    SVC --> REPO --> MODELS[(Models + TenantMixin)]
    SVC --> ING
    SVC --> INT
    SVC --> MSG
```

## Data Flow — Ingestion facture

```mermaid
flowchart LR
    DOC[PDF/Photo] --> OCR[OCRProvider]
    OCR --> PARSE[Parser] --> VALID[Validation]
    VALID --> REPORT[Rapport explicable]
    REPORT --> REVIEW[(Invoice: pending_review)]
    REVIEW -- approve humain --> LINES[(invoice_line + audit)]
```

## Sequence — Suggestion → commande (human-in-the-loop)

```mermaid
sequenceDiagram
    participant M as Commerçant
    participant API
    participant FC as ForecastModel
    participant DB as Postgres
    M->>API: POST /orders/suggest (demain)
    API->>FC: predict(history)
    FC-->>API: yhat + explication
    API->>DB: stock courant (tenant filtré)
    API-->>M: suggestion explicable (ajustable)
    M->>API: POST /orders/confirm (ajusté, mode)
    API->>DB: order=confirmed + audit
    alt mode whatsapp_auto
        API->>M: message fournisseur envoyé (status=sent)
    end
```

## Sequence — Webhook WhatsApp (texte/image)

```mermaid
sequenceDiagram
    participant WA as WhatsApp
    participant API
    participant CONV as ConversationService
    WA->>API: POST /whatsapp/webhook (signé)
    API->>API: verify_signature (HMAC)
    alt image
        API->>CONV: handle_image -> download + OCR
    else texte
        API->>CONV: handle_text (machine à états)
    end
    CONV-->>WA: réponse (provider)
```

## Agent Architecture

```mermaid
flowchart TB
    ORCH[Orchestrator / Supervisor] --> O[agent_order]
    ORCH --> S[agent_stock]
    ORCH --> F[agent_finance]
    ORCH --> MK[agent_marketing]
    ORCH --> SUP[agent_support]
    ORCH --> GOV[agent_governance]
    GOV -. valide actions sensibles .-> O
    O & MK & SUP --> LLM[(LLMProvider)]
```
- Intent détecté → routage vers l'agent ; `agent_governance` impose la validation
  humaine sur les actions sensibles. Interface commune `BaseAgent` (run/explain/actions).

## Deployment Diagram

```mermaid
flowchart TB
    subgraph Host/Cloud
        LB[Reverse proxy / TLS]
        subgraph Containers
            APIc[api]
            WORKERc[worker]
            FEc[frontend]
            PGc[(postgres+pgvector)]
            REDISc[(redis)]
        end
    end
    LB --> APIc & FEc
    APIc --> PGc & REDISc
    WORKERc --> PGc & REDISc
```

## Infrastructure
- **Local/dev** : `docker compose up` (postgres+pgvector, redis, api, worker, frontend).
- **Cible cloud (V2)** : conteneurs managés (ECS/Cloud Run), Postgres managé + pgvector,
  Redis managé, secrets via gestionnaire (SSM/Secret Manager), CI/CD GitHub Actions.
- **Observabilité** : logs structurés (structlog), métriques Prometheus (`/metrics`),
  healthchecks ; tracing (V2).
