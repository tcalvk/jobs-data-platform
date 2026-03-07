with source as (
    
    select 
        created_at,
        job_data,
        query_version_id,
        gcs_uri
    from {{ source('jobs_scraping', 'serpapi_jobs') }}

),

renamed as (

    select
        created_at as created_at_utc,
        DATETIME(TIMESTAMP(created_at), "America/Denver") as created_at_mst,
        job_data,
        query_version_id,
        gcs_uri
    from source

)

select * from renamed