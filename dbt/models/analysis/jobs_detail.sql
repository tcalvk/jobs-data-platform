with src as (
    select * from {{ ref('dim_job_listings') }}
)

, detail as (
    select * from {{ ref('jobs_detail_day') }}
)

, _join as (
    select 
        s.* except (job_description, search_location),
        d.job_level,
        d.search_location,
        avg(d.avg_annual_pay_range) as avg_annual_pay_range
    from src s
    left join detail d 
        using (job_id)
    qualify row_number() over(
        partition by d.job_id
        order by d.created_at_utc asc 
    )
)

, derive_removed_date as (
    select *,
        if(
            date_diff(date(current_timestamp()), date(last_seen_at_utc), day) >= 21,
             date_add(date(last_seen_at_utc), interval 1 day),
             cast(null as date)
        ) as removed_date
    from src 
)

, add_listing_info as (
    select *,
        if(
            removed_date is not null,  
            'Removed',
            'Active' 
        ) as listing_status,
        date_diff(cast(last_seen_at_utc as date), coalesce(posted_date, cast(created_at_utc as date)), day) as days_listed
    from derive_removed_date
)

select * from add_listing_info
