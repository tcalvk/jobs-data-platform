with source as (
    
    select 
        user_id,
        created_at,
        email,
        name
    from {{ source('tesla_data_platform', 'app_users') }}

)

select * from source
