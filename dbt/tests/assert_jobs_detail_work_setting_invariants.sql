with metadata as (
    select *,
        json_value(work_setting_metadata, '$.rule') as rule,
        json_value(work_setting_metadata, '$.confidence') as confidence,
        safe_cast(json_value(work_setting_metadata, '$.conflict') as bool) as conflict,
        json_query_array(work_setting_metadata, '$.evidence') as evidence
    from {{ ref('jobs_detail') }}
)
select job_id
from metadata
where work_setting is null
   or work_setting not in ('Office', 'Hybrid', 'Remote', 'Unknown')
   or work_setting_metadata is null
   or json_type(work_setting_metadata) != 'object'
   or to_json_string(json_keys(work_setting_metadata)) != '["confidence","conflict","evidence","rule"]'
   or json_type(json_query(work_setting_metadata, '$.rule')) != 'string'
   or json_type(json_query(work_setting_metadata, '$.confidence')) != 'string'
   or json_type(json_query(work_setting_metadata, '$.conflict')) != 'boolean'
   or json_type(json_query(work_setting_metadata, '$.evidence')) != 'array'
   or confidence is null or confidence not in ('high', 'medium', 'low')
   or conflict is null
   or rule is null
   or rule not in ('explicit_role_setting', 'li_tag_fallback', 'metadata_fallback',
                   'insufficient_evidence', 'conflicting_or_ambiguous_evidence', 'company_policy_inference', 'physical_duties_inference')
   or (conflict and work_setting != 'Unknown')
   or (work_setting = 'Unknown' and confidence != 'low')
   or (work_setting != 'Unknown' and not exists (
       select 1 from unnest(evidence) e where json_value(e, '$.setting') = work_setting
   ))
   or (rule in ('metadata_fallback', 'li_tag_fallback') and confidence != 'medium')
   or (rule = 'explicit_role_setting' and confidence != 'high')
   or (rule in ('company_policy_inference', 'physical_duties_inference') and confidence != 'low')
   or (rule = 'physical_duties_inference' and work_setting != 'Office')
   or (rule = 'company_policy_inference' and work_setting not in ('Remote', 'Hybrid'))
   or (rule = 'physical_duties_inference' and not exists (
       select 1 from unnest(evidence) e where starts_with(json_value(e, '$.source'), 'physical_duties:')
   ))
   or (rule = 'company_policy_inference' and not exists (
       select 1 from unnest(evidence) e where starts_with(json_value(e, '$.source'), 'company_policy:')
   ))
   or exists (
       select 1 from unnest(evidence) e
       where json_type(e) != 'object'
          or json_value(e, '$.text') is null or json_value(e, '$.normalized') is null
          or json_value(e, '$.source') is null
          or safe_cast(json_value(e, '$.strength') as int64) not in (-2, -1, 0, 1, 2, 3, 4)
          or json_value(e, '$.setting') not in ('Office', 'Hybrid', 'Remote', 'Unknown')
          or json_type(json_query(e, '$.conflict')) != 'boolean'
          or json_type(json_query(e, '$.negative_remote')) != 'boolean'
   )
