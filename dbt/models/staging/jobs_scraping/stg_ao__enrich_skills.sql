with source as (
    
    select 
        job_id,
        skills
    from {{ source('ao', 'enrich_skills') }}

)

select * from source