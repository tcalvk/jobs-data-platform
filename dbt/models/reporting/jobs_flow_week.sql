with jobs_base as (
    select * 
    from {{ ref('jobs_detail') }}
)

, new_jobs as (
    select
        date_trunc(coalesce(posted_date, cast(created_at_utc as date)), week) as week_beginning,
        search_term,
        job_platform,
        search_location,
        'New Jobs' as type,
        count(distinct job_id) as jobs_count
    from jobs_base
    group by all 
)

, removed_jobs as (
    select
        date_trunc(removed_date, week) as week_beginning,
        search_term,
        job_platform,
        search_location,
        'Removed Jobs' as type,
        count(distinct job_id) as jobs_count
    from jobs_base
    where removed_date is not null
    group by all
)

, _unions as (
    select * from new_jobs
    union all
    select * from removed_jobs
)

select * from _unions
