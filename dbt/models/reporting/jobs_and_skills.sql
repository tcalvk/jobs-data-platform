{{ 
    config (
        tags=['daily']
    ) 
}}

select 
    js.*  
    ,jd.* except (job_id)
from {{ ref('dim_jobs_and_skills') }} js 
left join {{ ref('jobs_detail') }} jd 
    on js.job_id = jd.job_id 