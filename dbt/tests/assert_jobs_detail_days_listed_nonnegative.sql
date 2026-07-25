select
    job_id,
    days_listed
from {{ ref('jobs_detail') }}
where days_listed < 0
