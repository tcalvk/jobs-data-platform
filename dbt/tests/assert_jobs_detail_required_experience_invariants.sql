select job_id
from {{ ref('jobs_detail') }}
where required_years_experience < 0
   or (json_value(required_years_experience_metadata, '$.status') in ('unspecified', 'ambiguous')
       and required_years_experience is not null)
   or (json_value(required_years_experience_metadata, '$.status') = 'explicit_requirement'
       and required_years_experience is null)
