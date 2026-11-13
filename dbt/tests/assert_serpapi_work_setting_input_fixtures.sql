-- Literal-only fixtures: no refs, source scans, or model materialization.
with fixtures as (
    select
        'ordered_strings' as fixture,
        parse_json(r'''{"job":{"extensions":["  Remote ONLY ","ＨＹＢＲＩＤ","","  Remote ONLY ",null,12,true,{},[]],"job_highlights":[{"title":"“Work”–Setting","items":["  HOME\tOffice  ","",null,12,{},"  HOME\tOffice  "]},{"title":" Other ","items":["On—Site"]},{"items":["No title"]},null,{}, {"items":"invalid"}],"detected_extensions":{"work_from_home":true}}}''') as job_data,
        ['  Remote ONLY ', 'ＨＹＢＲＩＤ', '', '  Remote ONLY '] as expected_extensions,
        [struct('“Work”–Setting' as title, '  HOME\tOffice  ' as item),
         struct('“Work”–Setting', ''), struct('“Work”–Setting', '  HOME\tOffice  '),
         struct(' Other ', 'On—Site'), struct(cast(null as string), 'No title')] as expected_highlights,
        ['remote only', 'hybrid', '', 'remote only'] as expected_extensions_normalized,
        [struct('"work"-setting' as title, 'home office' as item),
         struct('"work"-setting', ''), struct('"work"-setting', 'home office'),
         struct('other', 'on-site'), struct(cast(null as string), 'no title')] as expected_highlights_normalized,
        true as expected_work_from_home
    union all
    select 'missing', json '{}', [], [], [], [], cast(null as bool)
    union all
    select 'nulls', json '{"job":{"extensions":null,"job_highlights":null,"detected_extensions":{"work_from_home":null}}}',
        [], [], [], [], null
    union all
    select 'wrong_types', json '{"job":{"extensions":{},"job_highlights":42,"detected_extensions":{"work_from_home":"unknown"}}}',
        [], [], [], [], null
    union all
    select 'false_not_null', json '{"job":{"extensions":[],"job_highlights":[],"detected_extensions":{"work_from_home":false}}}',
        [], [], [], [], false
    union all
    select 'string_boolean', json '{"job":{"detected_extensions":{"work_from_home":"true"}}}',
        [], [], [], [], true
    union all
    select 'non_scalar_boolean', json '{"job":{"detected_extensions":{"work_from_home":{"value":true}}}}',
        [], [], [], [], null
),
extracted as (
    select
        *,
        {{ serpapi_work_setting_extensions('job_data') }} as actual_extensions,
        {{ serpapi_work_setting_highlights('job_data') }} as actual_highlights,
        safe_cast(json_value(job_data, '$.job.detected_extensions.work_from_home') as bool) as actual_work_from_home
    from fixtures
),
normalized as (
    select
        *,
        array(
            select {{ normalize_work_setting_text('extension') }}
            from unnest(actual_extensions) as extension with offset as position
            order by position
        ) as actual_extensions_normalized,
        array(
            select as struct
                {{ normalize_work_setting_text('highlight.title') }} as title,
                {{ normalize_work_setting_text('highlight.item') }} as item
            from unnest(actual_highlights) as highlight with offset as position
            order by position
        ) as actual_highlights_normalized
    from extracted
)
select fixture
from normalized
where to_json_string(actual_extensions) != to_json_string(expected_extensions)
    or to_json_string(actual_highlights) != to_json_string(expected_highlights)
    or to_json_string(actual_extensions_normalized) != to_json_string(expected_extensions_normalized)
    or to_json_string(actual_highlights_normalized) != to_json_string(expected_highlights_normalized)
    or actual_work_from_home is distinct from expected_work_from_home
