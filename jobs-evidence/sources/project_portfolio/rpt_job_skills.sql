select
    skill,
    job_id,
    posted_date,
    search_term,
    job_level,
    degree_requirement,
    job_title,
    company_name,
    search_location,
    job_platform,
    listing_status,
    avg_annual_pay_range
from `projects-portfolio-446806.reporting.rpt_job_skills`
where skill is not null
