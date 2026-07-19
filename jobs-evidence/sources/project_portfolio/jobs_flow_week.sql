select
    cast(week_beginning as date) as week_beginning,
    search_term,
    job_platform,
    search_location,
    type,
    safe_cast(jobs_count as int64) as jobs_count
from `projects-portfolio-446806.reporting.jobs_flow_week`
