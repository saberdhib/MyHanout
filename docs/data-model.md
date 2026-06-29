# Modèle de données — MyHanout AI

Entités SQLAlchemy 2.0 (async). Migration initiale : `backend/alembic/versions/0001_initial.py`.

## Diagramme ERD

```mermaid
erDiagram
    ROLE ||--o{ USER : "a"
    USER ||--o{ AUDIT_LOG : "génère"
    SUPPLIER ||--o{ PRODUCT : "fournit"
    SUPPLIER ||--o{ INVOICE : "émet"
    SUPPLIER ||--o{ ORDER : "reçoit"
    PRODUCT ||--o{ STOCK : "a"
    PRODUCT ||--o{ SALE : "vendu"
    PRODUCT ||--o{ INVOICE_LINE : "référencé"
    PRODUCT ||--o{ ORDER_LINE : "commandé"
    INVOICE ||--o{ INVOICE_LINE : "contient"
    ORDER ||--o{ ORDER_LINE : "contient"
    USER ||--o{ ORDER : "crée/valide"

    ROLE { int id PK; string name; string permissions }
    USER { int id PK; string email; int role_id FK }
    SUPPLIER { int id PK; string name; int payment_terms_days }
    PRODUCT { int id PK; string sku; string name; bool perishable; int shelf_life_days; int supplier_id FK }
    STOCK { int id PK; int product_id FK; numeric quantity; numeric reorder_threshold; date expiry_date }
    SALE { int id PK; int product_id FK; numeric quantity; datetime sold_at }
    INVOICE { int id PK; string number; int supplier_id FK; date due_date; numeric total_amount; string status; string ocr_status }
    INVOICE_LINE { int id PK; int invoice_id FK; int product_id FK; numeric quantity; numeric line_total }
    ORDER { int id PK; int supplier_id FK; string status; bool requires_approval; int approved_by_id FK }
    ORDER_LINE { int id PK; int order_id FK; int product_id FK; numeric quantity }
    EVENT { int id PK; string type; string severity; string entity_type; int entity_id }
    AUDIT_LOG { int id PK; int user_id FK; string action; string resource; int resource_id }
```

## Notes

- **Énumérations** stockées en texte (valeurs minuscules) via `values_callable` :
  `InvoiceStatus`, `OcrStatus`, `OrderStatus`, `EventType` (cf. `models/base.py`).
- **Horodatage** : `created_at` / `updated_at` automatiques (`TimestampMixin`).
- **RBAC** : `role.permissions` = scopes séparés par virgules (`*` = tous).
- **Human-in-the-loop** : `order.requires_approval` + `approved_by_id`.
- **pgvector** : table `document_chunk` (`embedding vector(1536)`) créée par la
  migration pour la recherche sémantique sur documents. Hors ORM afin de garder
  les tests compatibles SQLite.

## Divergences SQLite ↔ PostgreSQL

Les tests unitaires/fonctionnels tournent sur **SQLite** (rapides, sans service) ;
les tests d'intégration et les migrations tournent sur **PostgreSQL 16 + pgvector**
(job CI `integration-postgres`). Divergences gérées :

| Sujet | PostgreSQL | SQLite | Choix |
|-------|-----------|--------|-------|
| Type `vector` (pgvector) | natif (extension) | inexistant | `document_chunk` créé en SQL brut dans la migration, **hors ORM** → `create_all` SQLite ne le voit pas |
| Énumérations | `VARCHAR` (`native_enum=False` + `values_callable`) | `VARCHAR` | identique des deux côtés, valeurs minuscules (`pending_review`…) |
| `validation_report` (facture) | `TEXT` (JSON sérialisé) | `TEXT` | portable, pas de type `JSONB` pour rester commun |
| Application du schéma | `alembic upgrade head` (joue extension + SQL brut) | `Base.metadata.create_all` | la migration (extension/`document_chunk`) n'est exercée que sur PG |

> Validé en réel : `alembic upgrade head` (0001 + 0002) sur pg16, extension
> `vector` 0.6.0 active, insertion d'un `vector(1536)`, enum stocké en
> `pending_review`. Voir le job CI `integration-postgres`.

## Couche financière (pré-compta / pilotage)

| Table | Tenant | Rôle |
|-------|--------|------|
| `expense_category` | **Non** (référentiel global) | Taxonomie standard des charges (`code`, `label`, `kind` opex/capex, `accounting_hint`). Sans PII, identique pour tous → global, lecture seule. |
| `invoice` (étendue) | Oui | Classification : `category_id`, `expense_kind`, `classification_source` (ai/human/rule), `classification_confidence`, `classification_explanation`. |
| `expense_classification_feedback` | Oui | Corrections humaines (signal d'apprentissage) : ancienne/nouvelle catégorie & kind, source remplacée, auteur. |

> `ExpenseCategory` n'hérite pas de `TenantMixin` : le garde-fou central ne le
> filtre donc pas (voulu, table de lookup). Les chiffres finance (trésorerie,
> marges, valorisation) sont dérivés **par ORM** des tables tenant (`sale`,
> `invoice`, `invoice_line`, `stock`) → isolation garantie. Positionnement :
> **pilotage / pré-compta**, pas de comptabilité certifiée.

## Données de seed

`data/seeds/` : `suppliers.csv`, `products.csv`, `sales.csv` (~720 lignes,
saisonnalité hebdomadaire), `invoices.json`. Chargement : `make seed`.
