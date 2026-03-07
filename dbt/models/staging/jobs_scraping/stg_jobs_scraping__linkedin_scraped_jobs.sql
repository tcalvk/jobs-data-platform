with source as (
    
    select 
        job_id,
        job_description,
        created_at,
        search_term,
        job_location,
        job_title,
        listing_details,
        fit_level_preferences
    from {{ source('jobs_scraping', 'linkedin_scraped_jobs') }}

),

renamed as (

    select
        job_id,
        job_description,
        created_at as created_at_utc,
        DATETIME(TIMESTAMP(created_at), "America/Denver") as created_at_mst,
        search_term,
        job_location as search_job_location,
        job_title,
        listing_details,
        fit_level_preferences
    from source

)

select * from renamed