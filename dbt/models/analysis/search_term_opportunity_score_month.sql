with search_term_months as (
    select
        search_term,
        search_location,
        count(distinct job_id) as active_jobs_count
    from {{ ref('jobs_detail') }}
    where listing_status = 'Active'
    group by 1, 2
)
, agg as (
    select
        search_term,
        search_location,
        active_jobs_count,
        min(active_jobs_count) over () as min_active_jobs_count,
        max(active_jobs_count) over () as max_active_jobs_count
    from search_terms
    group by 1, 2, 3
)
, final as (
    select
        search_term,
        search_location,
        active_jobs_count,
        case
            when max_active_jobs_count = min_active_jobs_count then 100
            else safe_divide(
                active_jobs_count - min_active_jobs_count,
                max_active_jobs_count - min_active_jobs_count
            ) * 100
        end as demand_score
    from agg
)

select *
from final
