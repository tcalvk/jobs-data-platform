{{ config(materialized='table') }}

with job_detail as (

    select *
    from {{ ref('jobs_detail') }}

)

, job_segments as (

    select distinct
        search_term,
        search_location
    from job_detail
    where search_term is not null
        and search_location is not null

)

, date_bounds as (

    select
        coalesce(
            date_trunc(min(date(created_at_mst)), month),
            date_trunc(current_date('America/Denver'), month)
        ) as min_month,
        date_trunc(current_date('America/Denver'), month) as max_month
    from job_detail

)

, month_spine as (

    select
        month_start_date
    from date_bounds,
        unnest(generate_date_array(min_month, max_month, interval 1 month)) as month_start_date

)

, segment_month_spine as (

    select
        m.month_start_date,
        s.search_term,
        s.search_location
    from month_spine as m
    cross join job_segments as s

)

, monthly_active_jobs as (

    select
        b.month_start_date,
        b.search_term,
        b.search_location,
        count(distinct j.job_id) as active_jobs_count
    from segment_month_spine as b
    left join job_detail as j
        on b.search_term = j.search_term
        and b.search_location = j.search_location
        and j.posted_date <= last_day(b.month_start_date)
        and (
            j.removed_date is null
            or j.removed_date >= b.month_start_date
        )
    group by 1, 2, 3

)

, demand_calc as (

    select
        month_start_date,
        search_term,
        search_location,
        active_jobs_count,
        ln(1 + active_jobs_count) as log_active_jobs_count
    from monthly_active_jobs

)

, demand_scored as (

    select
        month_start_date,
        search_term,
        search_location,
        active_jobs_count,
        case
            when max(log_active_jobs_count) over (
                partition by month_start_date, search_location
            ) = min(log_active_jobs_count) over (
                partition by month_start_date, search_location
            ) then case
                -- All-zero locations should not earn full demand credit solely because
                -- every search term tied at zero active jobs.
                when max(active_jobs_count) over (
                    partition by month_start_date, search_location
                ) = 0 then 0
                else 100
            end
            else safe_divide(
                log_active_jobs_count - min(log_active_jobs_count) over (
                    partition by month_start_date, search_location
                ),
                max(log_active_jobs_count) over (
                    partition by month_start_date, search_location
                ) - min(log_active_jobs_count) over (
                    partition by month_start_date, search_location
                )
            ) * 100
        end as demand_score
    from demand_calc

)

, monthly_new_jobs as (

    select
        date_trunc(date(created_at_mst), month) as month_start_date,
        search_term,
        search_location,
        count(distinct job_id) as new_jobs_count
    from job_detail
    where created_at_mst is not null
        and search_term is not null
        and search_location is not null
    group by 1, 2, 3

)

, filled_new_jobs as (

    select
        b.month_start_date,
        b.search_term,
        b.search_location,
        coalesce(n.new_jobs_count, 0) as new_jobs_count
    from segment_month_spine as b
    left join monthly_new_jobs as n
        on b.month_start_date = n.month_start_date
        and b.search_term = n.search_term
        and b.search_location = n.search_location

)

, with_prior_month as (

    select
        month_start_date,
        search_term,
        search_location,
        new_jobs_count,
        coalesce(
            lag(new_jobs_count) over (
                partition by search_term, search_location
                order by month_start_date
            ),
            0
        ) as prior_month_new_jobs_count
    from filled_new_jobs

)

, growth_calc as (

    select
        month_start_date,
        search_term,
        search_location,
        new_jobs_count,
        prior_month_new_jobs_count,
        safe_divide(
            new_jobs_count - prior_month_new_jobs_count,
            prior_month_new_jobs_count + 1
        ) as smoothed_monthly_growth_rate,
        safe_divide(
            new_jobs_count - prior_month_new_jobs_count,
            prior_month_new_jobs_count + 1
        ) * ln(1 + new_jobs_count) as weighted_growth,
        month_start_date = date_trunc(current_date('America/Denver'), month) as is_partial_month
    from with_prior_month

)

