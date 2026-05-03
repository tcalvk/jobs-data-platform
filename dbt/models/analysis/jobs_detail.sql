with src as (
    select * except (job_description, search_location),
        case 
            when lower(job_title) like '%principal%' then 'Principal'
            when lower(job_title) like '%distinguished%' then 'Principal'
            when lower(job_title) like '%lead%' then 'Lead'
            when lower(job_title) like '%sr%' then 'Senior'
            when lower(job_title) like '%senior%' then 'Senior'
            when lower(job_title) like '%mid%' then 'Mid Level'
            when lower(job_title) like '%staff%' then 'Staff'
            when lower(job_title) like '% iii' then 'Mid Level'
            when lower(job_title) like '% ii' then 'Mid Level'
            when lower(job_title) like '% 3' then 'Mid Level'
            when lower(job_title) like '%entry%' then 'Entry'
            when lower(job_title) like '%junior%' then 'Entry'
            else 'Entry'
        end as job_level,
        if(
            date_diff(date(current_timestamp()), date(last_seen_at_mst), day) >= 7,
             dateadd(date(last_seen_at_mst), interval 1 day),
             cast(null as date)
        ) as removed_date,
        initcap(search_location) as search_location,
        -- This col's logic takes care of averaging if the low or high pay range is null (to ensure a true avg)
        (COALESCE(low_annual_pay_range, 0) + COALESCE(high_annual_pay_range, 0)) / 
        (
            CASE 
                WHEN low_annual_pay_range IS NULL AND high_annual_pay_range IS NULL THEN NULL 
                ELSE (CASE WHEN low_annual_pay_range IS NULL THEN 0 ELSE 1 END) + 
                    (CASE WHEN high_annual_pay_range IS NULL THEN 0 ELSE 1 END)
            END
        ) AS avg_annual_pay_range
    from {{ ref('dim_job_listings') }}
)

, add_listing_info as (
    select *,
        if(
            removed_date is not null,  
            'Removed',
            'Active' 
        ) as listing_status,
        date_diff(posted_date, date(last_seen_at_mst), day) as days_listed
    from src
)

select * from add_listing_info
