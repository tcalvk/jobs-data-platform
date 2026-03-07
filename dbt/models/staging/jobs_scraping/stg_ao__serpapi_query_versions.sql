with source as (
    select 
        query_id,
        q,
        location,
        hl,
        gl,
        max_jobs,
        google_domain,
        active,
        q_plain_text
    from {{ source('ao', 'serpapi_query_versions') }}
)

select * from source