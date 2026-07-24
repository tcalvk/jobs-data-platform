{% set partitions_to_replace = generate_partitions_to_replace() %}

{{
    config(
        materialized='incremental',
        partition_by={
            "field": "created_date",
            "data_type": "date",
            "granularity": "day"
        },
        incremental_strategy='insert_overwrite',
        partitions=partitions_to_replace,
        on_schema_change='fail'
    )
}}

with src as (
    select 
        job_id,
        job_description,
        created_at_utc,
        created_at_mst,
        search_term,
        search_job_location,
        job_title,
        listing_details,
        fit_level_preferences
    from {{ ref('stg_jobs_scraping__linkedin_scraped_jobs') }} 
    {% if is_incremental() %}
    where cast(created_at_utc as date) in ({{ partitions_to_replace | join(', ') }})
    {% endif %}
),

parse as (
    select 
        job_id
        ,job_title
        ,created_at_utc
        ,created_at_mst
        ,search_term
        ,search_job_location
        ,split(listing_details, '·') [SAFE_OFFSET(0)] as job_location
        ,split(listing_details, '·') [SAFE_OFFSET(1)] as posted_since
        ,case 
            when split(listing_details, '·') [SAFE_OFFSET(1)] not like '%Reposted%' then 
                case 
                    when split(listing_details, '·') [SAFE_OFFSET(1)] like '%hour%' 
                        then cast( date_add(created_at_utc, interval - safe_cast(split(split(listing_details, '·') [SAFE_OFFSET(1)], 'hour') [SAFE_OFFSET(0)] as int64) hour) as date)
                    when split(listing_details, '·') [SAFE_OFFSET(1)] like '%day%' 
                        then cast( date_add(created_at_utc, interval - safe_cast(split(split(listing_details, '·') [SAFE_OFFSET(1)], 'day') [SAFE_OFFSET(0)] as int64) day) as date)
                    when split(listing_details, '·') [SAFE_OFFSET(1)] like '%week%' 
                        then cast( date_add(cast(created_at_utc as date), interval - safe_cast(split(split(listing_details, '·') [SAFE_OFFSET(1)], 'week') [SAFE_OFFSET(0)] as int64) week) as date)
                    when split(listing_details, '·') [SAFE_OFFSET(1)] like '%month%' 
                        then cast( date_add(cast(created_at_utc as date), interval - safe_cast(split(split(listing_details, '·') [SAFE_OFFSET(1)], 'month') [SAFE_OFFSET(0)] as int64) month) as date)
                    else null 
                end 
            else 
                case
                    when split(listing_details, '·') [SAFE_OFFSET(1)] like '%hour%'
                        then cast(date_add(created_at_utc, interval - safe_cast( split( split(listing_details, '·') [SAFE_OFFSET(1)], ' ') [SAFE_OFFSET(2)] as int64) hour) as date)
                    when split(listing_details, '·') [SAFE_OFFSET(1)] like '%day%'
                        then cast(date_add(created_at_utc, interval - safe_cast( split( split(listing_details, '·') [SAFE_OFFSET(1)], ' ') [SAFE_OFFSET(2)] as int64) day) as date)
                    when split(listing_details, '·') [SAFE_OFFSET(1)] like '%week%'
                        then cast(date_add(cast(created_at_utc as date), interval - safe_cast( split( split(listing_details, '·') [SAFE_OFFSET(1)], ' ') [SAFE_OFFSET(2)] as int64) week) as date)
                    when split(listing_details, '·') [SAFE_OFFSET(1)] like '%month%'
                        then cast(date_add(cast(created_at_utc as date), interval - safe_cast( split( split(listing_details, '·') [SAFE_OFFSET(1)], ' ') [SAFE_OFFSET(2)] as int64) month) as date)
                    else null 
                end  
        end as posted_date_parsed 
        ,case 
            when lower(fit_level_preferences) like '%full%' then 'Full-time'
            when lower(fit_level_preferences) like '%part%' then 'Part-time'
            when lower(fit_level_preferences) like '%contract%' then 'Contract'
            when lower(fit_level_preferences) like '%intern%' then 'Internship'
            else null 
        end as schedule_type 
        ,case 
            when lower(fit_level_preferences) like '%remote%' then 'Remote'
            when lower(fit_level_preferences) like '%hybrid%' then 'Hybrid'
            when lower(fit_level_preferences) like '%on-site%' then 'On-site'
            else null 
        end as work_location 
        ,CASE
            WHEN REGEXP_CONTAINS(fit_level_preferences, r'K') THEN CAST(REGEXP_EXTRACT(fit_level_preferences, r'\$(\d+(?:,\d{3})?)') AS INT64) * 1000
            WHEN REGEXP_CONTAINS(fit_level_preferences, r'/hr') THEN CAST(REGEXP_EXTRACT(fit_level_preferences, r'\$(\d+(?:,\d{3})?)') AS INT64) * 1920
            ELSE CAST(REGEXP_EXTRACT(fit_level_preferences, r'\$(\d+(?:,\d{3})?)') AS INT64)
        END AS low_annual_pay_range
        ,CASE
            WHEN REGEXP_CONTAINS(fit_level_preferences, r'-.*K') THEN CAST(REGEXP_EXTRACT(fit_level_preferences, r'-\s*\$(\d+(?:,\d{3})?)') AS INT64) * 1000
            WHEN REGEXP_CONTAINS(fit_level_preferences, r'-.*?/hr') THEN CAST(REGEXP_EXTRACT(fit_level_preferences, r'-\s*\$(\d+(?:,\d{3})?)') AS INT64) * 1920
            ELSE CAST(REGEXP_EXTRACT(fit_level_preferences, r'-\s*\$(\d+(?:,\d{3})?)') AS INT64)
    END AS high_annual_pay_range
    ,job_description
    ,'LinkedIn' as data_source,
    cast(null as string) as company_name,
    'LinkedIn' as job_platform,
    cast(null as string) as degree_requirement,
    from src
),

final_transform as (
    select 
        job_id as platform_job_id,
        job_title,
        created_at_utc,
        created_at_mst,
        cast(created_at_utc as date) as created_date,
        company_name,
        search_term,
        search_job_location as search_location,
        job_platform,
        job_location,
        posted_since,
        posted_date_parsed,
        schedule_type,
        work_location,
        low_annual_pay_range,
        high_annual_pay_range,
        job_description,
        data_source,
        cast(null as string) as degree_requirement,
        cast(null as string) as source_link
    from parse
)

select * from final_transform
