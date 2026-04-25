with source as (
    
    select 
        job_id,
        skills,
        data_source,
        created_at
    from {{ source('ao', 'enrich_skills') }}

)

select * from source