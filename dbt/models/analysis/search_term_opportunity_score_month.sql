with job_detail as (
    select *
    from {{ ref('jobs_detail') }}
)

, search_term_months as (
    select
        search_term,
        search_location,
        date_trunc(posted_date, month) as month, -- structure opportunity scoring by month, so that it's not oversensitive, but still adjusts over time
        count(distinct job_id) as active_jobs_count
    from job_detail
    where listing_status = 'Active'
    group by 1, 2, 3
)

, _agg as (
    select
        month,
        search_term,
        search_location,
        active_jobs_count,
        min(active_jobs_count) over () as min_active_jobs_count,
        max(active_jobs_count) over () as max_active_jobs_count
    from search_term_months
    group by 1, 2, 3, 4
)
, demand_score as (
    select
        month,
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
    from _agg
)

select *
from demand_score
