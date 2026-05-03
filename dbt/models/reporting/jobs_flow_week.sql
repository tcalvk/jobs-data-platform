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
        count(job_id) as new_jobs_count
    from jobs_base
    group by all 
)

, removed_jobs as (
    select
        date_trunc(removed_date, week) as week_beginning,
        search_term,
        job_platform,
        search_location,
        count(job_id) as removed_jobs_count
    from jobs_base
    where removed_date is not null
    group by all
)

select 
    coalesce(nj.week_beginning, rj.week_beginning) as week_beginning,
    coalesce(nj.search_term, rj.search_term) as search_term,
    coalesce(nj.job_platform, rj.job_platform) as job_platform,
    coalesce(nj.search_location, rj.search_location) as search_location,
    coalesce(nj.new_jobs_count, 0) as new_jobs_count,
    coalesce(rj.removed_jobs_count, 0) as removed_jobs_count
from new_jobs nj
full outer join removed_jobs rj 
    using (week_beginning, search_term, job_platform, search_location)
where coalesce(nj.week_beginning, rj.week_beginning) is not null 
