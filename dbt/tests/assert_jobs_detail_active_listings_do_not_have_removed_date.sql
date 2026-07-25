select
    job_id,
    listing_status,
    removed_date
from {{ ref('jobs_detail') }}
where listing_status = 'Active'
    and removed_date is not null
