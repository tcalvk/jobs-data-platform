with source as (
    
    select 
        category_id,
        amount,
        date,
        category,
        account,
        cast(transaction_id as string) as transaction_id,
        transaction_type,
        cast(null as string) as status,
        'manual_transactions' as source
    from {{ source('personal_finance', 'manual_transactions') }}

)

select * from source