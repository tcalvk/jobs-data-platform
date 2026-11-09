{% set patterns = work_setting_patterns() %}
with src as (
    select * from {{ ref('dim_job_listings') }}
)

, detail_day as (
    select * from {{ ref('jobs_detail_day') }}
)

, _agg as (
    select
        job_id,
        avg(avg_annual_pay_range) as avg_annual_pay_range,
        min(created_at_utc) as first_seen_at_utc,
        max(created_at_utc) as last_seen_at_utc
    from detail_day
    group by 1
)
, joined as (
    select
        s.* except (low_annual_pay_range, high_annual_pay_range, search_location),
        initcap(search_location) as search_location,
        a.avg_annual_pay_range,
        a.first_seen_at_utc,
        a.last_seen_at_utc
    from src s
    left join _agg a 
        using (job_id)
)

, derive_dates as (
    select *,
        if(
            date_diff(date(current_timestamp()), date(last_seen_at_utc), day) >= 21,
            date_add(date(last_seen_at_utc), interval 1 day),
            cast(null as date)
        ) as removed_date,
        if(
            posted_date_parsed is not null, 
                posted_date_parsed, 
            cast(first_seen_at_utc as date)
        ) as posted_date
    from joined 
)

, add_dims as (
    select *,
        if(
            removed_date is not null,  
            'Removed',
            'Active' 
        ) as listing_status,
        date_diff(cast(last_seen_at_utc as date), coalesce(posted_date, cast(created_at_utc as date)), day) as days_listed,
        case 
            when lower(job_title) like '%principal%' then 'Principal'
            when lower(job_title) like '%distinguished%' then 'Principal'
            when lower(job_title) like '%lead%' then 'Lead'
            when lower(job_title) like '%sr%' then 'Senior'
            when lower(job_title) like '%senior%' then 'Senior'
            when lower(job_title) like '%mid%' then 'Mid Level'
            when lower(job_title) like '%staff%' then 'Staff'
            when lower(job_title) like '% iii' then 'Mid Level'
            when lower(job_title) like '% ii' then 'Mid Level'
            when lower(job_title) like '% 3' then 'Mid Level'
            when lower(job_title) like '%entry%' then 'Entry'
            when lower(job_title) like '%junior%' then 'Entry'
            else 'Mid Level'
        end as job_level,
        
    from derive_dates
)

