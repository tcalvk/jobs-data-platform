{% macro generate_partitions_to_replace() -%}
    {# num_days includes the invocations UTC date; default: three UTC calendar days. #}
    {%- set raw_num_days = var('num_days', 3) -%}
    {%- set num_days_text = raw_num_days | string | trim -%}

    {%- if not modules.re.match('^[1-9][0-9]*$', num_days_text) -%}
        {{ exceptions.raise_compiler_error(
            "The 'num_days' variable must be a positive integer; received: " ~ raw_num_days
        ) }}
    {%- endif -%}

    {%- set num_days = num_days_text | int -%}
    {# dbt guarantees run_started_at is UTC, so no timezone conversion is needed. #}
    {%- set run_date_utc = run_started_at.date() -%}
    {%- set partitions = [] -%}

    {%- for day_offset in range(num_days) -%}
        {%- set partition_date = run_date_utc - modules.datetime.timedelta(days=day_offset) -%}
        {%- do partitions.append("date('" ~ partition_date.isoformat() ~ "')") -%}
    {%- endfor -%}

    {{ return(partitions) }}
{%- endmacro %}
