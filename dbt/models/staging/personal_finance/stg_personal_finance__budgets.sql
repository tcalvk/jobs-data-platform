with source as (
    
    select 
        category_id,
        amount,
        start_date,
        end_date
    from {{ source('personal_finance', 'budgets') }}

)

select * from source
