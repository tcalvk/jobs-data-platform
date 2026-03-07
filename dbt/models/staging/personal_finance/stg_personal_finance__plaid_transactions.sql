with source as (
    
    select 
        date,
        plaid_amount,
        business,
        plaid_category,
        transaction_id,
        account,
        status,
        coalesce(category_id_override, category_id_plaid) as category_id,
        amount_override,
        category,
        amount,
        transaction_type,
        category_id_override,
        category_id_plaid,
        'plaid_transactions' as source
    from {{ source('personal_finance', 'plaid_transactions') }}

)

select * from source