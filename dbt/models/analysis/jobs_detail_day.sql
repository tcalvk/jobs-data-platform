with job_facts as (
    select * from {{ ref('fact_scraped_jobs') }}
)

, jobs_detail as (
    select * from {{ ref('jobs_detail') }}
)

, joined as (
    select 
        jf.created_at_utc,
        jf.search_term,
        jf.job_platform,
        
    from job_facts jf 
    left join jobs_detail jd 
        using (platform_job_id, company_name, data_source)
)