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

## Données de seed

`data/seeds/` : `suppliers.csv`, `products.csv`, `sales.csv` (~720 lignes,
saisonnalité hebdomadaire), `invoices.json`. Chargement : `make seed`.
