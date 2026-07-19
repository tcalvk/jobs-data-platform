---
title: Market Dynamics
full_width: true
sidebar: hide
hide_toc: true
hide_breadcrumbs: true
---

<script>
  import JobTitleTokenInput from '../../components/JobTitleTokenInput.svelte';

  let showMoreFilters = false;
</script>

<style>
  .market-dynamics-page {
    background: #e9eef1;
    box-sizing: border-box;
    margin: 0;
    padding: 1.1rem 1.1rem 1.75rem 1.1rem;
    min-height: 100vh;
    width: 100%;
  }

  .filter-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.9rem 1.35rem;
    align-items: end;
    margin-bottom: 1.2rem;
  }

  .filter-grid :global(.inline-block) {
    width: 100%;
    min-width: 0;
    max-width: 100%;
    margin: 0 !important;
  }

  .filter-grid :global(.inline-block button) {
    width: 100%;
    min-width: 0 !important;
    max-width: 100%;
    justify-content: space-between;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    background: #ffffff !important;
    color: #263238 !important;
    border-color: #cbd5e1 !important;
  }

  .filter-grid :global(.inline-block label),
  .filter-grid :global(.inline-block p),
  .filter-grid :global(.inline-block span),
  .filter-grid :global(input) {
    color: #263238 !important;
  }

  .filter-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin: -0.55rem 0 1.2rem 0;
  }

  .reset-filters-button,
  .more-filters-toggle {
    border: 1px solid #cbd5e1;
    border-radius: 0.375rem;
    background: #ffffff;
    color: #263238;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.35rem 0.7rem;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
  }

  .reset-filters-button:hover,
  .reset-filters-button:focus-visible,
  .more-filters-toggle:hover,
  .more-filters-toggle:focus-visible {
    border-color: #2563eb;
    outline: none;
  }

  .more-filter-grid {
    margin-top: -0.35rem;
  }

  .filters-hidden {
    display: none;
  }

  .filter-grid :global(input) {
    background: #ffffff !important;
    border-color: #cbd5e1 !important;
  }

  .filter-grid :global(svg) {
    flex: 0 0 auto;
    color: #263238 !important;
  }

  :global([data-theme='dark']) .filter-grid :global(.bg-base-200),
  :global([data-theme='dark']) .filter-grid :global(span.rounded-sm) {
    background-color: #f8fafc !important;
    border-color: #94a3b8 !important;
    color: #0f172a !important;
  }

  :global([data-theme='dark']) .filter-grid :global(.text-base-content),
  :global([data-theme='dark']) .filter-grid :global(.text-base-content *) {
    color: #0f172a !important;
  }

  :global([data-theme='dark']) .reset-filters-button,
  :global([data-theme='dark']) .more-filters-toggle {
    background: #18181b;
    border-color: #3f3f46;
    color: #ffffff;
  }

  .chart-card {
    background: white;
    margin-top: 1.2rem;
    padding: 0.7rem 0.75rem 0.45rem 0.75rem;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
  }

  .chart-split-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
    align-items: stretch;
  }

  .section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #263238;
    margin: 0 0 0.35rem 0;
  }

  .chart-no-data {
    min-height: 18rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #475569;
    font-size: 0.9rem;
    text-align: center;
  }

  :global(.over-container) {
    display: none !important;
  }

  @media (max-width: 900px) {
    .filter-grid,
    .chart-split-grid {
      grid-template-columns: 1fr;
    }

    .market-dynamics-page {
      margin-left: 0;
      margin-right: 0;
    }
  }
</style>

```sql available_dates
select distinct posted_date
from project_portfolio.jobs_detail_report
where posted_date is not null
```

```sql search_terms
with options as (
    select
        search_term,
        search_term as search_term_label,
        row_number() over (order by search_term) as option_rank
    from (
        select distinct search_term
        from project_portfolio.jobs_detail_report
        where search_term is not null
    )
)
select 'All' as search_term, '𝐀𝐥𝐥 Values' as search_term_label, 0 as ordinal
union all
select search_term, search_term_label, option_rank as ordinal
from options
order by ordinal
```

```sql search_locations
select 'All' as search_location, '𝐀𝐥𝐥 Values' as search_location_label, 0 as ordinal
union all
select 'United States' as search_location, 'United States' as search_location_label, 1 as ordinal
order by ordinal
```

```sql job_location_states
with options as (
    select
        state_name as job_location_state,
        state_name as job_location_state_label,
        row_number() over (order by state_name) as option_rank
    from (
        select distinct state_name
        from project_portfolio.jobs_detail_report
        where state_name is not null
    )
)
select 'All' as job_location_state, '𝐀𝐥𝐥 Values' as job_location_state_label, 0 as ordinal
union all
select job_location_state, job_location_state_label, option_rank as ordinal
from options
order by ordinal
```

