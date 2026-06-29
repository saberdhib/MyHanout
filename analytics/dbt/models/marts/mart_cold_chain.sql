-- Chaîne du froid : température min/max/moyenne par équipement et par jour,
-- avec drapeau hors-plage (HACCP).
select
    tr.organization_id,
    tr.equipment_id,
    e.name as equipment_name,
    date_trunc('day', tr.recorded_at)::date as day,
    min(tr.temp_c) as min_temp_c,
    max(tr.temp_c) as max_temp_c,
    avg(tr.temp_c)::numeric(5, 2) as avg_temp_c,
    bool_or(tr.temp_c < e.min_temp_c or tr.temp_c > e.max_temp_c) as out_of_range
from {{ source('app', 'temperature_reading') }} tr
join {{ source('app', 'equipment') }} e on e.id = tr.equipment_id
group by 1, 2, 3, 4
