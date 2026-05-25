with job_facts as (
    select * from {{ ref('fact_scraped_jobs') }}
)

, derived as (
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
    from job_facts
)

select * from derived