```sql job_platforms
with platform_counts as (
    select
        job_platform,
        count(distinct job_id) as record_count
    from project_portfolio.jobs_detail_report
    where job_platform is not null
    group by 1
), options as (
    select
        job_platform,
        job_platform || ' (' || cast(record_count as varchar) || ')' as job_platform_label,
        record_count,
        row_number() over (order by record_count desc, job_platform) as option_rank
    from platform_counts
)
select
    'All' as job_platform,
    '𝐀𝐥𝐥 Values' as job_platform_label,
    null as record_count,
    0 as ordinal
union all
select
    job_platform,
    job_platform_label,
    record_count,
    option_rank as ordinal
from options
order by ordinal
```

```sql listing_statuses
with options as (
    select
        listing_status,
        listing_status as listing_status_label,
        row_number() over (order by listing_status) as option_rank
    from (
        select distinct listing_status
        from project_portfolio.jobs_detail_report
        where listing_status is not null
    )
)
select 'All' as listing_status, '𝐀𝐥𝐥 Values' as listing_status_label, 0 as ordinal
union all
select listing_status, listing_status_label, option_rank as ordinal
from options
order by ordinal
```

```sql job_levels
with options as (
    select
        job_level,
        job_level as job_level_label,
        row_number() over (order by job_level) as option_rank
    from (
        select distinct job_level
        from project_portfolio.jobs_detail_report
        where job_level is not null
    )
)
select 'All' as job_level, '𝐀𝐥𝐥 Values' as job_level_label, 0 as ordinal
union all
select job_level, job_level_label, option_rank as ordinal
from options
order by ordinal
```

```sql degree_requirements
with options as (
    select
        degree_requirement,
        degree_requirement as degree_requirement_label,
        row_number() over (order by degree_requirement) as option_rank
    from (
        select distinct degree_requirement
        from project_portfolio.jobs_detail_report
        where degree_requirement is not null
    )
)
select 'All' as degree_requirement, '𝐀𝐥𝐥 Values' as degree_requirement_label, 0 as ordinal
union all
select degree_requirement, degree_requirement_label, option_rank as ordinal
from options
order by ordinal
```

```sql job_title_match_methods
select 'contains' as match_method, 'Contains' as match_method_label, 0 as ordinal
union all
select 'is' as match_method, 'Is' as match_method_label, 1 as ordinal
union all
select 'does_not_contain' as match_method, 'Does Not Contain' as match_method_label, 2 as ordinal
order by ordinal
```

<div class="market-dynamics-page">

<div class="filter-grid">
  <Dropdown data={search_terms} name=search_term value=search_term label=search_term_label order=ordinal title="Search Term" defaultValue="All" />
  <Dropdown data={job_platforms} name=job_platform value=job_platform label=job_platform_label order=ordinal title="Job Platform" defaultValue="All" />
  <Dropdown data={listing_statuses} name=listing_status value=listing_status label=listing_status_label order=ordinal title="Listing Status" defaultValue="All" />
  <DateRange name=posted_window data={available_dates} dates=posted_date defaultValue="Last 90 Days" />
  <Dropdown data={job_location_states} name=job_location_state value=job_location_state label=job_location_state_label order=ordinal title="Job Location State" multiple=true defaultValue={['All']} />
  <Dropdown data={job_levels} name=job_level value=job_level label=job_level_label order=ordinal title="Job Level" defaultValue="All" />
  <Dropdown data={degree_requirements} name=degree_requirement value=degree_requirement label=degree_requirement_label order=ordinal title="Degree Requirement" defaultValue="All" />
</div>

<div class="filter-actions">
  <button class="reset-filters-button" type="button" on:click={() => globalThis.location.assign(globalThis.location.pathname)}>
    Reset Filters
  </button>
  <button class="more-filters-toggle" type="button" on:click={() => showMoreFilters = !showMoreFilters} aria-expanded={showMoreFilters}>
    {showMoreFilters ? 'Hide More Filters' : 'More Filters'}
  </button>
</div>

