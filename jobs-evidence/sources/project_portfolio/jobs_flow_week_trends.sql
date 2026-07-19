select
    cast(week_beginning as date) as week_beginning,
    search_term,
    search_location,
    type,
    safe_cast(jobs_count as int64) as jobs_count,
    safe_cast(previous_week_jobs_count as int64) as previous_week_jobs_count,
    safe_cast(wow_percent_change as float64) as wow_percent_change
from `projects-portfolio-446806.reporting.jobs_flow_week_trends`
