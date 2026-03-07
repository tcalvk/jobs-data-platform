with source as (
    
    select 
        Account_Id as account_id,
        Account_Name as name,
        Account_Type as account_type,
        Balance__report_month_ as balance_report_month,
        Update_Method as update_method
    from {{ source('personal_finance', 'accounts') }}

)

select * from source