<div class="filter-grid more-filter-grid" class:filters-hidden={!showMoreFilters}>
  <Dropdown data={search_locations} name=search_location value=search_location label=search_location_label order=ordinal title="Search Location" defaultValue="United States" />
  <Dropdown data={job_title_match_methods} name=job_title_match_method value=match_method label=match_method_label order=ordinal title="Job Title Match" defaultValue="contains" />
  <JobTitleTokenInput name="job_title_filter" title="Job Title" />
  <Dropdown data={job_title_match_methods} name=company_name_match_method value=match_method label=match_method_label order=ordinal title="Company Name Match" defaultValue="contains" />
  <JobTitleTokenInput name="company_name_filter" title="Company Name" placeholder="Type a company and press Enter" />
</div>

```sql active_job_concentration_by_company
with filtered_jobs as (
    select
        job_id,
        case
            when nullif(trim(company_name), '') is null then 'synthetic:missing-company'
            else 'company:' || trim(company_name)
        end as company_key,
        case
            when nullif(trim(company_name), '') is null then 'Company Not Specified (Missing)'
            when trim(company_name) = 'Others' then 'Others (Company)'
            else trim(company_name)
        end as display_name,
        coalesce(nullif(trim(company_name), ''), '') as company_sort_name
    from project_portfolio.jobs_detail_report
    where listing_status = 'Active'
      and posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
      and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
      and ('${inputs.job_level.value}' = 'All' or job_level = '${inputs.job_level.value}')
      and ('${inputs.degree_requirement.value}' = 'All' or degree_requirement = '${inputs.degree_requirement.value}')
      and (
          trim(${inputs.job_title_filter.sql}) = ''
          or (
              '${inputs.job_title_match_method.value}' = 'is'
              and lower(coalesce(job_title, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.job_title_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.job_title_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          trim(${inputs.company_name_filter.sql}) = ''
          or (
              '${inputs.company_name_match_method.value}' = 'is'
              and lower(coalesce(company_name, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.company_name_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.company_name_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
      and ('All' in ${inputs.job_location_state.value} or state_name in ${inputs.job_location_state.value})
      and ('${inputs.job_platform.value}' = 'All' or job_platform = '${inputs.job_platform.value}')
), company_counts as (
    select
        company_key,
        display_name,
        company_sort_name,
        count(distinct job_id) as active_job_count
    from filtered_jobs
    group by 1, 2, 3
), ranked_companies as (
    select
        company_key,
        display_name,
        active_job_count,
        row_number() over (
            order by active_job_count desc, company_sort_name asc, company_key asc
        ) as company_rank
    from company_counts
), chart_slices as (
    select
        company_key as name,
        display_name,
        active_job_count,
        company_rank as display_order
    from ranked_companies
    where company_rank <= 20

    union all

    select
        'synthetic:tail' as name,
        'Others' as display_name,
        sum(active_job_count) as active_job_count,
        21 as display_order
    from ranked_companies
    where company_rank > 20
    having count(*) > 0
), totals as (
    select count(distinct job_id) as total_active_jobs
    from filtered_jobs
)
select
    name,
    display_name,
    active_job_count as value,
    active_job_count,
    round(100.0 * active_job_count / nullif(total_active_jobs, 0), 1) as percentage
from chart_slices
cross join totals
order by display_order, display_name
```

