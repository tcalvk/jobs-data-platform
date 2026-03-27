select 
    user_id,
    created_at,
    email,
    name
from {{ ref('stg_tesla_data_platform__app_users') }}
