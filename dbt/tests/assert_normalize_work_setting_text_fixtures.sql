with fixtures as (
    select cast(null as string) as original, cast(null as string) as expected
    union all select '', ''
    union all select ' \t\r\n \u2003 ', ''
    union all select '  ＨＹＢＲＩＤ\t\nOffice  Based  ', 'hybrid office based'
    union all select '‘Remote’ “ONLY”', concat(chr(39), 'remote', chr(39), ' "only"')
    union all select '‐‑‒–—―−', '-------'
    union all select 'e\u0301', 'é'
    union all select 'Not REMOTE / Austin, TX', 'not remote / austin, tx'
)
select original, expected, {{ normalize_work_setting_text('original') }} as actual
from fixtures
where {{ normalize_work_setting_text('original') }} is distinct from expected
