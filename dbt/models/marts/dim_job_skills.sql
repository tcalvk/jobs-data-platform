with _dedupe as (
    select * 
    from {{ ref('stg_ao__enrich_skills') }}
    qualify row_number() over (
        partition by job_id, data_source
        order by created_at desc 
    ) = 1 
)

, raw_skills as (
    select
        job_id,
        data_source,
        upper(trim(skill)) as skill
    from _dedupe
    ,unnest(split(skills, ',')) as skill
)

, _filter_and_dedupe as (
    select *
    from raw_skills
    where skill != ''
    and skill is not null
    qualify row_number() over (
        partition by job_id, data_source, skill
        order by job_id
    ) = 1
)

select * 
from _filter_and_dedupe
