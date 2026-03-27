with source as (
    
    select 
        vehicle_id,
        added_at as created_at,
        display_name,
        user_id,
        vin
    from {{ source('tesla_data_platform', 'app_vehicles') }}

)

select * from source
