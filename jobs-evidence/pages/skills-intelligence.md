---
title: Skills Intelligence
full_width: true
sidebar: hide
hide_toc: true
hide_breadcrumbs: true
---

<script>
  import JobTitleTokenInput from '../../components/JobTitleTokenInput.svelte';
  import { getInputContext } from '@evidence-dev/sdk/utils/svelte';

  let showMoreFilters = false;
  let filtersReady = false;
  let dashboardLoaded = false;
  const inputContext = getInputContext();
  const activeInputNames = [
    'search_term',
    'job_platform',
    'listing_status',
    'posted_window',
    'job_location_state',
    'job_level',
    'degree_requirement',
    'search_location',
    'job_title_match_method',
    'job_title_filter',
    'company_name_match_method',
    'company_name_filter'
  ];

  const snapshotInput = (input) => {
    if (input === undefined) return undefined;

    const descriptors = Object.getOwnPropertyDescriptors(input);
    for (const key of ['value', 'label', 'sql', 'start', 'end', 'rawValues']) {
      delete descriptors[key];
    }
    const snapshot = Object.create(Object.getPrototypeOf(input), descriptors);

    for (const key of ['value', 'label', 'sql', 'start', 'end']) {
      if (input[key] !== undefined) {
        Object.defineProperty(snapshot, key, {
          configurable: true,
          enumerable: true,
          value: input[key],
          writable: true
        });
      }
    }

    if (input.rawValues !== undefined) {
      Object.defineProperty(snapshot, 'rawValues', {
        configurable: true,
        enumerable: true,
        value: Array.isArray(input.rawValues)
          ? [...input.rawValues]
          : input.rawValues && typeof input.rawValues === 'object'
            ? { ...input.rawValues }
            : input.rawValues,
        writable: true
      });
    }

    return snapshot;
  };

  const snapshotActiveInputs = (current, revision) => {
    const next = { ...current };

    for (const name of activeInputNames) {
      const snapshot = snapshotInput(current[name]);
      if (snapshot !== undefined) {
        next[`applied_${name}`] = snapshot;
      }
    }

    next.dashboard_load = {
      value: revision,
      label: String(revision),
      sql: String(revision)
    };

    return next;
  };

  const inputIsReady = (name, input) => {
    if (!input) return false;
    if (name === 'posted_window') {
      return input.start != null && input.end != null;
    }
    if (name.endsWith('_filter')) {
      return input.value != null && input.sql != null;
    }
    return input.value != null;
  };

  const allInputsAreReady = (current) =>
    activeInputNames.every((name) => inputIsReady(name, current[name]));

  const applyFilters = () => {
    if (!filtersReady) return;

    let updateCompleted = false;

    inputContext.update((current) => {
      if (!allInputsAreReady(current)) {
        filtersReady = false;
        return current;
      }

      const currentRevision = Number(current.dashboard_load?.value) || 0;
      const next = snapshotActiveInputs(current, currentRevision + 1);
      updateCompleted = true;
      return next;
    });

    if (updateCompleted) dashboardLoaded = true;
  };

  // Live edits only update readiness. Queries continue to use applied_* snapshots until
  // an explicit Load/Update, whose revision also intentionally refreshes unchanged filters.

  onMount(() => {
    const unsubscribe = inputContext.subscribe((current) => {
      filtersReady = allInputsAreReady(current);
    });

    return unsubscribe;
  });
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

  .apply-filters-button,
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

  .apply-filters-button:hover,
  .apply-filters-button:focus-visible,
  .reset-filters-button:hover,
  .reset-filters-button:focus-visible,
  .more-filters-toggle:hover,
  .more-filters-toggle:focus-visible {
    border-color: #2563eb;
    outline: none;
  }

  .apply-filters-button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
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

  .dashboard-unloaded {
    min-height: 32rem;
    margin-top: 0.35rem;
    border: 1px solid #cbd5e1;
    border-radius: 0.65rem;
    background: rgba(255, 255, 255, 0.72);
    color: #263238;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    padding: 2rem;
    text-align: center;
    box-sizing: border-box;
  }

  .dashboard-unloaded-symbol {
    width: 2.75rem;
    height: 2.75rem;
    border: 2px solid #94a3b8;
    border-radius: 999px;
    color: #2563eb;
    display: grid;
    place-items: center;
    font-size: 1.55rem;
    line-height: 1;
  }

  .dashboard-unloaded-title {
    margin: 0.35rem 0 0;
    font-size: 1.1rem;
    font-weight: 700;
  }

  .dashboard-unloaded-copy {
    margin: 0;
    color: #64748b;
    font-size: 0.9rem;
  }

  .main-chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1.2rem;
    align-items: start;
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

  :global([data-theme='dark']) .apply-filters-button,
  :global([data-theme='dark']) .reset-filters-button,
  :global([data-theme='dark']) .more-filters-toggle {
    background: #18181b;
    border-color: #3f3f46;
    color: #ffffff;
  }

  :global([data-theme='dark']) .dashboard-unloaded {
    background: rgba(24, 24, 27, 0.78);
    border-color: #3f3f46;
    color: #f8fafc;
  }

  :global([data-theme='dark']) .dashboard-unloaded-copy {
    color: #a1a1aa;
  }

  @media (max-width: 900px) {
    .filter-grid,
    .kpi-grid,
    .main-chart-grid {
      grid-template-columns: 1fr;
    }

    .coe-page {
      margin-left: 0;
      margin-right: 0;
    }

    .dashboard-unloaded {
      min-height: 24rem;
      padding: 1.5rem;
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
  <button class="apply-filters-button" type="button" on:click={applyFilters} disabled={!filtersReady}>
    {dashboardLoaded ? 'Update' : 'Load'}
  </button>
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

{#if !dashboardLoaded}
  <div class="dashboard-unloaded" role="status" aria-live="polite">
    <div class="dashboard-unloaded-symbol" aria-hidden="true">↻</div>
    <p class="dashboard-unloaded-title">Dashboard ready to load</p>
    <p class="dashboard-unloaded-copy">Choose your filters, then click Load.</p>
  </div>
{/if}

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
    where ${inputs.dashboard_load?.value} >= 1
      and posted_date between cast('${inputs.applied_posted_window?.start ?? inputs.posted_window.start}' as date) and cast('${inputs.applied_posted_window?.end ?? inputs.posted_window.end}' as date)
      and s.skill is not null
      and trim(s.skill) <> ''
      and ('${inputs.applied_search_term?.value ?? inputs.search_term.value}' = 'All' or search_term = '${inputs.applied_search_term?.value ?? inputs.search_term.value}')
      and ('${inputs.applied_job_level?.value ?? inputs.job_level.value}' = 'All' or job_level = '${inputs.applied_job_level?.value ?? inputs.job_level.value}')
      and ('${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}' = 'All' or degree_requirement = '${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}')
      and (
          trim(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}) = ''
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'is'
              and lower(coalesce(job_title, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          trim(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}) = ''
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'is'
              and lower(coalesce(company_name, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          '${inputs.applied_search_location?.value ?? inputs.search_location.value}' = 'All'
          or search_location like '%' || '${inputs.applied_search_location?.value ?? inputs.search_location.value}' || '%'
      )
      and ('All' in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value} or js.state_name in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value})
      and ('${inputs.applied_job_platform?.value ?? inputs.job_platform.value}' = 'All' or job_platform = '${inputs.applied_job_platform?.value ?? inputs.job_platform.value}')
      and ('${inputs.applied_listing_status?.value ?? inputs.listing_status.value}' = 'All' or listing_status = '${inputs.applied_listing_status?.value ?? inputs.listing_status.value}')
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

{#if dashboardLoaded}
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
{/if}

```sql top_requested_skills
with job_states as (
    select distinct
        job_id,
        state_name
    from project_portfolio.jobs_detail_report
), filtered_skills as (
    select s.*
    from project_portfolio.rpt_job_skills as s
    where ${inputs.dashboard_load?.value} >= 1
      and posted_date between cast('${inputs.applied_posted_window?.start ?? inputs.posted_window.start}' as date) and cast('${inputs.applied_posted_window?.end ?? inputs.posted_window.end}' as date)
      and s.skill is not null
      and trim(s.skill) <> ''
      and ('${inputs.applied_search_term?.value ?? inputs.search_term.value}' = 'All' or search_term = '${inputs.applied_search_term?.value ?? inputs.search_term.value}')
      and ('${inputs.applied_job_level?.value ?? inputs.job_level.value}' = 'All' or job_level = '${inputs.applied_job_level?.value ?? inputs.job_level.value}')
      and ('${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}' = 'All' or degree_requirement = '${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}')
      and (
          trim(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}) = ''
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'is'
              and lower(coalesce(job_title, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          trim(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}) = ''
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'is'
              and lower(coalesce(company_name, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          '${inputs.applied_search_location?.value ?? inputs.search_location.value}' = 'All'
          or search_location like '%' || '${inputs.applied_search_location?.value ?? inputs.search_location.value}' || '%'
      )
      and (
          'All' in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value}
          or exists (
              select 1
              from job_states as js
              where js.job_id = s.job_id
                and js.state_name in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value}
          )
      )
      and ('${inputs.applied_job_platform?.value ?? inputs.job_platform.value}' = 'All' or job_platform = '${inputs.applied_job_platform?.value ?? inputs.job_platform.value}')
      and ('${inputs.applied_listing_status?.value ?? inputs.listing_status.value}' = 'All' or listing_status = '${inputs.applied_listing_status?.value ?? inputs.listing_status.value}')
)
select
    skill,
    count(distinct job_id) as distinct_job_count
from filtered_skills
group by 1
order by distinct_job_count desc, skill
limit 15
```

```sql skill_demand_salary_impact
with job_states as (
    select distinct
        job_id,
        state_name
    from project_portfolio.jobs_detail_report
), filtered_skills as (
    select s.*
    from project_portfolio.rpt_job_skills as s
    where ${inputs.dashboard_load?.value} >= 1
      and posted_date between cast('${inputs.applied_posted_window?.start ?? inputs.posted_window.start}' as date) and cast('${inputs.applied_posted_window?.end ?? inputs.posted_window.end}' as date)
      and s.skill is not null
      and trim(s.skill) <> ''
      and ('${inputs.applied_search_term?.value ?? inputs.search_term.value}' = 'All' or search_term = '${inputs.applied_search_term?.value ?? inputs.search_term.value}')
      and ('${inputs.applied_job_level?.value ?? inputs.job_level.value}' = 'All' or job_level = '${inputs.applied_job_level?.value ?? inputs.job_level.value}')
      and ('${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}' = 'All' or degree_requirement = '${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}')
      and (
          trim(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}) = ''
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'is'
              and lower(coalesce(job_title, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          trim(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}) = ''
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'is'
              and lower(coalesce(company_name, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          '${inputs.applied_search_location?.value ?? inputs.search_location.value}' = 'All'
          or search_location like '%' || '${inputs.applied_search_location?.value ?? inputs.search_location.value}' || '%'
      )
      and (
          'All' in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value}
          or exists (
              select 1
              from job_states as js
              where js.job_id = s.job_id
                and js.state_name in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value}
          )
      )
      and ('${inputs.applied_job_platform?.value ?? inputs.job_platform.value}' = 'All' or job_platform = '${inputs.applied_job_platform?.value ?? inputs.job_platform.value}')
      and ('${inputs.applied_listing_status?.value ?? inputs.listing_status.value}' = 'All' or listing_status = '${inputs.applied_listing_status?.value ?? inputs.listing_status.value}')
), skill_salary_metrics as (
    select
        skill,
        count(distinct job_id) as distinct_job_count,
        avg(avg_annual_pay_range) as avg_annual_pay_range,
        count(distinct case when avg_annual_pay_range is not null then job_id end) as salary_job_count
    from filtered_skills
    group by 1
), ranked_skills as (
    select
        skill,
        distinct_job_count,
        avg_annual_pay_range,
        salary_job_count,
        salary_job_count * 1.0 / nullif(distinct_job_count, 0) as salary_coverage_pct,
        row_number() over (order by distinct_job_count desc, skill) as demand_rank,
        row_number() over (order by avg_annual_pay_range desc nulls last, skill) as salary_rank
    from skill_salary_metrics
    where avg_annual_pay_range is not null
      and salary_job_count >= 3
)
select
    skill,
    distinct_job_count,
    avg_annual_pay_range,
    salary_job_count,
    salary_coverage_pct
from ranked_skills
where demand_rank <= 40
   or salary_rank <= 40
order by distinct_job_count desc, avg_annual_pay_range desc nulls last, skill
limit 25
```

```sql skill_trend_over_time
with job_states as (
    select distinct
        job_id,
        state_name
    from project_portfolio.jobs_detail_report
), filtered_skills as (
    select s.*
    from project_portfolio.rpt_job_skills as s
    where ${inputs.dashboard_load?.value} >= 1
      and posted_date between cast('${inputs.applied_posted_window?.start ?? inputs.posted_window.start}' as date) and cast('${inputs.applied_posted_window?.end ?? inputs.posted_window.end}' as date)
      and s.skill is not null
      and trim(s.skill) <> ''
      and ('${inputs.applied_search_term?.value ?? inputs.search_term.value}' = 'All' or search_term = '${inputs.applied_search_term?.value ?? inputs.search_term.value}')
      and ('${inputs.applied_job_level?.value ?? inputs.job_level.value}' = 'All' or job_level = '${inputs.applied_job_level?.value ?? inputs.job_level.value}')
      and ('${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}' = 'All' or degree_requirement = '${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}')
      and (
          trim(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}) = ''
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'is'
              and lower(coalesce(job_title, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          trim(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}) = ''
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'is'
              and lower(coalesce(company_name, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          '${inputs.applied_search_location?.value ?? inputs.search_location.value}' = 'All'
          or search_location like '%' || '${inputs.applied_search_location?.value ?? inputs.search_location.value}' || '%'
      )
      and (
          'All' in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value}
          or exists (
              select 1
              from job_states as js
              where js.job_id = s.job_id
                and js.state_name in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value}
          )
      )
      and ('${inputs.applied_job_platform?.value ?? inputs.job_platform.value}' = 'All' or job_platform = '${inputs.applied_job_platform?.value ?? inputs.job_platform.value}')
      and ('${inputs.applied_listing_status?.value ?? inputs.listing_status.value}' = 'All' or listing_status = '${inputs.applied_listing_status?.value ?? inputs.listing_status.value}')
), top_skills as (
    select
        skill,
        count(distinct job_id) as distinct_job_count
    from filtered_skills
    group by 1
    order by distinct_job_count desc, skill
    limit 10
), monthly_skill_demand as (
    select
        date_trunc('month', fs.posted_date) as month_start_date,
        fs.skill,
        count(distinct fs.job_id) as distinct_job_count
    from filtered_skills as fs
    inner join top_skills as ts
        on fs.skill = ts.skill
    group by 1, 2
)
select
    strftime(month_start_date, '%b %Y') as month,
    skill,
    distinct_job_count
from monthly_skill_demand
order by month_start_date, skill
```

```sql skill_penetration_by_job_title
with filtered_jobs as (
    select distinct
        d.job_id,
        d.job_title
    from project_portfolio.jobs_detail_report as d
    where ${inputs.dashboard_load?.value} >= 1
      and d.posted_date between cast('${inputs.applied_posted_window?.start ?? inputs.posted_window.start}' as date) and cast('${inputs.applied_posted_window?.end ?? inputs.posted_window.end}' as date)
      and d.job_title is not null
      and trim(d.job_title) <> ''
      and ('${inputs.applied_search_term?.value ?? inputs.search_term.value}' = 'All' or d.search_term = '${inputs.applied_search_term?.value ?? inputs.search_term.value}')
      and ('${inputs.applied_job_level?.value ?? inputs.job_level.value}' = 'All' or d.job_level = '${inputs.applied_job_level?.value ?? inputs.job_level.value}')
      and ('${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}' = 'All' or d.degree_requirement = '${inputs.applied_degree_requirement?.value ?? inputs.degree_requirement.value}')
      and (
          trim(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}) = ''
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'is'
              and lower(coalesce(d.job_title, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(d.job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_job_title_match_method?.value ?? inputs.job_title_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_job_title_filter?.sql ?? inputs.job_title_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(d.job_title, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          trim(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}) = ''
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'is'
              and lower(coalesce(d.company_name, '')) in (
                  select lower(trim(value))
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'contains'
              and exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(d.company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
          or (
              '${inputs.applied_company_name_match_method?.value ?? inputs.company_name_match_method.value}' = 'does_not_contain'
              and not exists (
                  select 1
                  from unnest(string_split(${inputs.applied_company_name_filter?.sql ?? inputs.company_name_filter.sql}, '|||')) as t(value)
                  where trim(value) <> ''
                    and lower(coalesce(d.company_name, '')) like '%' || lower(trim(value)) || '%'
              )
          )
      )
      and (
          '${inputs.applied_search_location?.value ?? inputs.search_location.value}' = 'All'
          or d.search_location like '%' || '${inputs.applied_search_location?.value ?? inputs.search_location.value}' || '%'
      )
      and (
          'All' in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value}
          or d.state_name in ${inputs.applied_job_location_state?.value ?? inputs.job_location_state.value}
      )
      and ('${inputs.applied_job_platform?.value ?? inputs.job_platform.value}' = 'All' or d.job_platform = '${inputs.applied_job_platform?.value ?? inputs.job_platform.value}')
      and ('${inputs.applied_listing_status?.value ?? inputs.listing_status.value}' = 'All' or d.listing_status = '${inputs.applied_listing_status?.value ?? inputs.listing_status.value}')
), top_titles as (
    select
        job_title,
        count(distinct job_id) as title_job_count
    from filtered_jobs
    group by 1
    order by title_job_count desc, job_title
    limit 20
), top_title_jobs as (
    select
        fj.job_id,
        fj.job_title
    from filtered_jobs as fj
    inner join top_titles as tt
        on fj.job_title = tt.job_title
), cohort_job_skills as (
    select distinct
        ttj.job_id,
        ttj.job_title,
        trim(s.skill) as skill
    from top_title_jobs as ttj
    inner join project_portfolio.rpt_job_skills as s
        on ttj.job_id = s.job_id
    where s.skill is not null
      and trim(s.skill) <> ''
), top_skills as (
    select
        skill,
        count(distinct job_id) as skill_job_count
    from cohort_job_skills
    group by 1
    order by skill_job_count desc, skill
    limit 10
), title_skill_counts as (
    select
        cjs.job_title,
        cjs.skill,
        count(distinct cjs.job_id) as skill_title_job_count
    from cohort_job_skills as cjs
    inner join top_skills as ts
        on cjs.skill = ts.skill
    group by 1, 2
)
select
    tt.job_title,
    ts.skill,
    coalesce(tsc.skill_title_job_count, 0) * 1.0 / nullif(tt.title_job_count, 0) as penetration_pct,
    tt.title_job_count,
    ts.skill_job_count,
    coalesce(tsc.skill_title_job_count, 0) as skill_title_job_count
from top_titles as tt
cross join top_skills as ts
left join title_skill_counts as tsc
    on tt.job_title = tsc.job_title
   and ts.skill = tsc.skill
order by tt.title_job_count desc, tt.job_title, ts.skill_job_count desc, ts.skill
```

{#if dashboardLoaded}
<div class="main-chart-grid">

<div class="chart-card">
  <div class="section-title">Top Requested Skills</div>
  <BarChart
    data={top_requested_skills}
    x=skill
    y=distinct_job_count
    swapXY=true
    labels=true
    yAxisTitle="Distinct Jobs"
    xAxisTitle=""
    color="#4285f4"
    chartAreaHeight=360
  />
</div>

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
    yAxisTitle="Average Salary"
    xFmt=num0
    yFmt=usd0
    sizeFmt=num0
    chartAreaHeight=360
    tooltip={[
      { id: 'skill', showColumnName: false },
      { id: 'distinct_job_count', title: 'Jobs Requiring Skill', fmt: 'num0' },
      { id: 'avg_annual_pay_range', title: 'Average Salary', fmt: 'usd0' },
      { id: 'salary_coverage_pct', title: 'Salary Coverage', fmt: 'pct0' },
      { id: 'salary_job_count', title: 'Jobs With Salary', fmt: 'num0' }
    ]}
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

</div>

<div class="chart-card">
  <div class="section-title">Skill Trend Over Time</div>
  <LineChart
    data={skill_trend_over_time}
    x=month
    y=distinct_job_count
    series=skill
    sort=false
    xAxisTitle=""
    yAxisTitle="Distinct Jobs"
    yFmt=num0
    markers=true
    chartAreaHeight=320
  />
</div>

<div class="chart-card">
  <div class="section-title">Skill Penetration by Job Title</div>
  <Heatmap
    data={skill_penetration_by_job_title}
    x=skill
    y=job_title
    value=penetration_pct
    valueFmt=pct0
    min=0
    max=1
    xSort=skill_job_count
    xSortOrder=desc
    ySort=title_job_count
    ySortOrder=desc
    xAxisPosition=top
    xLabelRotation=-35
    valueLabels=true
    mobileValueLabels=false
    cellHeight=30
    chartAreaHeight=600
    leftPadding=150
    rightPadding=56
  />
</div>

{/if}

</div>
