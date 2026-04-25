with filter_skills as (
    select * 
    from {{ ref('dim_job_skills') }}
    where 1=1 
    and (
        skill not like '%YEARS%' and
        skill not like '%DEGREE%' and 
        skill != ' '
    )
)

select 
    jd.*,
    fs.skill
from {{ ref('jobs_detail') }} jd 
left join filter_skills fs
    using (job_id, data_source)
where skill is not null 
