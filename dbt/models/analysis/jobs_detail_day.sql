with job_facts as (
    select * from {{ ref('fact_scraped_jobs') }}
)

, derived as (
    select * except (job_description, search_location),
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