, work_setting_inputs as (
    select *, array_concat(
        [struct('title' as source, job_title as text, 3 as strength)],
        array(select as struct 'description' as source, fragment as text, 4 as strength
              from unnest(split(regexp_replace(
                  regexp_replace(coalesce(job_description, ''), r'(?i)\b(in[- ]person|remote|hybrid|onsite|on-site|office-based)\s*;\s*(remote|hybrid|onsite|on-site|office-based|in[- ]person)\b', r'\1 or \2'),
                  r'[.;]+', chr(30)), chr(30))) fragment),
        array(select as struct concat('highlight:', h.title) as source, h.item as text, 4 as strength
              from unnest(work_setting_highlights) h
              where lower(trim(h.title)) in ('responsibilities', 'job responsibilities', 'role', 'work location', 'work arrangement', 'schedule', 'description')),
        array(select as struct 'serpapi_extension' as source, e as text, 1 as strength
              from unnest(work_setting_extensions) e),
        array(select as struct 'linkedin_preferences' as source, e as text, 1 as strength
              from unnest(split(coalesce(work_setting_source_metadata, ''), '·')) e),
        if(work_from_home is not null,
           [struct('serpapi_wfh' as source, cast(work_from_home as string) as text, if(work_from_home, 1, 0) as strength)], [])
    ) as _ws_inputs
    from add_dims
)
, work_setting_normalized as (
    select * except (_ws_inputs),
        array(select as struct i.*, {{ normalize_work_setting_text('i.text') }} as normalized
              from unnest(_ws_inputs) i where nullif(trim(i.text), '') is not null) as _ws_inputs
    from work_setting_inputs
)
, work_setting_cleaned as (
    select * except (_ws_inputs), array(
        select as struct i.*,
            -- Experience is not a prohibition on remote attendance.
            regexp_replace(regexp_replace(normalized, r'\bno remote work experience\b', ''), r'{{ patterns.remote_neutral }}', '') as contextual,
            regexp_replace(regexp_replace(
                if(regexp_contains(normalized, r'{{ patterns.office_substantive }}|{{ patterns.office_week }}|{{ patterns.office_days_lead }}'),
                   normalized,
                   regexp_replace(normalized, r'{{ patterns.office_logistics }}', '')),
                r'{{ patterns.office_negation }}', ''), r'{{ patterns.office_label_negation }}', '') as office_context,
            coalesce(
                safe_cast(regexp_extract(regexp_replace(
                    if(regexp_contains(normalized, r'{{ patterns.office_substantive }}|{{ patterns.office_week }}|{{ patterns.office_days_lead }}'),
                       normalized,
                       regexp_replace(normalized, r'{{ patterns.office_logistics }}', '')),
                    r'{{ patterns.office_negation }}', ''), r'{{ patterns.office_week }}') as int64),
                safe_cast(regexp_extract(regexp_replace(
                    if(regexp_contains(normalized, r'{{ patterns.office_substantive }}|{{ patterns.office_week }}|{{ patterns.office_days_lead }}'),
                       normalized,
                       regexp_replace(normalized, r'{{ patterns.office_logistics }}', '')),
                    r'{{ patterns.office_negation }}', ''), r'{{ patterns.office_days_lead }}') as int64)
            ) as office_days,
            coalesce(
                safe_cast(regexp_extract(regexp_replace(regexp_replace(normalized, r'{{ patterns.remote_neutral }}', ''), r'{{ patterns.negation }}', ''), r'{{ patterns.remote_week }}') as int64),
                if(regexp_contains(normalized, r'{{ patterns.office_week }}|{{ patterns.office_days_lead }}'), safe_cast(regexp_extract(normalized, r'{{ patterns.remote_tail }}') as int64), null),
                if(regexp_contains(regexp_replace(regexp_replace(normalized, r'{{ patterns.remote_neutral }}', ''), r'{{ patterns.negation }}', ''), r'{{ patterns.friday_home }}'), 1, null)
            ) as remote_days,
            strength >= 3 as role_source
        from unnest(_ws_inputs) i
    ) as _ws_inputs
    from work_setting_normalized
)
, work_setting_scoped as (
    select * except (_ws_inputs), array(
        select as struct i.*,
            -- Onboarding is not a universal temporal exemption. Only a bounded
            -- few-day onsite introduction with clear ongoing remote work qualifies;
            -- remote-first -> onsite, week/month-long and other transitions do not.
            regexp_contains(contextual, r'\b(?:onsite|on-site|in[- ]office)\b[^.;]{0,45}\b(?:onboarding|orientation)\b')
                and regexp_contains(contextual, r'\b(?:[1-5]|one|two|three|four|five) (?:business )?days?\b')
                and regexp_contains(contextual, r'{{ patterns.role_remote }}|\b(?:then|thereafter|followed by) (?:fully |100% )?remote\b')
                and not regexp_contains(contextual, r'\bfirst (?:[a-z0-9]+ )?(?:weeks?|months?|years?)\b|\bremote\b[^.;]{0,100}\bthen (?:work )?(?:onsite|on-site|in[- ]office)\b') as short_onsite_onboarding,
            length(contextual) <= 240
                and (regexp_contains(contextual, r'{{ patterns.recurring }}') or (office_days is not null and remote_days is not null))
                and regexp_contains(office_context, r'\b(?:onsite|on-site|in[- ]office)\b')
                and (
                    regexp_contains(regexp_replace(contextual, r'{{ patterns.negation }}', ''), r'{{ patterns.role_remote }}|{{ patterns.remote_week }}|\bremote [1-4] days? (?:per|a|each) week\b')
                    or (office_days is not null and remote_days is not null)
                    or (regexp_contains(contextual, r'\balternat(?:e|ing) weeks?\b')
                        and regexp_contains(contextual, r'\b(?:remote|remotely|from home)\b'))
                )
                and (office_days is null or remote_days is null or office_days + remote_days <= 5)
                and not regexp_contains(regexp_replace(contextual, r'{{ patterns.negation }}', ''), r'\b(?:fully|100%|exclusively|strictly) (?:remote|onsite|on-site|in[- ]office)\b')
                and not regexp_contains(contextual, r'\b(?:annual|onboarding|orientation)\b|\bremote (?:systems?|sensing|access|control|support|desktop|monitoring)\b') as recurring_mix
        from unnest(_ws_inputs) i
    ) as _ws_inputs
    from work_setting_cleaned
)
, work_setting_signals as (
    select * except (_ws_inputs), array(
        select as struct i.*,
            role_source and (
                regexp_contains(regexp_replace(contextual, r'{{ patterns.negation }}', ''), r'{{ patterns.ambiguity }}')
                or regexp_contains(contextual, r'\bfor candidates (?:based|living|located)[^.;]{0,110}\b(?:hybrid|onsite|on-site|remote)\b')
                or regexp_contains(contextual, r'\bremote or [a-z -]{1,30}based\b|\boffice[^.;]{0,20}\bor (?:via )?(?:a )?remote\b')
                or (regexp_contains(contextual, r'\b(?:remote|onsite|on-site|office-based|in-person)\b[^.;]{0,100}\b(?:first (?:[a-z0-9]+ )?(?:days?|weeks?|months?|years?)|thereafter|subsequently|then (?:fully )?(?:remote|onsite|on-site|office-based|in-person))\b')
                    and not short_onsite_onboarding)
            ) as ambiguous,
            exists (
                select 1 from unnest(regexp_extract_all(contextual, r'{{ patterns.negation }}')) n
                where regexp_contains(n, r'\bremote|remotely|home\b')
            ) as negative_remote,
            role_source and (
                regexp_contains(regexp_replace(contextual, r'{{ patterns.negation }}', ''), r'{{ patterns.role_hybrid }}')
                or recurring_mix
                or (source = 'title' and regexp_contains(contextual, r'(?:^hybrid\s*(?:[-:]|$)|[([]\s*hybrid\s*[)\],:-])')
                    and not regexp_contains(contextual, r'\b(?:no|not) hybrid\b|\bhybrid (?:cloud|systems?|architecture|infrastructure|environments?|solutions?)\b'))
            ) as hybrid,
            role_source and (
                regexp_contains(regexp_replace(office_context, r'{{ patterns.negation }}', ''), r'{{ patterns.role_office }}')
                or (source = 'title' and regexp_contains(office_context, r'\b(?:onsite|on-site|in-office)\b'))
            ) and not regexp_contains(contextual, r'\b(?:occasional|occasionally|occasions|annual|once a year|onboarding|orientation|as needed|as required|when needed|when required|periodically|periodic|from time to time|ad hoc)\b|\bif (?:this|the) (?:position|role) is (?:listed|designated)\b|\b(?:not|no) (?:required (?:to be )?)?(?:onsite|on-site|in-office|in-person)\b') as office,
            role_source and (
                regexp_contains(regexp_replace(regexp_replace(contextual, r'{{ patterns.negation }}', ''), r'\bremote (?:systems?|sensing|access|control|support|desktop|monitoring)\b', ''), r'{{ patterns.role_remote }}')
                or (remote_days is not null and not regexp_contains(contextual, r'{{ patterns.negation }}'))
                or (short_onsite_onboarding and regexp_contains(contextual, r'\b(?:then|thereafter|followed by) (?:fully |100% )?remote\b'))
                or (source = 'title' and regexp_contains(contextual, r'\bremote\b')
                    and not regexp_contains(contextual, r'{{ patterns.negation }}|\bnon-remote\b|\bremote (?:systems?|sensing|access|control|support|desktop|monitoring)\b'))
            ) as remote
        from unnest(_ws_inputs) i
    ) as _ws_signals
    from work_setting_scoped
)
, work_setting_evidence as (
    select * except (_ws_signals), array_concat(
        array(select as struct source, text, normalized, strength,
            case when ambiguous then 'Unknown'
                 when hybrid then 'Hybrid'
                 when office and remote then 'Unknown'
                 when office then 'Office' when remote then 'Remote'
                 when source in ('serpapi_extension', 'linkedin_preferences') and normalized in ('remote', 'work from home', 'wfh') then 'Remote'
                 when source in ('serpapi_extension', 'linkedin_preferences') and normalized = 'hybrid' then 'Hybrid'
                 when source in ('serpapi_extension', 'linkedin_preferences') and normalized in ('onsite', 'on-site', 'on site', 'in office', 'office') then 'Office'
                 when source = 'serpapi_wfh' and normalized = 'true' then 'Remote'
                 else 'Unknown' end as setting,
            ambiguous or (office and remote and not recurring_mix)
                or (hybrid and not recurring_mix and (
                    (office and office_days is null) or (remote and remote_days is null)))
                or (source = 'title' and hybrid and (office or remote)) as conflict,
            negative_remote,
            if(office and not ambiguous and not negative_remote and not regexp_contains(contextual, r'\b(?:fully|100%|exclusively|only|strictly|annual|year|travel|onboarding|orientation)\b'), office_days, null) as office_days,
            if(remote and not ambiguous and not negative_remote and not regexp_contains(contextual, r'\b(?:fully|100%|exclusively|only|strictly|annual|year|travel|onboarding|orientation)\b'), remote_days, null) as remote_days
          from unnest(_ws_signals)
          where hybrid or office or remote or ambiguous or negative_remote
             or (source in ('serpapi_extension', 'linkedin_preferences') and normalized in ('remote', 'work from home', 'wfh', 'hybrid', 'onsite', 'on-site', 'on site', 'in office', 'office'))
             or source = 'serpapi_wfh'),
        -- Tags are separate lower-strength evidence, never promoted by their sentence.
        array(select as struct concat(source, ':li_tag') as source, text, normalized,
                2 as strength, case tag when '#li-remote' then 'Remote' when '#li-hybrid' then 'Hybrid' else 'Office' end as setting,
                false as conflict, false as negative_remote,
                cast(null as int64) as office_days, cast(null as int64) as remote_days
              from unnest(_ws_signals)
              cross join unnest(regexp_extract_all(normalized, r'#li-(?:remote|hybrid|onsite|on-site)\b')) tag
              where role_source),
        -- Company assertions are lower than every actual role/title/tag/metadata
        -- signal. A strong Unknown conflict or prohibition also blocks fallback.
        array(select as struct concat('company_policy:', source) as source, text, normalized,
                -1 as strength,
                case when regexp_contains(contextual, r'{{ patterns.company_remote }}') and regexp_contains(contextual, r'{{ patterns.company_hybrid }}') then 'Unknown'
                     when regexp_contains(contextual, r'{{ patterns.company_remote }}') then 'Remote' else 'Hybrid' end as setting,
                regexp_contains(contextual, r'{{ patterns.company_remote }}') and regexp_contains(contextual, r'{{ patterns.company_hybrid }}') as conflict,
                false as negative_remote, cast(null as int64) as office_days, cast(null as int64) as remote_days
              from unnest(_ws_signals)
              where role_source and source != 'title'
                and regexp_contains(contextual, r'{{ patterns.company_remote }}|{{ patterns.company_hybrid }}')
                and not regexp_contains(contextual, r'{{ patterns.company_guard }}')),
        -- Last-resort duty inference, never a title/skill or missing-WFH default.
        -- Strong Unknown evidence is ranked above this just like an affirmative
        -- role arrangement, so unresolved options/transitions stay Unknown.
        array(select as struct concat('physical_duties:', source) as source, text, normalized,
                -2 as strength, 'Office' as setting, false as conflict, false as negative_remote,
                cast(null as int64) as office_days, cast(null as int64) as remote_days
              from unnest(_ws_signals)
              where role_source and source != 'title' and not ambiguous and not negative_remote
                and regexp_contains(contextual, r'{{ patterns.physical_care }}|{{ patterns.physical_operations }}')
                and not regexp_contains(contextual, r'{{ patterns.physical_guard }}'))
    ) as work_setting_evidence
    from work_setting_signals
)
, work_setting_compatible_mix as (
    select * except (work_setting_evidence), array_concat(e.work_setting_evidence, array(
        -- Merge only quantified recurring components from the SAME role-text scope.
        -- 3 office days + 2 home days is a mix; arbitrary onsite/remote words are not.
        -- Full/exclusive assertions and temporal/ambiguous fragments have no day
        -- component, so they cannot be neutralized by this compatibility rule.
        select as struct concat(o.source, ':weekly_mix') as source,
            concat(o.text, '. ', r.text) as text, concat(o.normalized, '. ', r.normalized) as normalized,
            o.strength, 'Hybrid' as setting, false as conflict, false as negative_remote,
            cast(null as int64) as office_days, cast(null as int64) as remote_days
        from unnest(e.work_setting_evidence) o cross join unnest(e.work_setting_evidence) r
        where o.source = r.source and o.strength = r.strength
          and o.office_days + r.remote_days <= 5
          and not o.conflict and not r.conflict and not o.negative_remote
    )) as work_setting_evidence
    from work_setting_evidence e
)
, work_setting_ranked as (
    select *, (select max(if(setting != 'Unknown' or conflict or negative_remote, strength, null)) from unnest(e.work_setting_evidence)) as _ws_strength
    from work_setting_compatible_mix e
)
, work_setting_compatible as (
    select *, array(
        -- A partial weekly attendance component is compatible with an explicit
        -- Hybrid assertion in the same scope. Unqualified/full Office or Remote
        -- assertions stay contradictory: there is no blanket Hybrid precedence.
        select case when (office_days is not null or remote_days is not null)
                         and exists (select 1 from unnest(work_setting_evidence) h
                                     where h.strength = e.strength and h.setting = 'Hybrid' and not h.conflict
                                       and (h.source = e.source or h.source = concat(e.source, ':weekly_mix')))
                    then 'Hybrid' else setting end as setting
        from unnest(work_setting_evidence) e where strength = _ws_strength
    ) as _ws_effective_settings
    from work_setting_ranked
)
, work_setting_resolved as (
    select *,
        (select logical_or(conflict)
             or (select count(distinct s) from unnest(_ws_effective_settings) s where s != 'Unknown') > 1
             or (logical_or(negative_remote) and countif(setting = 'Remote') > 0)
         from unnest(work_setting_evidence) where strength = _ws_strength) as _ws_conflict,
        (select max(nullif(s, 'Unknown')) from unnest(_ws_effective_settings) s) as _ws_setting
    from work_setting_compatible
)
, work_setting_output as (
select * except (_ws_strength, _ws_conflict, _ws_setting, _ws_effective_settings,
                 work_setting_extensions, work_setting_highlights, work_from_home, work_setting_source_metadata),
    if(coalesce(_ws_conflict, false), 'Unknown', coalesce(_ws_setting, 'Unknown')) as work_setting,
    case when coalesce(_ws_conflict, false) then 'conflicting_or_ambiguous_evidence'
         when _ws_setting is null then 'insufficient_evidence'
         when _ws_strength >= 3 then 'explicit_role_setting'
         when _ws_strength = 2 then 'li_tag_fallback'
         when _ws_strength = -1 then 'company_policy_inference'
         when _ws_strength = -2 then 'physical_duties_inference'
         else 'metadata_fallback' end as work_setting_rule,
    case when coalesce(_ws_conflict, false) or _ws_setting is null or _ws_strength < 0 then 'low'
         when _ws_strength >= 3 then 'high' else 'medium' end as work_setting_confidence,
    coalesce(_ws_conflict, false) as work_setting_conflict
from work_setting_resolved
)
select * except (work_setting_rule, work_setting_evidence, work_setting_confidence, work_setting_conflict),
    to_json(struct(
        work_setting_rule as rule,
        work_setting_evidence as evidence,
        work_setting_confidence as confidence,
        work_setting_conflict as conflict
    )) as work_setting_metadata
from work_setting_output