, growth_scored as (

    select
        month_start_date,
        search_term,
        search_location,
        new_jobs_count,
        prior_month_new_jobs_count,
        smoothed_monthly_growth_rate,
        weighted_growth,
        case
            when new_jobs_count = 0
                and prior_month_new_jobs_count = 0 then 0
            when max(weighted_growth) over (
                partition by month_start_date, search_location
            ) = min(weighted_growth) over (
                partition by month_start_date, search_location
            ) then case
                -- All-zero current and prior activity should not earn full growth
                -- credit solely because every search term tied at zero growth.
                when max(new_jobs_count) over (
                    partition by month_start_date, search_location
                ) = 0
                    and max(prior_month_new_jobs_count) over (
                        partition by month_start_date, search_location
                    ) = 0 then 0
                else 100
            end
            else least(100, greatest(0, safe_divide(
                weighted_growth - min(weighted_growth) over (
                    partition by month_start_date, search_location
                ),
                max(weighted_growth) over (
                    partition by month_start_date, search_location
                ) - min(weighted_growth) over (
                    partition by month_start_date, search_location
                )
            ) * 100))
        end as growth_score,
        is_partial_month
    from growth_calc

)

, salary_source_jobs as (

    select
        j.job_id,
        date_trunc(date(j.created_at_mst), month) as month_start_date,
        j.search_term,
        j.search_location,
        case
            when j.avg_annual_pay_range is not null then cast(j.avg_annual_pay_range as float64)
            when pay_range.low_annual_pay_range is not null
                and pay_range.high_annual_pay_range is not null
                then (pay_range.low_annual_pay_range + pay_range.high_annual_pay_range) / 2
            when pay_range.low_annual_pay_range is not null then pay_range.low_annual_pay_range
            when pay_range.high_annual_pay_range is not null then pay_range.high_annual_pay_range
        end as salary_estimate
    from job_detail as j
    cross join unnest([
        struct(
            safe_cast(json_value(to_json_string(j), '$.low_annual_pay_range') as float64) as low_annual_pay_range,
            safe_cast(json_value(to_json_string(j), '$.high_annual_pay_range') as float64) as high_annual_pay_range
        )
    ]) as pay_range
    where j.created_at_mst is not null
        and j.search_term is not null
        and j.search_location is not null

)

, monthly_salary as (

    select
        month_start_date,
        search_term,
        search_location,
        count(distinct job_id) as salary_total_jobs_count,
        count(distinct case
            when salary_estimate is not null then job_id
        end) as jobs_with_salary_count,
        avg(salary_estimate) as avg_salary,
        approx_quantiles(salary_estimate, 100 ignore nulls)[offset(50)] as median_salary
    from salary_source_jobs
    group by 1, 2, 3

)

, salary_coverage as (

    select
        *,
        safe_divide(jobs_with_salary_count, salary_total_jobs_count) as salary_coverage_pct
    from monthly_salary

)

, salary_scored as (

    select
        month_start_date,
        search_term,
        search_location,
        salary_total_jobs_count,
        jobs_with_salary_count,
        salary_coverage_pct,
        avg_salary,
        median_salary,
        case
            when avg_salary is null then null
            when max(avg_salary) over (
                partition by month_start_date, search_location
            ) = min(avg_salary) over (
                partition by month_start_date, search_location
            ) then 100
            else least(100, greatest(0, safe_divide(
                avg_salary - min(avg_salary) over (
                    partition by month_start_date, search_location
                ),
                max(avg_salary) over (
                    partition by month_start_date, search_location
                ) - min(avg_salary) over (
                    partition by month_start_date, search_location
                )
            ) * 100))
        end as salary_score
    from salary_coverage

)

, company_job_counts as (

    select
        date_trunc(date(created_at_mst), month) as month_start_date,
        search_term,
        search_location,
        trim(company_name) as company_name,
        count(distinct job_id) as company_jobs_count
    from job_detail
    where created_at_mst is not null
        and search_term is not null
        and search_location is not null
        and nullif(trim(company_name), '') is not null
    group by 1, 2, 3, 4

)

, ranked_companies as (

    select
        *,
        row_number() over (
            partition by month_start_date, search_term, search_location
            order by company_jobs_count desc, company_name
        ) as company_rank
    from company_job_counts

)

