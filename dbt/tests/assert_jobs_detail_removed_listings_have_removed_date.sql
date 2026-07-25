select
    job_id,
    listing_status,
    removed_date
from {{ ref('jobs_detail') }}
where listing_status = 'Removed'
    and removed_date is null
