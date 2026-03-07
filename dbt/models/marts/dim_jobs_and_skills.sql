with raw_skills as (
    select
        job_id,
        upper(trim(skill)) as skill
    FROM {{ ref('stg_ao__enrich_skills') }}
    ,unnest(split(skills, ',')) as skill
)

,remove_strings as (
    select * 
    from raw_skills 
    where 1=1 
    and (
        skill not like '%YEARS%' and
        skill not like '%DEGREE%' and 
        skill != ' '
    )
)

select * 
from remove_strings 
