select *
from {{ ref('search_term_opportunity_score_month') }}
where opportunity_score not between 0 and 100
    or demand_score not between 0 and 100
    or growth_score not between 0 and 100
    or salary_score not between 0 and 100
    or long_tail_score not between 0 and 100
