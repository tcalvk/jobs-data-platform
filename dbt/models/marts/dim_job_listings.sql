{% set sources = [
  ref('int_jobs_scraping__serpapi_jobs'),
  ref('int_jobs_scraping__linkedin_jobs')
] %}

{% set columns = [
    'created_at_utc',
    'created_at_mst',
    'platform_job_id',
    'job_title',
    'company_name',
    'search_location',
    'search_term',
    'job_location',
    'job_platform',
    'posted_date',
    'schedule_type',
    'low_annual_pay_range',
    'high_annual_pay_range',
    'job_description',
    'data_source',
    'degree_requirement',
] %}

with unioned as (
  {% for src in sources %}
    
    select
      {% for col in columns %}
        {{ col }}{% if not loop.last %},{% endif %}
      {% endfor %}
    from {{ src }}
    
    {% if not loop.last %}union all{% endif %}
  
  {% endfor %}
),

gen_surr_key as (
  select *,
    {{ dbt_utils.generate_surrogate_key([
      'platform_job_id',
      'company_name',
      'data_source',
      'search_term',
      'search_location'
    ]) }} as job_id
    from unioned
),

dedupe as (
  select *
  from gen_surr_key
  qualify row_number() over (
    partition by job_id 
    order by posted_date asc -- Get the first appearance of a given job for the dim table 
  ) = 1          
)

select 
  d.*,
  max(g.created_at_utc) as last_seen_at_utc
from dedupe d 
left join gen_surr_key g 
  using (job_id) 
group by all 
