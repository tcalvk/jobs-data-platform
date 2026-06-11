select *
from {{ ref('search_term_opportunity_score_month') }}
where active_jobs_count = 0
    and new_jobs_count = 0
    and prior_month_new_jobs_count = 0
    and (demand_score != 0 or growth_score != 0)
