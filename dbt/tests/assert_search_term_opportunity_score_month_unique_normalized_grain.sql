{{ config(severity='warn') }}

select
    month_start_date,
    lower(trim(search_term)) as search_term_join_key,
    lower(trim(search_location)) as search_location_join_key,
    count(*) as row_count
from {{ ref('search_term_opportunity_score_month') }}
group by 1, 2, 3
having count(*) > 1
