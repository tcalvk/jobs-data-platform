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
        INITCAP(REPLACE(q, '+', ' ')) as q_plain_text
    from {{ ref('serpapi_query_versions') }}
)

select * from source