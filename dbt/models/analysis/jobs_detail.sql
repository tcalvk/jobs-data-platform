select * except (job_description, search_location),
    case 
        when lower(job_title) like '%principal%' then 'Principal'
        when lower(job_title) like '%distinguished%' then 'Principal'
        when lower(job_title) like '%lead%' then 'Lead'
        when lower(job_title) like '%sr%' then 'Senior'
        when lower(job_title) like '%senior%' then 'Senior'
        when lower(job_title) like '%mid%' then 'Mid Level'
        when lower(job_title) like '%staff%' then 'Mid Level'
        when lower(job_title) like '%ii%' then 'Mid Level'
        when lower(job_title) like '%iii%' then 'Mid Level'
        when lower(job_title) like '%3%' then 'Mid Level'
        when lower(job_title) like '%i%' then 'Entry'
        when lower(job_title) like '%entry%' then 'Entry'
        when lower(job_title) like '%junior%' then 'Entry'
        else 'Entry'
    end as job_level,
    if (
        date_diff(date(current_timestamp()), date(last_seen_at_mst), day) >= 7,
        'Removed',
        'Active' 
    ) as listing_status,
    initcap(search_location) as search_location
from {{ ref('dim_job_listings') }}