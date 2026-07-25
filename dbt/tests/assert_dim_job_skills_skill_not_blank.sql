select
    job_id,
    data_source,
    skill
from {{ ref('dim_job_skills') }}
where trim(skill) = ''
    or skill is null