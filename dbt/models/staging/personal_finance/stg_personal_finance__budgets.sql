with source as (
    
    select 
        Category_Id,
        Amount,
        Start_Date,
        End_Date
    from {{ source('personal_finance', 'budgets') }}

),

renamed as (
    select 
        Category_Id as category_id,
        Amount as amount,
        Start_Date as start_date,
        End_Date as end_date
    from source 
)

select * from renamed
