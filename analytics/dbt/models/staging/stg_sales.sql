-- Ventes nettoyées (1 ligne par vente). organization_id conservé (multi-tenant).
select
    id as sale_id,
    organization_id,
    product_id,
    quantity::numeric as quantity,
    unit_price::numeric as unit_price,
    total::numeric as total,
    sold_at,
    external_ref
from {{ source('app', 'sale') }}
