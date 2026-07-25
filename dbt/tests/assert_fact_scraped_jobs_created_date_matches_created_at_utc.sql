select
    job_id,
    created_at_utc,
    created_date
from {{ ref('fact_scraped_jobs') }}
where created_date != date(created_at_utc)
