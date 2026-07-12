---
title: Skills Intelligence
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
  .coe-page {
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

  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.95rem 1.55rem;
    margin: 0.35rem 0 1.2rem 0;
  }

  .kpi-card {
    text-align: center;
  }

  .kpi-card .kpi-title {
    font-size: 1.12rem;
    font-weight: 700;
    color: #263238;
    margin-bottom: 0.2rem;
  }

  .kpi-value-box {
    min-height: 3rem;
    background: white;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  }

  .kpi-value-box :global(.inline-block) {
    padding: 0 !important;
    margin: 0 !important;
    min-width: auto !important;
  }

  .kpi-value-box :global(p) {
    display: none;
  }

  .kpi-value-box :global(.text-xl) {
    font-size: 1.55rem !important;
    line-height: 1.1 !important;
    margin-top: 0 !important;
    font-weight: 500 !important;
    color: #263238;
    overflow-wrap: anywhere;
  }

  .chart-card {
    background: white;
    margin-top: 1.2rem;
    padding: 0.7rem 0.75rem 0.45rem 0.75rem;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
  }

  .section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #263238;
    margin: 0 0 0.35rem 0;
  }

  :global(.over-container) {
    display: none !important;
  }

  :global([data-theme='dark']) .reset-filters-button,
  :global([data-theme='dark']) .more-filters-toggle {
    background: #18181b;
    border-color: #3f3f46;
    color: #ffffff;
  }

  @media (max-width: 900px) {
    .filter-grid,
    .kpi-grid {
      grid-template-columns: 1fr;
    }

    .coe-page {
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

```sql skill_options
with options as (
    select
        skill,
        skill as skill_label,
        row_number() over (order by skill) as option_rank
    from (
        select distinct skill
        from project_portfolio.rpt_job_skills
        where skill is not null
    )
)
select 'All' as skill, '𝐀𝐥𝐥 Values' as skill_label, 0 as ordinal
union all
select skill, skill_label, option_rank as ordinal
from options
order by ordinal
```

<div class="coe-page">

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
  <Dropdown data={skill_options} name=skill value=skill label=skill_label order=ordinal title="Skill" multiple=true defaultValue={['All']} />
</div>

```sql kpis
with job_states as (
    select distinct
        job_id,
        state_name
    from project_portfolio.jobs_detail_report
), filtered_skills as (
    select s.*
    from project_portfolio.rpt_job_skills as s
    left join job_states as js
        on s.job_id = js.job_id
    where skill is not null
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
      and ('All' in ${inputs.job_location_state.value} or js.state_name in ${inputs.job_location_state.value})
      and ('${inputs.job_platform.value}' = 'All' or job_platform = '${inputs.job_platform.value}')
      and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
      and ('All' in ${inputs.skill.value} or skill in ${inputs.skill.value})
), skill_job_counts as (
    select
        skill,
        count(distinct job_id) as distinct_job_count
    from filtered_skills
    group by 1
), top_skill as (
    select skill
    from skill_job_counts
    order by distinct_job_count desc, skill
    limit 1
), highest_salary_skill as (
    select
        skill,
        avg(avg_annual_pay_range) as avg_annual_pay_range,
        count(distinct job_id) as distinct_job_count
    from filtered_skills
    where avg_annual_pay_range is not null
    group by 1
    having count(distinct job_id) >= 100
    order by avg_annual_pay_range desc nulls last, skill
    limit 1
)
select
    coalesce((select skill from top_skill), 'No skills') as top_skill,
    coalesce((select skill from highest_salary_skill), 'No salary data') as highest_salary_skill,
    count(distinct skill) as skills_tracked
from filtered_skills
```

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-title">Top Skill</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=top_skill /></div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Highest Salary Skill</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=highest_salary_skill /></div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Skills Tracked</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=skills_tracked fmt=num0 /></div>
  </div>
</div>


```sql skill_demand_salary_impact
with job_states as (
    select distinct
        job_id,
        state_name
    from project_portfolio.jobs_detail_report
), filtered_skills as (
    select s.*
    from project_portfolio.rpt_job_skills as s
    left join job_states as js
        on s.job_id = js.job_id
    where skill is not null
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
      and ('All' in ${inputs.job_location_state.value} or js.state_name in ${inputs.job_location_state.value})
      and ('${inputs.job_platform.value}' = 'All' or job_platform = '${inputs.job_platform.value}')
      and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
      and ('All' in ${inputs.skill.value} or skill in ${inputs.skill.value})
)
select
    skill,
    count(distinct job_id) as distinct_job_count,
    avg(avg_annual_pay_range) as avg_annual_pay_range,
    count(distinct case when avg_annual_pay_range is not null then job_id end) as salary_job_count,
    round(100.0 * count(distinct case when avg_annual_pay_range is not null then job_id end) / nullif(count(distinct job_id), 0), 1) as salary_coverage_pct
from filtered_skills
group by 1
having distinct_job_count > 0
order by distinct_job_count desc, avg_annual_pay_range desc nulls last
limit 50
```

<div class="chart-card">
  <div class="section-title">Skill Demand vs Salary Impact</div>
  <BubbleChart
    data={skill_demand_salary_impact}
    x=distinct_job_count
    y=avg_annual_pay_range
    size=distinct_job_count
    series=skill
    tooltipTitle=skill
    legend={false}
    xAxisTitle="Jobs Requiring Skill"
    yAxisTitle="Avg Salary for Jobs Requiring Skill"
    xFmt=num0
    yFmt=usd0
    sizeFmt=num0
    chartAreaHeight=360
  />
</div>

```sql skill_trend_over_time
with job_states as (
    select distinct
        job_id,
        state_name
    from project_portfolio.jobs_detail_report
), filtered_skills as (
    select s.*
    from project_portfolio.rpt_job_skills as s
    left join job_states as js
        on s.job_id = js.job_id
    where skill is not null
      and month_start_date is not null
      and posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
      and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
      and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
      and ('All' in ${inputs.job_location_state.value} or js.state_name in ${inputs.job_location_state.value})
      and ('All' in ${inputs.skill.value} or skill in ${inputs.skill.value})
), monthly_skill_counts as (
    select
        month_start_date,
        skill,
        count(distinct job_id) as distinct_job_count
    from filtered_skills
    group by 1, 2
), ranked_skills as (
    select
        skill,
        sum(distinct_job_count) as total_job_count,
        dense_rank() over (order by sum(distinct_job_count) desc, skill) as skill_rank
    from monthly_skill_counts
    group by 1
)
select
    m.month_start_date,
    m.skill,
    m.distinct_job_count
from monthly_skill_counts as m
inner join ranked_skills as r
    on m.skill = r.skill
where r.skill_rank <= 10
order by m.month_start_date, m.skill
```

<div class="chart-card">
  <div class="section-title">Skill Trend Over Time</div>
  <LineChart
    data={skill_trend_over_time}
    x=month_start_date
    y=distinct_job_count
    series=skill
    xAxisTitle="Month"
    yAxisTitle="Jobs Requiring Skill"
    yFmt=num0
    chartAreaHeight=300
  />
</div>

</div>
