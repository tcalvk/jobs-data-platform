{% macro normalize_work_setting_text(expression) -%}
    {# Keep NULL distinct from ''; normalize only derived evidence, never source text. #}
    trim(regexp_replace(
        translate(
            lower(normalize({{ expression }}, NFKC)),
            '\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u00a0',
            concat(repeat(chr(39), 4), repeat(chr(34), 4), repeat('-', 7), ' ')
        ),
        r'[\s\p{Z}]+',
        ' '
    ))
{%- endmacro %}
