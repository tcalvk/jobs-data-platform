select 
    created_at,
    user_id,
    vehicle_id,
    odo_miles
from {{ ref('stg_tesla_data_platform__vehicle_info') }}
