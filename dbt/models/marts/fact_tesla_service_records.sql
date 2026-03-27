select
    service_record_id,
    vehicle_id,
    vehicle_name,
    vin,
    service_id,
    service_description,
    completed_date,
    total_cost,
    mileage_stamp
from {{ ref('stg_tesla_data_platform__service_records') }}
