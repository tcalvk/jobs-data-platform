with source as (
    select
        created_at_utc,
        created_at_mst,
        job_data,
        query_version_id,
        gcs_uri
    from {{ ref('stg_jobs_scraping__serpapi_jobs') }}
),

parsed as (
    select
        created_at_utc,
        created_at_mst,
        JSON_VALUE(job_data, '$.gl') as gl,
        JSON_VALUE(job_data, '$.google_domain') as google_domain,
        JSON_VALUE(job_data, '$.hl') as hl,
        JSON_VALUE(job_data, '$.location') as search_location,
        SAFE_CAST(JSON_VALUE(job_data, '$.page') as INT64) as page,
        JSON_VALUE(job_data, '$.q') as query_text,
        SAFE_CAST(JSON_VALUE(job_data, '$.query_id') as INT64) as query_id,
        JSON_VALUE(job_data, '$.serpapi_json_endpoint') as serpapi_json_endpoint,
        JSON_VALUE(job_data, '$.serpapi_search_id') as serpapi_search_id,
        JSON_VALUE(job_data, '$.source_name') as source_name,
        JSON_VALUE(job_data, '$.job.title') as job_title,
        JSON_VALUE(job_data, '$.job.company_name') as company_name,
        JSON_VALUE(job_data, '$.job.description') as job_description,
        JSON_VALUE(job_data, '$.job.job_id') as job_id,
        JSON_VALUE(job_data, '$.job.location') as job_location,
        JSON_VALUE(job_data, '$.job.via') as job_platform,
        JSON_VALUE(job_data, '$.job.share_link') as job_share_link,
        JSON_VALUE(job_data, '$.job.source_link') as source_link,
        JSON_VALUE(job_data, '$.job.thumbnail') as job_thumbnail,
        JSON_VALUE(job_data, '$.job.detected_extensions.posted_at') as posted_since,
        JSON_VALUE(job_data, '$.job.detected_extensions.schedule_type') as schedule_type,
        JSON_QUERY(job_data, '$.job.apply_options') as apply_options_json,
        JSON_QUERY(job_data, '$.job.extensions') as extensions_json,
        (
            select ext
            from unnest(JSON_VALUE_ARRAY(job_data, '$.job.extensions')) as ext
            where REGEXP_CONTAINS(lower(ext), r'(?:year|hour|week|month)')
            limit 1
        ) as pay_info,
        JSON_QUERY(job_data, '$.job.job_highlights') as job_highlights_json,
        query_version_id,
        gcs_uri,
        job_data
    from source
),

pay_parsed as (
    select
        *,
        REGEXP_EXTRACT_ALL(lower(pay_info), r'\d+(?:\.\d+)?\s*k?') as pay_tokens
    from parsed
),

pay_annualized as (
    select
        *,
        CASE
            WHEN pay_info is null THEN null
            WHEN REGEXP_CONTAINS(lower(pay_info), r'hour') THEN 1920
            WHEN REGEXP_CONTAINS(lower(pay_info), r'month') THEN 12
            WHEN REGEXP_CONTAINS(lower(pay_info), r'week') THEN 52
            ELSE 1
        END as pay_multiplier,
        (
            select
                SAFE_CAST(REGEXP_EXTRACT(tok, r'\d+(?:\.\d+)?') as FLOAT64)
                * CASE WHEN REGEXP_CONTAINS(tok, r'k') THEN 1000 ELSE 1 END
            from unnest(pay_tokens) as tok
            with offset as off
            where off = 0
        ) as low_pay_raw,
        (
            select
                SAFE_CAST(REGEXP_EXTRACT(tok, r'\d+(?:\.\d+)?') as FLOAT64)
                * CASE WHEN REGEXP_CONTAINS(tok, r'k') THEN 1000 ELSE 1 END
            from unnest(pay_tokens) as tok
            with offset as off
            where off = 1
        ) as high_pay_raw
    from pay_parsed
),

pay_ranges as (
    select
        *,
        COALESCE(high_pay_raw, low_pay_raw) as high_pay_base,
        low_pay_raw as low_pay_base
    from pay_annualized
),

posted_since_parsed as (
    select
        *,
        safe_cast(regexp_extract(lower(posted_since), r'\d+') as int64) as posted_since_quantity,
        lower(to_json_string(job_data)) as job_data_lower
    from pay_ranges
),

final_transform as (
    select
        created_at_utc,
        created_at_mst,
        gl,
        google_domain,
        hl,
        search_location,
        page,
        query_text,
        query_id,
        serpapi_json_endpoint,
        serpapi_search_id,
        source_name,
        job_id as platform_job_id,
        job_title,
        company_name,
        job_description,
        job_location,
        job_platform,
        job_share_link,
        source_link,
        job_thumbnail,
        posted_since,
        case
            when regexp_contains(lower(posted_since), r'hour') then
                cast(
                    timestamp_sub(
                        timestamp(created_at_utc),
                        interval posted_since_quantity hour
                    ) as date
                )
            when regexp_contains(lower(posted_since), r'day') then
                date_sub(
                    cast(created_at_mst as date),
                    interval posted_since_quantity day
                )
            when regexp_contains(lower(posted_since), r'week') then
                date_sub(
                    cast(created_at_mst as date),
                    interval posted_since_quantity week
                )
            when regexp_contains(lower(posted_since), r'month') then
                date_sub(
                    cast(created_at_mst as date),
                    interval posted_since_quantity month
                )
        end as posted_date_parsed,
        schedule_type,
        apply_options_json,
        extensions_json,
        low_pay_base * pay_multiplier as low_annual_pay_range,
        high_pay_base * pay_multiplier as high_annual_pay_range,
        job_highlights_json,
        query_version_id,
        gcs_uri,
        job_data,
        case
            when regexp_contains(
                job_data_lower,
                r'\b(ph\.?d\.?|p\.?h\.?d\.?|doctorate|doctoral)\b'
            ) then 'Doctorate'

            when regexp_contains(
                job_data_lower,
                r'\b(master\'?s?|masters?|master degree|master\'?s degree|mba|m\.s\.|m\.a\.|m\.sc\.?)\b'
            ) then 'Master\'s'

            when regexp_contains(
                job_data_lower,
                r'\b(bachelor\'?s?|bachelors?|bachelor degree|bachelor\'?s degree|b\.s\.|b\.a\.|b\.sc\.?|undergraduate degree|4[- ]year degree)\b'
            ) then 'Bachelor\'s'

            when regexp_contains(
                job_data_lower,
                r'\b(associate\'?s?|associates?|associate degree|associate\'?s degree|a\.s\.|a\.a\.|2[- ]year degree)\b'
            ) then 'Associate\'s'

            when regexp_contains(
                job_data_lower,
                r'\b(high school diploma|high school degree|ged)\b'
            ) then 'High School'

            else 'Degree Not Specified'
        end as degree_requirement,
        'Serpapi' as data_source,
    from posted_since_parsed
)

select 
    ft.*,
    qv.q_plain_text as search_term
from final_transform ft 
left join {{ ref('stg_seeds__serpapi_query_versions') }} qv
    using (query_id)
