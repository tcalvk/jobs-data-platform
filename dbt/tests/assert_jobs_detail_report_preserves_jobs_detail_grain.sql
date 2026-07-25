with jobs_detail_counts as (

    select
        count(*) as jobs_detail_total_row_count,
        count(distinct job_id) as jobs_detail_distinct_job_id_count
    from {{ ref('jobs_detail') }}

)

, jobs_detail_report_counts as (

    select
        count(*) as jobs_detail_report_total_row_count,
        count(distinct job_id) as jobs_detail_report_distinct_job_id_count
    from {{ ref('jobs_detail_report') }}

)

select
    jobs_detail_counts.jobs_detail_total_row_count,
    jobs_detail_report_counts.jobs_detail_report_total_row_count,
    jobs_detail_counts.jobs_detail_distinct_job_id_count,
    jobs_detail_report_counts.jobs_detail_report_distinct_job_id_count
from jobs_detail_counts
cross join jobs_detail_report_counts
where jobs_detail_report_counts.jobs_detail_report_total_row_count
        != jobs_detail_counts.jobs_detail_total_row_count
    or jobs_detail_report_counts.jobs_detail_report_distinct_job_id_count
        != jobs_detail_counts.jobs_detail_distinct_job_id_count