, long_tail_scored as (

    select
        month_start_date,
        search_term,
        search_location,
        sum(company_jobs_count) as long_tail_total_jobs_count,
        count(distinct company_name) as company_count,
        sum(case
            when company_rank <= 10 then company_jobs_count
            else 0
        end) as top_10_company_jobs_count,
        sum(case
            when company_rank > 10 then company_jobs_count
            else 0
        end) as long_tail_jobs_count,
        safe_divide(
            sum(case
                when company_rank <= 10 then company_jobs_count
                else 0
            end),
            sum(company_jobs_count)
        ) as top_10_company_share,
        safe_divide(
            sum(case
                when company_rank > 10 then company_jobs_count
                else 0
            end),
            sum(company_jobs_count)
        ) as long_tail_share,
        safe_divide(
            sum(case
                when company_rank > 10 then company_jobs_count
                else 0
            end),
            sum(company_jobs_count)
        ) * 100 as long_tail_score
    from ranked_companies
    group by 1, 2, 3

)

, joined as (

    select
        d.month_start_date,
        d.month_start_date as month,
        d.search_term,
        d.search_location,
        d.active_jobs_count,
        d.demand_score,
        g.new_jobs_count,
        g.prior_month_new_jobs_count,
        g.smoothed_monthly_growth_rate,
        g.weighted_growth,
        g.growth_score,
        s.salary_total_jobs_count,
        s.jobs_with_salary_count,
        s.salary_coverage_pct,
        s.avg_salary,
        s.median_salary,
        s.salary_score,
        l.long_tail_total_jobs_count,
        l.company_count,
        l.top_10_company_jobs_count,
        l.long_tail_jobs_count,
        l.top_10_company_share,
        l.long_tail_share,
        l.long_tail_score,
        g.is_partial_month
    from demand_scored as d
    left join growth_scored as g
        on d.month_start_date = g.month_start_date
        and d.search_term = g.search_term
        and d.search_location = g.search_location
    left join salary_scored as s
        on d.month_start_date = s.month_start_date
        and d.search_term = s.search_term
        and d.search_location = s.search_location
    left join long_tail_scored as l
        on d.month_start_date = l.month_start_date
        and d.search_term = l.search_term
        and d.search_location = l.search_location

)

, weighted as (

    select
        *,
        (
            coalesce(demand_score * 0.30, 0)
            + coalesce(growth_score * 0.30, 0)
            + coalesce(salary_score * 0.25, 0)
            + coalesce(long_tail_score * 0.15, 0)
        ) as available_weighted_score_sum,
        (
            case when demand_score is not null then 0.30 else 0 end
            + case when growth_score is not null then 0.30 else 0 end
            + case when salary_score is not null then 0.25 else 0 end
            + case when long_tail_score is not null then 0.15 else 0 end
        ) as available_weight_sum
    from joined

)

, final as (

    select
        month_start_date,
        month,
        search_term,
        search_location,
        active_jobs_count,
        new_jobs_count,
        prior_month_new_jobs_count,
        smoothed_monthly_growth_rate,
        weighted_growth,
        salary_total_jobs_count,
        jobs_with_salary_count,
        salary_coverage_pct,
        avg_salary,
        median_salary,
        long_tail_total_jobs_count,
        company_count,
        top_10_company_jobs_count,
        long_tail_jobs_count,
        top_10_company_share,
        long_tail_share,
        demand_score,
        growth_score,
        salary_score,
        long_tail_score,
        least(100, greatest(0, safe_divide(
            available_weighted_score_sum,
            available_weight_sum
        ))) as opportunity_score,
        case
            when safe_divide(available_weighted_score_sum, available_weight_sum) >= 80
                then 'Strong Opportunity'
            when safe_divide(available_weighted_score_sum, available_weight_sum) >= 60
                then 'Good Opportunity'
            when safe_divide(available_weighted_score_sum, available_weight_sum) >= 40
                then 'Moderate Opportunity'
            when safe_divide(available_weighted_score_sum, available_weight_sum) is null
                then 'Insufficient Data'
            else 'Weak Opportunity'
        end as opportunity_tier,
        is_partial_month
    from weighted

)

select *
from final
