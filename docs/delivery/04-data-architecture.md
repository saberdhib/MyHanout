# 4 · Data Architecture — MyHanout AI

## Data Sources Inventory
| Source | Statut | Mode |
|--------|--------|------|
| Factures PDF/photo | ✅ Livré | OCR (Mistral) + fallback + parsing |
| Saisie fin de journée | ✅ Livré (Phase 2) | WhatsApp / dashboard |
| Historique ventes | ✅ Seed/idéal POS | base du forecasting |
| WhatsApp (messages) | ✅ Livré (Phase 2) | webhook signé |
| POS (caisse) | ⬜ V3 | connecteur à définir |
| Comptabilité | ⬜ V3 | export/échéances |
| Fournisseurs (catalogues) | 🟡 | saisie manuelle, EDI futur |
| Météo / promotions | ⬜ V2 | régresseurs forecasting |

## Intégrations (état & cible)
- **OCR pipeline** : ✅ upload PDF/image → OCR → parse → validation → `pending_review`
  → approve (écrit `invoice_line` + audit). Idempotent (hash SHA-256). Confidence + erreurs typées.
- **WhatsApp** : ✅ webhook signé, texte + image (→ OCR), machine à états persistée.
- **POS / Accounting / Supplier EDI** : ⬜ planifiés, derrière des connecteurs abstraits
  (même pattern provider que OCR/LLM/WhatsApp).

## Data Model (entités principales)
`organization` (tenant) · `membership` (user×org×rôle) · `user` · `product` · `stock` ·
`sale` · `supplier` · `invoice`/`invoice_line` · `order`/`order_line` · `daily_entry` ·
`forecast_evaluation` · `conversation` · `event` · `audit_log` · `document_chunk` (pgvector).
Diagramme ERD détaillé : `docs/data-model.md`.

## PostgreSQL Schema
- SQLAlchemy 2.0 async ; migrations Alembic (`0001`→`000x`).
- **Multi-tenant** : `TenantMixin` (`organization_id` NOT NULL, indexé) sur toutes les
  tables métier ; garde-fou central (filtre auto des SELECT + estampillage des INSERT).
- Énumérations stockées en VARCHAR (valeurs minuscules via `values_callable`).

## pgvector Schema
- Extension `vector` activée par migration ; table `document_chunk(embedding vector(1536))`
  hors ORM (créée en SQL brut) → compat tests SQLite.
- Usage cible (V2) : RAG sur factures/documents (recherche sémantique).

## Data Dictionary (extrait)
| Table.colonne | Type | Sens |
|---------------|------|------|
| product.sku | str(64) unique | Référence catalogue (par org) |
| product.perishable / shelf_life_days | bool / int | Gestion péremption |
| stock.quantity / reorder_threshold | num | État + seuil d'alerte |
| sale.sold_at / quantity | datetime / num | Historique forecasting |
| invoice.status | enum | pending_review/approved/rejected/… |
| invoice.file_hash | str(64) unique | Idempotence d'import |
| invoice.ocr_confidence | num | Fiabilité OCR (signalée au réviseur) |
| daily_entry.(quantity_ordered, stock_remaining) | num | Donnée d'or MLOps |
| forecast_evaluation.(predicted, actual, error_abs, error_pct, model_version) | num/str | Écart prévu/réel |
| membership.role | enum | owner/staff/accountant/read_only |

## ETL / ELT
- **Ingestion (EL→T)** : documents bruts → OCR → parsing → validation → persistance
  structurée (T à l'approbation humaine). Orchestrable en asynchrone (Celery `ocr_task`).
- **Normalisation** : unités, libellés, rapprochement SKU (`ingestion/etl/normalize.py`).
- **Agrégation analytics** : ventes journalières par produit (base forecasting),
  agrégats MAE/MAPE (MLOps).

## Data Quality Rules
- Facture : fournisseur présent, ≥ 1 ligne, cohérence total vs somme des lignes (tol. 1 %),
  confiance OCR ≥ seuil — sinon `pending_review` avec motif explicite.
- Saisie quotidienne : idempotence (produit, date) ; quantités ≥ 0.
- Tenant : `organization_id` NOT NULL (contrainte BD + garde-fou applicatif).

## Feature Store (léger)
- Features de forecasting calculées à la demande : saisonnalité hebdo, jours fériés,
  fêtes paramétrables (`intelligence/forecasting/features/`).
- Versionnées via `forecast_evaluation.model_version` (traçabilité).
- V2 : matérialiser un store de features (lags/rolling/calendrier/météo) pour Prophet/LGBM.
