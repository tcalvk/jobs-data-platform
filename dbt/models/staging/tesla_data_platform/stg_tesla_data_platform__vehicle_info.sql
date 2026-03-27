with source as (
    
    select 
        created_at,
        user_id,
        vehicle_id,
        odo_miles
    from {{ source('tesla_data_platform', 'vehicle_info') }}

)

select * from source
