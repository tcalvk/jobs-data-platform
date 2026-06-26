---
title: Career Opportunity Explorer
full_width: true
sidebar: hide
hide_toc: true
hide_breadcrumbs: true
---

<script>
  import JobTitleTokenInput from '../../components/JobTitleTokenInput.svelte';

  let showActiveJobsDetail = false;
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

  .kpi-drilldown {
    display: block;
    width: 100%;
    border: 0;
    padding: 0;
    background: transparent;
    cursor: pointer;
  }

  .kpi-drilldown:hover .kpi-value-box,
  .kpi-drilldown:focus-visible .kpi-value-box {
    box-shadow: 0 0 0 2px #2563eb, 0 1px 4px rgba(15, 23, 42, 0.12);
  }

  .kpi-drilldown:focus-visible {
    outline: none;
  }

  .kpi-card .kpi-title {
    font-size: 1.12rem;
    font-weight: 700;
    color: #263238;
    margin-bottom: 0.2rem;
  }

  .kpi-value-box {
    min-height: 2.15rem;
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
    font-size: 1.9rem !important;
    line-height: 1 !important;
    margin-top: 0 !important;
    font-weight: 500 !important;
    color: #263238;
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

  .section-description {
    color: #475569;
    font-size: 0.82rem;
    margin: -0.2rem 0 0.35rem 0;
  }

  .drilldown-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.6rem;
  }

  .drilldown-close {
    border: 1px solid #cbd5e1;
    border-radius: 0.35rem;
    background: #ffffff;
    color: #263238;
    font-size: 0.8rem;
    padding: 0.25rem 0.55rem;
    cursor: pointer;
  }

  #active-jobs-detail {
    --drilldown-card-bg: #ffffff;
    --drilldown-table-bg: #ffffff;
    --drilldown-table-alt-bg: #f8fafc;
    --drilldown-table-hover-bg: #eff6ff;
    --drilldown-header-bg: #e2e8f0;
    --drilldown-border: #cbd5e1;
    --drilldown-text: #1f2937;
    --drilldown-muted-text: #475569;
    --drilldown-heading-text: #111827;
    --drilldown-control-bg: #ffffff;
    --drilldown-control-border: #cbd5e1;
    --drilldown-link: #1d4ed8;
    background: var(--drilldown-card-bg);
    border: 1px solid var(--drilldown-border);
    color: var(--drilldown-text);
  }

  :global([data-theme='dark']) #active-jobs-detail {
    --drilldown-card-bg: #f8fafc;
    --drilldown-table-bg: #ffffff;
    --drilldown-table-alt-bg: #f1f5f9;
    --drilldown-table-hover-bg: #dbeafe;
    --drilldown-header-bg: #dbeafe;
    --drilldown-border: #94a3b8;
    --drilldown-text: #0f172a;
    --drilldown-muted-text: #334155;
    --drilldown-heading-text: #020617;
    --drilldown-control-bg: #ffffff;
    --drilldown-control-border: #94a3b8;
    --drilldown-link: #1d4ed8;
    box-shadow: 0 1px 10px rgba(255, 255, 255, 0.08);
  }

  #active-jobs-detail .section-title {
    color: var(--drilldown-heading-text);
  }

  #active-jobs-detail :global(.scrollbox) {
    background: var(--drilldown-table-bg) !important;
    border: 1px solid var(--drilldown-border);
    border-radius: 0.45rem;
  }

  #active-jobs-detail :global(table) {
    background-color: var(--drilldown-table-bg) !important;
    color: var(--drilldown-text) !important;
  }

  #active-jobs-detail :global(thead),
  #active-jobs-detail :global(th),
  #active-jobs-detail :global(th span),
  #active-jobs-detail :global(th button) {
    background-color: var(--drilldown-header-bg) !important;
    color: var(--drilldown-heading-text) !important;
    font-weight: 700;
  }

  #active-jobs-detail :global(th),
  #active-jobs-detail :global(td) {
    border-color: var(--drilldown-border) !important;
  }

  #active-jobs-detail :global(td),
  #active-jobs-detail :global(td span),
  #active-jobs-detail :global(td div) {
    color: var(--drilldown-text) !important;
  }

  #active-jobs-detail :global(tbody tr) {
    background-color: var(--drilldown-table-bg) !important;
  }

  #active-jobs-detail :global(tbody tr:nth-child(even)),
  #active-jobs-detail :global(.bg-base-200) {
    background-color: var(--drilldown-table-alt-bg) !important;
  }

  #active-jobs-detail :global(tbody tr:hover),
  #active-jobs-detail :global(tbody tr:hover td) {
    background-color: var(--drilldown-table-hover-bg) !important;
  }

  #active-jobs-detail :global(input) {
    background: var(--drilldown-control-bg) !important;
    border-color: var(--drilldown-control-border) !important;
    color: var(--drilldown-text) !important;
  }

  #active-jobs-detail :global(.search-container),
  #active-jobs-detail :global(.search-bar) {
    background-color: var(--drilldown-control-bg) !important;
    border-color: var(--drilldown-control-border) !important;
    color: var(--drilldown-text) !important;
  }

  #active-jobs-detail :global(.search-container) {
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08) !important;
  }

  #active-jobs-detail :global(.search-icon) {
    background: transparent !important;
    color: var(--drilldown-muted-text) !important;
  }

  #active-jobs-detail :global(input::placeholder) {
    color: var(--drilldown-muted-text) !important;
  }

  #active-jobs-detail :global(svg),
  #active-jobs-detail :global(label),
  #active-jobs-detail :global(p) {
    color: var(--drilldown-muted-text) !important;
  }

  #active-jobs-detail :global(button),
  #active-jobs-detail .drilldown-close {
    background: var(--drilldown-control-bg);
    border-color: var(--drilldown-control-border);
    color: var(--drilldown-text);
  }

  #active-jobs-detail :global(a:not(.apply-link-button)) {
    color: var(--drilldown-link) !important;
  }

  #active-jobs-detail :global(th:first-child),
  #active-jobs-detail :global(td:first-child) {
    width: 18rem;
    min-width: 18rem;
    max-width: 18rem;
    white-space: normal;
    overflow-wrap: anywhere;
  }

  #active-jobs-detail :global(.apply-link-button) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.35rem;
    background: #2563eb;
    color: #ffffff !important;
    font-size: 0.78rem;
    font-weight: 700;
    line-height: 1;
    padding: 0.35rem 0.65rem;
    text-decoration: none !important;
    white-space: nowrap;
  }

  #active-jobs-detail :global(.apply-link-button:hover),
  #active-jobs-detail :global(.apply-link-button:focus-visible) {
    background: #1d4ed8;
    outline: none;
  }

  :global([data-theme='dark']) .reset-filters-button,
  :global([data-theme='dark']) .more-filters-toggle {
    background: #18181b;
    border-color: #3f3f46;
    color: #ffffff;
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

  @media (max-width: 900px) {
    .filter-grid,
    .kpi-grid,
    .chart-split-grid {
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
</div>

```sql kpis
select
    count(distinct case when listing_status = 'Active' then job_id end) as active_jobs,
    count(distinct case when posted_date >= cast('${inputs.posted_window.end}' as date) - interval '7 day' then job_id end) as new_jobs_last_7_days,
    count(distinct case when listing_status = 'Active' then company_name end) as companies_hiring,
    avg(case when listing_status = 'Active' then days_listed end) as avg_days_listed_active,
    avg(case when listing_status = 'Active' then avg_annual_pay_range end) as avg_salary_active,
    count(distinct case when listing_status = 'Active' then job_platform end) as job_platforms_active
from project_portfolio.jobs_detail_report
where posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
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
  --and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
```

<div class="kpi-grid">
  <button class="kpi-card kpi-drilldown" type="button" on:click={() => showActiveJobsDetail = true} aria-label="Show active jobs detail table">
    <div class="kpi-title">Active Jobs</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=active_jobs fmt=num0 /></div>
  </button>
  <div class="kpi-card">
    <div class="kpi-title">New Jobs (Last 7 Days)</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=new_jobs_last_7_days fmt=num0 /></div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Companies Hiring</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=companies_hiring fmt=num0 /></div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Avg Days Listed (Active)</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=avg_days_listed_active fmt=num2 /></div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Avg Salary (Active)</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=avg_salary_active fmt=usd2 /></div>
  </div>
  <div class="kpi-card">
    <div class="kpi-title">Job Platforms (Active)</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=job_platforms_active fmt=num0 /></div>
  </div>
</div>

```sql active_jobs_detail
select
    job_title,
    case
        when source_link is not null then '<a class="apply-link-button markdown" href="' || replace(source_link, '"', '%22') || '" target="_blank" rel="noopener noreferrer">Apply</a>'
        else null
    end as apply_link,
    company_name,
    search_term,
    job_location,
    search_location,
    job_platform,
    schedule_type,
    job_level,
    degree_requirement,
    avg_annual_pay_range,
    posted_date,
    days_listed,
    opportunity_score,
    opportunity_tier,
    data_source,
    job_id
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
order by posted_date desc nulls last, opportunity_score desc nulls last
limit 1000
```

{#if showActiveJobsDetail}
<div class="chart-card" id="active-jobs-detail">
  <div class="drilldown-header">
    <div class="section-title">Active Jobs Detail</div>
    <button class="drilldown-close" type="button" on:click={() => showActiveJobsDetail = false}>Close</button>
  </div>
  <DataTable data={active_jobs_detail} rows=25 search sort="posted_date desc">
    <Column id=job_title title="Job Title" wrap=true />
    <Column id=apply_link title="Apply Link" contentType=html align=center />
    <Column id=company_name title="Company Name" />
    <Column id=search_term title="Search Term" />
    <Column id=job_location title="Job Location" />
    <Column id=search_location title="Search Location" />
    <Column id=job_platform title="Job Platform" />
    <Column id=schedule_type title="Schedule Type" />
    <Column id=job_level title="Job Level" />
    <Column id=degree_requirement title="Degree Requirement" />
    <Column id=avg_annual_pay_range title="Avg Annual Pay Range" fmt=usd0 />
    <Column id=posted_date title="Posted Date" />
    <Column id=days_listed title="Days Listed" fmt=num0 />
    <Column id=opportunity_score title="Opportunity Score" fmt=num1 />
    <Column id=opportunity_tier title="Opportunity Tier" />
    <Column id=data_source title="Data Source" />
    <Column id=job_id title="Job ID" />
  </DataTable>
</div>
{/if}

```sql top_terms
select
    search_term,
    round(avg(opportunity_score), 1) as opportunity_score
from project_portfolio.jobs_detail_report
where posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
  and opportunity_score is not null
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
  and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
group by 1
order by opportunity_score desc nulls last
limit 10
```

<div class="chart-card">
  <div class="section-title">Top 10 Search Terms by Opportunity Score</div>
  <BarChart
    data={top_terms}
    x=search_term
    y=opportunity_score
    swapXY=true
    labels=true
    yAxisTitle="Opportunity Score"
    xAxisTitle=""
    color="#4285f4"
    chartAreaHeight=280
  />
</div>

```sql demand_vs_pay
select
    search_term,
    sum(case when listing_status = 'Active' then 1 else 0 end) as active_jobs,
    avg(avg_annual_pay_range) as avg_annual_pay_range,
    round(coalesce(avg(opportunity_score), 1), 1) as opportunity_score
from project_portfolio.jobs_detail_report
where posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
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
  and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
group by 1
having active_jobs > 0
order by opportunity_score desc
limit 25
```

<div class="chart-card">
  <div class="section-title">Job Demand vs Pay (Size = Opportunity Score)</div>
  <BubbleChart
    data={demand_vs_pay}
    x=avg_annual_pay_range
    y=active_jobs
    size=opportunity_score
    series=search_term
    tooltipTitle=search_term
    legend={false}
    xAxisTitle="Avg Annual Pay Range"
    yAxisTitle="Active Jobs"
    xFmt=usd0
    yFmt=num0
    sizeFmt=num1
    chartAreaHeight=280
    seriesOptions={{
      label: {
        show: true,
        formatter: (params) => params.value[3],
        position: 'right',
        color: () => globalThis?.matchMedia?.('(prefers-color-scheme: dark)').matches ? '#ffffff' : '#263238',
        fontSize: 11
      },
      labelLayout: {
        hideOverlap: true
      }
    }}
  />
</div>

```sql days_listed_distribution
with binned as (
    select
        cast(floor(coalesce(days_listed, 0) / 2) * 2 as int) as bin_start,
        job_id
    from project_portfolio.jobs_detail_report
    where days_listed is not null
      and days_listed >= 0
      and days_listed < 32
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
      and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
)
select
    '[' || bin_start || ', ' || (bin_start + 2) || ')' as days_bucket,
    count(distinct job_id) as record_count,
    'Record Count' as record_series,
    bin_start
from binned
group by 1, 3, 4
order by bin_start
```

```sql degree_requirement_distribution
with grouped as (
    select
        coalesce(degree_requirement, 'Degree Not Specified') as degree_requirement,
        count(distinct job_id) as record_count
    from project_portfolio.jobs_detail_report
    where posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
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
      and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
    group by 1
)
select
    degree_requirement as name,
    record_count as value,
    case degree_requirement
        when 'High School' then 1
        when 'Associate''s' then 2
        when 'Bachelor''s' then 3
        when 'Master''s' then 4
        when 'Doctorate' then 5
        when 'Degree Not Specified' then 6
        else 7
    end as degree_order
from grouped
order by degree_order
```

<div class="chart-split-grid">

<div class="chart-card">
  <div class="section-title">Distribution of Days Listed</div>
  <BarChart
    data={days_listed_distribution}
    x=days_bucket
    y=record_count
    series=record_series
    sort=false
    color="#4285f4"
    yAxisTitle="Record Count"
    xAxisTitle=""
    yFmt=num0
    chartAreaHeight=260
  />
</div>

<div class="chart-card">
  <div class="section-title">Degree Requirement Distribution</div>
  <div class="section-description">Shows the percentage distribution of degree requirement based on the selected filters</div>
  <ECharts config={
    {
      tooltip: {
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle'
      },
      series: [
        {
          type: 'pie',
          radius: ['42%', '70%'],
          center: ['62%', '50%'],
          avoidLabelOverlap: true,
          label: {
            formatter: '{b}: {d}%'
          },
          data: [...degree_requirement_distribution]
        }
      ]
    }
  } height="260px" />
</div>

</div>

```sql jobs_by_location
select
    state_name as point_name,
    lat,
    long,
    count(distinct job_id) as jobs_posted
from project_portfolio.jobs_detail_report
where lat is not null
  and long is not null
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
  and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
group by 1, 2, 3
order by jobs_posted desc
```

<div class="chart-card">
  <div class="section-title">Jobs Posted by Location</div>
  <PointMap
    data={jobs_by_location}
    lat=lat
    long=long
    value=jobs_posted
    pointName=point_name
    valueFmt=num0
    legendType=scalar
    startingLat=38
    startingLong=-97
    startingZoom=3
    height=390
    colorPalette={["#a7f3d0", "#22c55e", "#f59e0b", "#ef4444"]}
    tooltip={[{ id: 'point_name', showColumnName: false }, { id: 'jobs_posted', fmt: 'num0' }]}
  />
</div>

</div>
