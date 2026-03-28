-- Includes all service types from the fact model (not limited to notification-driven services),
-- joined with vehicle and user info for a full picture of recent maintenance history.

select
    sr.service_record_id,
    u.user_id,
    u.name as user_name,
    u.email,
    sr.vehicle_id,
    sr.vehicle_name,
    sr.vin,
    sr.service_id,
    sr.service_description,
    sr.completed_date,
    sr.mileage_stamp,
    sr.total_cost,
    date_diff(current_date, sr.completed_date, day) as days_ago

from {{ ref('fact_tesla_service_records') }} sr
left join {{ ref('dim_tesla_app_vehicles') }} v on v.vin = sr.vin
left join {{ ref('dim_tesla_app_users') }} u on u.user_id = v.user_id

order by sr.completed_date desc
