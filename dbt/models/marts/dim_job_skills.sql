with _dedupe as (
    select * 
    from {{ ref('stg_ao__enrich_skills') }}
    qualify row_number() over (
        partition by job_id, data_source
        order by created_at desc 
    ) = 1 
)

,raw_skills as (
    select
        job_id,
        data_source,
        upper(trim(skill)) as skill
    from _dedupe
    ,unnest(split(skills, ',')) as skill
)

select * 
from raw_skills 
