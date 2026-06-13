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

select * from filter_skills
