select
    job_id,
    first_seen_at_utc,
    last_seen_at_utc
from {{ ref('jobs_detail') }}
where last_seen_at_utc < first_seen_at_utc
