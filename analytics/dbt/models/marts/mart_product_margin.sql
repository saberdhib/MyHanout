-- Marge réelle par produit : prix de vente moyen - dernier coût d'achat connu.
with sales as (
    select organization_id, product_id, sum(total) as revenue, sum(units) as units
    from {{ ref('mart_daily_sales') }}
    group by 1, 2
)
select
    s.organization_id,
    s.product_id,
    p.sku,
    p.name as product_name,
    s.units,
    case when s.units > 0 then s.revenue / s.units else 0 end as avg_sale_price,
    c.last_cost,
    case
        when s.units > 0 then (s.revenue / s.units) - coalesce(c.last_cost, 0)
    end as margin_unit
from sales s
left join {{ ref('stg_purchase_costs') }} c
    on c.organization_id = s.organization_id and c.product_id = s.product_id
left join {{ source('app', 'product') }} p on p.id = s.product_id
