select
    month_start_date,
    search_term,
    search_location,
    count(*) as row_count
from {{ ref('search_term_opportunity_score_month') }}
group by 1, 2, 3
having count(*) > 1
