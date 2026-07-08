with source as (
    
    select 
        Date,
        _Amount_,
        Business,
        Description,
        Category,
        TransactionID,
        Account,
        Status,
        Category_Id__BSA_,
        Last_Month,
        To_Review,
        Reviewed,
        Category_Id_Override,
        Amount_Override,
        Category_Override,
        Category__final__,
        Amount__final_,
        Month,
        Transaction_Type
    from {{ source('personal_finance', 'plaid_transactions') }}

),

renamed as (

    select 
        Date as date,
        _Amount_ as plaid_amount,
        Business as business,
        Description as description,
        Category as plaid_category,
        TransactionID as transaction_id,
        Account as account,
        Status as status,
        coalesce(
            Category_Id_Override, 
            safe_cast(Category_Id__BSA_ as int64)
        ) as category_id,
        Amount_Override as amount_override,
        Category__final__ as category,
        Amount__final_ as amount,
        Transaction_Type as transaction_type,
        Category_Id_Override as category_id_override,
        Category_Id__BSA_ as category_id_plaid,
        'plaid_transactions' as source
    from source
    where Date is not null -- Remove blank rows in the sheet 

)

select * from renamed