{# Shared by the model and literal-fixture tests so extraction cannot drift. #}
{% macro serpapi_work_setting_extensions(job_data) -%}
    array(
        select json_value(extension)
        from unnest(json_query_array({{ job_data }}, '$.job.extensions')) as extension
        with offset as extension_offset
        where json_type(extension) = 'string'
        order by extension_offset
    )
{%- endmacro %}

{% macro serpapi_work_setting_highlights(job_data) -%}
    array(
        select as struct
            json_value(section, '$.title') as title,
            json_value(item) as item
        from unnest(json_query_array({{ job_data }}, '$.job.job_highlights')) as section
        with offset as section_offset
        cross join unnest(json_query_array(section, '$.items')) as item
        with offset as item_offset
        where json_type(item) = 'string'
        order by section_offset, item_offset
    )
{%- endmacro %}
