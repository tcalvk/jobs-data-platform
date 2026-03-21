with source as (
    
    select 
        CategoryId,
        Amount,
        TransactionDate,
        CategoryName,
        AccountId,
        Account_Name,
        TransactionId,
        Category_Type,
        Tran_Type
    from {{ source('personal_finance', 'manual_transactions') }}
    
),

renamed as (

    select 
        CategoryId as category_id,
        Amount as amount,
        TransactionDate as date,
        CategoryName as category,
        Account_Name as account,
        cast(TransactionId as string) as transaction_id,
        Tran_Type as transaction_type,
        cast(null as string) as status,
        'manual_transactions' as source
    from source

)

select * from renamed