<div class="chart-card">
  <div class="section-title">Active Job Concentration by Company</div>
  {#if active_job_concentration_by_company.length > 0}
  <ECharts config={
    {
      baseOption: {
        tooltip: {
          trigger: 'item',
          formatter: (params) => `${params.data.display_name}<br/>Active Jobs: ${Number(params.data.active_job_count).toLocaleString()}<br/>Share: ${Number(params.data.percentage).toFixed(1)}%`
        },
        legend: {
          type: 'scroll',
          orient: 'vertical',
          right: 10,
          top: 20,
          bottom: 20,
          formatter: (name) => [...active_job_concentration_by_company].find((row) => row.name === name)?.display_name ?? name
        },
        series: [
          {
            type: 'pie',
            radius: ['45%', '72%'],
            center: ['38%', '50%'],
            avoidLabelOverlap: true,
            label: {
              show: false
            },
            emphasis: {
              label: {
                show: true,
                fontWeight: 'bold',
                formatter: (params) => params.data.display_name
              }
            },
            data: [...active_job_concentration_by_company]
          }
        ]
      },
      media: [
        {
          query: {
            maxWidth: 700
          },
          option: {
            legend: {
              orient: 'horizontal',
              left: 'center',
              right: 'auto',
              top: 'auto',
              bottom: 0
            },
            series: [
              {
                radius: ['34%', '56%'],
                center: ['50%', '40%']
              }
            ]
          }
        }
      ]
    }
  } height="420px" />
  {:else}
    <div class="chart-no-data" role="status">No active jobs match the selected filters.</div>
  {/if}
</div>

```sql new_and_removed_jobs_trend
with normalized_bounds as (
    select
        cast(
            date_trunc('week', cast('${inputs.posted_window.start}' as date) + interval '1 day') - interval '1 day'
            as date
        ) as start_week,
        cast(
            date_trunc('week', cast('${inputs.posted_window.end}' as date) + interval '1 day') - interval '1 day'
            as date
        ) as end_week
), filtered_flow as (
    select
        week_beginning as week,
        type as job_flow_type,
        sum(jobs_count) as job_count
    from project_portfolio.jobs_flow_week
    cross join normalized_bounds
    where week_beginning between start_week and end_week
      and type in ('New Jobs', 'Removed Jobs')
      and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
      and ('${inputs.job_platform.value}' = 'All' or job_platform = '${inputs.job_platform.value}')
      and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
    group by 1, 2
), weeks as (
    select cast(generated_week as date) as week
    from normalized_bounds
    cross join unnest(
        generate_series(start_week, end_week, interval '1 week')
    ) as generated_weeks(generated_week)
    where exists (select 1 from filtered_flow)
), flow_types as (
    select *
    from (values ('New Jobs', 1), ('Removed Jobs', 2)) as t(job_flow_type, series_order)
)
select
    weeks.week,
    flow_types.job_flow_type,
    coalesce(filtered_flow.job_count, 0) as job_count,
    flow_types.series_order
from weeks
cross join flow_types
left join filtered_flow
    on weeks.week = filtered_flow.week
    and flow_types.job_flow_type = filtered_flow.job_flow_type
order by weeks.week asc, flow_types.series_order asc
```

```sql avg_days_listed_over_time
with eligible_jobs as (
    select
        job_id,
        last_seen_at_utc,
        days_listed,
        row_number() over (
            partition by job_id
            order by last_seen_at_utc desc, days_listed desc, job_id
        ) as dedupe_rank
    from project_portfolio.jobs_detail_report
    where job_id is not null
      and last_seen_at_utc is not null
      and days_listed is not null
      and cast(last_seen_at_utc as date) between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
      and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
      and ('${inputs.job_platform.value}' = 'All' or job_platform = '${inputs.job_platform.value}')
      and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
      and ('All' in ${inputs.job_location_state.value} or state_name in ${inputs.job_location_state.value})
      and ('${inputs.job_level.value}' = 'All' or job_level = '${inputs.job_level.value}')
      and ('${inputs.degree_requirement.value}' = 'All' or degree_requirement = '${inputs.degree_requirement.value}')
      and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
      and (
          trim(${inputs.job_title_filter.sql}) = ''
          or (
              '${inputs.job_title_match_method.value}' = 'is'
              and lower(coalesce(job_title, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.job_title_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.job_title_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          trim(${inputs.company_name_filter.sql}) = ''
          or (
              '${inputs.company_name_match_method.value}' = 'is'
              and lower(coalesce(company_name, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.company_name_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.company_name_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
), deduplicated_jobs as (
    select
        job_id,
        last_seen_at_utc,
        days_listed
    from eligible_jobs
    where dedupe_rank = 1
)
select
    cast(
        date_trunc('week', cast(last_seen_at_utc as date) + interval '1 day') - interval '1 day'
        as date
    ) as week,
    avg(days_listed) as avg_days_listed
from deduplicated_jobs
group by 1
order by week asc
```

<div class="chart-split-grid">

<div class="chart-card">
  <div class="section-title">New and Removed Jobs Trend</div>
  <LineChart
    data={new_and_removed_jobs_trend}
    x=week
    y=job_count
    series=job_flow_type
    seriesOrder={['New Jobs', 'Removed Jobs']}
    sort=false
    xAxisTitle=""
    yAxisTitle="Job Count"
    yFmt=num0
    markers=true
    chartAreaHeight=280
    emptySet=pass
    emptyMessage="No new or removed jobs match the selected flow filters."
  />
</div>

<div class="chart-card">
  <div class="section-title">Avg Days Listed Over Time</div>
  <AreaChart
    data={avg_days_listed_over_time}
    x=week
    y=avg_days_listed
    sort=false
    xAxisTitle=""
    yAxisTitle="Avg Days Listed"
    yFmt=num1
    chartAreaHeight=280
    emptySet=pass
    emptyMessage="No jobs match the selected filters."
  />
</div>

</div>

```sql avg_annual_pay_range_over_time
with eligible_jobs as (
    select
        job_id,
        posted_date,
        avg_annual_pay_range,
        row_number() over (
            partition by job_id
            order by posted_date asc, avg_annual_pay_range desc, job_id
        ) as dedupe_rank
    from project_portfolio.jobs_detail_report
    where job_id is not null
      and posted_date is not null
      and avg_annual_pay_range is not null
      and posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
      and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
      and ('${inputs.job_platform.value}' = 'All' or job_platform = '${inputs.job_platform.value}')
      and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
      and ('All' in ${inputs.job_location_state.value} or state_name in ${inputs.job_location_state.value})
      and ('${inputs.job_level.value}' = 'All' or job_level = '${inputs.job_level.value}')
      and ('${inputs.degree_requirement.value}' = 'All' or degree_requirement = '${inputs.degree_requirement.value}')
      and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
      and (
          trim(${inputs.job_title_filter.sql}) = ''
          or (
              '${inputs.job_title_match_method.value}' = 'is'
              and lower(coalesce(job_title, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.job_title_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.job_title_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          trim(${inputs.company_name_filter.sql}) = ''
          or (
              '${inputs.company_name_match_method.value}' = 'is'
              and lower(coalesce(company_name, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.company_name_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.company_name_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
), deduplicated_jobs as (
    select
        job_id,
        posted_date,
        avg_annual_pay_range
    from eligible_jobs
    where dedupe_rank = 1
)
select
    cast(
        date_trunc('week', posted_date + interval '1 day') - interval '1 day'
        as date
    ) as week,
    avg(avg_annual_pay_range) as avg_annual_pay_range
from deduplicated_jobs
group by 1
order by week asc
```

<div class="chart-card">
  <div class="section-title">Avg Annual Pay Range over Time</div>
  <AreaChart
    data={avg_annual_pay_range_over_time}
    x=week
    y=avg_annual_pay_range
    sort=false
    xAxisTitle=""
    yAxisTitle="Avg Annual Pay Range"
    yFmt=usd0
    chartAreaHeight=280
    emptySet=pass
    emptyMessage="No jobs with annual pay data match the selected filters."
  />
</div>

```sql jobs_posted_trends_by_week
with normalized_bounds as (
    select
        cast(
            date_trunc('week', cast('${inputs.posted_window.start}' as date) + interval '1 day') - interval '1 day'
            as date
        ) as start_week,
        cast(
            date_trunc('week', cast('${inputs.posted_window.end}' as date) + interval '1 day') - interval '1 day'
            as date
        ) as end_week
), aggregated_counts as (
    select
        week_beginning,
        search_term,
        sum(jobs_count) as jobs_count
    from project_portfolio.jobs_flow_week_trends
    cross join normalized_bounds
    where week_beginning between start_week - interval '1 week' and end_week
      and type = 'New Jobs'
      and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
      and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
    group by 1, 2
), selected_search_terms as (
    select distinct search_term
    from aggregated_counts
), weekly_spine as (
    select cast(generated_week as date) as week_beginning
    from normalized_bounds
    cross join unnest(
        generate_series(start_week - interval '1 week', end_week, interval '1 week')
    ) as generated_weeks(generated_week)
    where exists (select 1 from aggregated_counts)
), complete_counts as (
    select
        weekly_spine.week_beginning,
        selected_search_terms.search_term,
        coalesce(aggregated_counts.jobs_count, 0) as jobs_count
    from weekly_spine
    cross join selected_search_terms
    left join aggregated_counts
        on weekly_spine.week_beginning = aggregated_counts.week_beginning
        and selected_search_terms.search_term is not distinct from aggregated_counts.search_term
), counts_with_previous_week as (
    select
        week_beginning,
        search_term,
        jobs_count,
        lag(jobs_count) over (
            partition by search_term
            order by week_beginning asc
        ) as previous_week_jobs_count
    from complete_counts
), changes as (
    select
        week_beginning,
        search_term,
        1.0 * (jobs_count - previous_week_jobs_count)
            / nullif(previous_week_jobs_count, 0) as wow_percent_change
    from counts_with_previous_week
)
select
    week_beginning,
    search_term,
    wow_percent_change
from changes
cross join normalized_bounds
where week_beginning between start_week and end_week
  and wow_percent_change is not null
order by week_beginning asc, search_term asc
```

<div class="chart-card">
  <div class="section-title">Jobs Posted Trends by Week</div>
  <LineChart
    data={jobs_posted_trends_by_week}
    x=week_beginning
    y=wow_percent_change
    series=search_term
    sort=false
    xAxisTitle=""
    yAxisTitle="% Change"
    yFmt=pct1
    markers=true
    chartAreaHeight=320
    emptySet=pass
    emptyMessage="No week-over-week job posting changes match the selected filters."
  />
</div>

</div>
