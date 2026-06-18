with src as (
    select * from {{ ref('dim_job_listings') }}
)

, detail_day as (
    select * from {{ ref('jobs_detail_day') }}
)

, _agg as (
    select
        job_id,
        avg(avg_annual_pay_range) as avg_annual_pay_range,
        min(created_at_utc) as first_seen_at_utc,
        max(created_at_utc) as last_seen_at_utc
    from detail_day
    group by 1
)
, joined as (
    select
        s.* except (low_annual_pay_range, high_annual_pay_range, search_location),
        initcap(search_location) as search_location,
        a.avg_annual_pay_range,
        a.first_seen_at_utc,
        a.last_seen_at_utc
    from src s
    left join _agg a 
        using (job_id)
)

, derive_dates as (
    select *,
        if(
            date_diff(date(current_timestamp()), date(last_seen_at_utc), day) >= 21,
            date_add(date(last_seen_at_utc), interval 1 day),
            cast(null as date)
        ) as removed_date,
        if(
            posted_date_parsed is not null, 
                posted_date_parsed, 
            cast(first_seen_at_utc as date)
        ) as posted_date
    from joined 
)

, add_dims as (
    select *,
        if(
            removed_date is not null,  
            'Removed',
            'Active' 
        ) as listing_status,
        date_diff(cast(last_seen_at_utc as date), coalesce(posted_date, cast(created_at_utc as date)), day) as days_listed,
        case 
            when lower(job_title) like '%principal%' then 'Principal'
            when lower(job_title) like '%distinguished%' then 'Principal'
            when lower(job_title) like '%lead%' then 'Lead'
            when lower(job_title) like '%sr%' then 'Senior'
            when lower(job_title) like '%senior%' then 'Senior'
            when lower(job_title) like '%mid%' then 'Mid Level'
            when lower(job_title) like '%staff%' then 'Staff'
            when lower(job_title) like '% iii' then 'Mid Level'
            when lower(job_title) like '% ii' then 'Mid Level'
            when lower(job_title) like '% 3' then 'Mid Level'
            when lower(job_title) like '%entry%' then 'Entry'
            when lower(job_title) like '%junior%' then 'Entry'
            else null
        end as job_level,
    from derive_dates
)

select * from add_dims
