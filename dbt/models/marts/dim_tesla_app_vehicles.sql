select 
    vehicle_id,
    created_at,
    display_name,
    user_id,
    vin
from {{ ref('stg_tesla_data_platform__app_vehicles') }}
