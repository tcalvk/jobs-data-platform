---
title: Career Opportunity Explorer
full_width: true
sidebar: hide
hide_toc: true
hide_breadcrumbs: true
---

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

  .filter-grid :global(button) {
    width: 100%;
    min-width: 0 !important;
    max-width: 100%;
    justify-content: space-between;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .filter-grid :global(svg) {
    flex: 0 0 auto;
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
from project_portfolio.career_jobs
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
        from project_portfolio.career_jobs
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
with options as (
    select
        search_location,
        search_location as search_location_label,
        row_number() over (order by search_location) as option_rank
    from (
        select distinct search_location
        from project_portfolio.career_jobs
        where search_location is not null
    )
)
select 'All' as search_location, '𝐀𝐥𝐥 Values' as search_location_label, 0 as ordinal
union all
select search_location, search_location_label, option_rank as ordinal
from options
order by ordinal
```

```sql job_platforms
with platform_counts as (
    select
        job_platform,
        count(distinct job_id) as record_count
    from project_portfolio.career_jobs
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
        from project_portfolio.career_jobs
        where listing_status is not null
    )
)
select 'All' as listing_status, '𝐀𝐥𝐥 Values' as listing_status_label, 0 as ordinal
union all
select listing_status, listing_status_label, option_rank as ordinal
from options
order by ordinal
```

<div class="coe-page">

<div class="filter-grid">
  <Dropdown data={search_terms} name=search_term value=search_term label=search_term_label order=ordinal title="Search Term" defaultValue="All" />
  <Dropdown data={job_platforms} name=job_platform value=job_platform label=job_platform_label order=ordinal title="Job Platform" defaultValue="All" />
  <Dropdown data={listing_statuses} name=listing_status value=listing_status label=listing_status_label order=ordinal title="Listing Status" defaultValue="All" />
  <DateRange name=posted_window data={available_dates} dates=posted_date defaultValue="Last 90 Days" />
  <Dropdown data={search_locations} name=search_location value=search_location label=search_location_label order=ordinal title="Search Location" defaultValue="United States" />
</div>

```sql kpis
select
    count(distinct case when listing_status = 'Active' then job_id end) as active_jobs,
    count(distinct case when posted_date >= cast('${inputs.posted_window.end}' as date) - interval '7 day' then job_id end) as new_jobs_last_7_days,
    count(distinct case when listing_status = 'Active' then company_name end) as companies_hiring,
    avg(case when listing_status = 'Active' then days_listed end) as avg_days_listed_active,
    avg(case when listing_status = 'Active' then avg_annual_pay_range end) as avg_salary_active,
    count(distinct case when listing_status = 'Active' then job_platform end) as job_platforms_active
from project_portfolio.career_jobs
where posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
  and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
  and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
  and ('${inputs.job_platform.value}' = 'All' or job_platform = '${inputs.job_platform.value}')
  --and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
```

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-title">Active Jobs</div>
    <div class="kpi-value-box"><BigValue data={kpis} value=active_jobs fmt=num0 /></div>
  </div>
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

```sql top_terms
select
    search_term,
    round(avg(opportunity_score), 1) as opportunity_score
from project_portfolio.career_jobs
where posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
  and opportunity_score is not null
  and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
  and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
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
    count(distinct job_id) as job_count,
    avg(avg_annual_pay_range) as avg_annual_pay_range,
    coalesce(avg(opportunity_score), 1) as opportunity_score
from project_portfolio.career_jobs
where posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
  and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
  and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
  and ('${inputs.job_platform.value}' = 'All' or job_platform = '${inputs.job_platform.value}')
  and ('${inputs.listing_status.value}' = 'All' or listing_status = '${inputs.listing_status.value}')
group by 1
having count(distinct job_id) > 0
order by opportunity_score desc
limit 25
```

<div class="chart-card">
  <div class="section-title">Job Demand vs Pay (Size = Opportunity Score)</div>
  <ScatterPlot
    data={demand_vs_pay}
    x=avg_annual_pay_range
    y=job_count
    size=opportunity_score
    series=search_term
    xAxisTitle="Avg Annual Pay Range"
    yAxisTitle="Job Count"
    xFmt=usd0
    yFmt=num0
    chartAreaHeight=280
  />
</div>

```sql days_listed_distribution
with binned as (
    select
        cast(floor(coalesce(days_listed, 0) / 2) * 2 as int) as bin_start,
        job_id
    from project_portfolio.career_jobs
    where days_listed is not null
      and days_listed >= 0
      and days_listed < 32
      and posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
      and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
      and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
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

<div class="chart-card">
  <div class="section-title">Distribution of Days Listed</div>
  <BarChart
    data={days_listed_distribution}
    x=days_bucket
    y=record_count
    series=record_series
    color="#4285f4"
    yAxisTitle="Record Count"
    xAxisTitle=""
    yFmt=num0
    chartAreaHeight=260
  />
</div>

```sql jobs_by_location
select
    state_name as point_name,
    lat,
    long,
    count(distinct job_id) as jobs_posted
from project_portfolio.career_jobs
where lat is not null
  and long is not null
  and posted_date between cast('${inputs.posted_window.start}' as date) and cast('${inputs.posted_window.end}' as date)
  and ('${inputs.search_term.value}' = 'All' or search_term = '${inputs.search_term.value}')
  and ('${inputs.search_location.value}' = 'All' or search_location = '${inputs.search_location.value}')
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
