select
    query_id,
    max_jobs
from {{ ref('stg_seeds__serpapi_query_versions') }}
where max_jobs is null
    or max_jobs <= 0
