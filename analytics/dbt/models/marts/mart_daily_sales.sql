-- Ventes agrégées par jour / organisation / produit (base des KPIs & forecasts).
select
    organization_id,
    product_id,
    date_trunc('day', sold_at)::date as sale_date,
    sum(quantity) as units,
    sum(total) as revenue,
    count(*) as n_sales
from {{ ref('stg_sales') }}
group by 1, 2, 3
