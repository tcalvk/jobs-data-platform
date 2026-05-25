with fact_detail as (
    select 
        search_term, 
        search_location, 
        job_id,
        posted_date
    from {{ ref('jobs_detail_day') }}
)

, dim_detail as (
    select 
        job_id,
        listing_status,
        removed_date
    from {{ ref('jobs_detail') }}
)

, search_term_months as (
    select
        fd.search_term,
        fd.search_location,
        date_trunc(fd.posted_date, month) as month, -- structure opportunity scoring by month, so that it's not oversensitive, but still adjusts over time
        count(distinct fd.job_id) as active_jobs_count
    from fact_detail fd
    left join dim_detail dd 
        using (job_id) 
    where dd.listing_status = 'Active'
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
