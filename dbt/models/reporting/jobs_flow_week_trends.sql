with new_jobs as (
    select * except(job_platform)
    from {{ ref('jobs_flow_week') }}
    where type = 'New Jobs'
)

, agg as (
    select 
        week_beginning,
        search_term,
        search_location,
        type,
        sum(jobs_count) as jobs_count
    from new_jobs
    group by 1, 2, 3, 4
)

select *,
    (jobs_count - previous_week_jobs_count) / nullif(previous_week_jobs_count, 0) * 100 as wow_percent_change
from (
    select *,
        lag(jobs_count) over (
            partition by search_term, search_location 
            order by week_beginning asc 
        ) as previous_week_jobs_count
    from agg 
)
