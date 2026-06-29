-- Dernier coût d'achat par produit/org, dérivé des lignes de facture.
with lines as (
    select
        il.product_id,
        i.organization_id,
        il.unit_price::numeric as unit_price,
        i.issue_date,
        row_number() over (
            partition by i.organization_id, il.product_id
            order by i.issue_date desc nulls last, i.id desc
        ) as rn
    from {{ source('app', 'invoice_line') }} il
    join {{ source('app', 'invoice') }} i on i.id = il.invoice_id
    where il.product_id is not null
)
select organization_id, product_id, unit_price as last_cost, issue_date
from lines
where rn = 1
