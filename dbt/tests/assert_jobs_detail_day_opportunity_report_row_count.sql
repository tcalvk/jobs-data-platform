with base_count as (

    select count(*) as row_count
    from {{ ref('jobs_detail_day') }}

)

, report_count as (

    select count(*) as row_count
    from {{ ref('jobs_detail_day_opportunity_report') }}

)

select
    base_count.row_count as base_row_count,
    report_count.row_count as report_row_count
from base_count
cross join report_count
where base_count.row_count != report_count.row_count
