with jobs_detail_day as (

    select *
    from {{ ref('jobs_detail_day') }}

)

, search_term_opportunity_score_month as (

    select
        month_start_date,
        search_term,
        search_location,
        opportunity_score,
        opportunity_tier
    from {{ ref('search_term_opportunity_score_month') }}

)

, joined as (

    select
        jobs_detail_day.*,
        search_term_opportunity_score_month.opportunity_score,
        search_term_opportunity_score_month.opportunity_tier
    from jobs_detail_day
    left join search_term_opportunity_score_month
        on date_trunc(date(jobs_detail_day.created_at_mst), month)
            = search_term_opportunity_score_month.month_start_date
        and jobs_detail_day.search_term = search_term_opportunity_score_month.search_term
        and jobs_detail_day.search_location = search_term_opportunity_score_month.search_location

)

select *
from joined
