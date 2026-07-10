{% set run_date = run_started_at.date() %}
{% set first_day_this_month = run_date.replace(day=1) %}
{% set last_day_previous_month = first_day_this_month - modules.datetime.timedelta(days=1) %}
{% set first_day_previous_month = last_day_previous_month.replace(day=1) %}
{% set partitions_to_replace = [] %}

{% for day_offset in range(last_day_previous_month.day) %}
    {% set partition_date = first_day_previous_month + modules.datetime.timedelta(days=day_offset) %}
    {% do partitions_to_replace.append("date '" ~ partition_date.isoformat() ~ "'") %}
{% endfor %}

{{
    config(
        materialized='incremental',
        tags=['monthly_incremental_refresh'],
        partition_by={
            "field": "date",
            "data_type": "date",
            "granularity": "day"
        },
        incremental_strategy='insert_overwrite',
        partitions=partitions_to_replace
    )
}}

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

    {% if is_incremental() %}
        where Date between date '{{ first_day_previous_month.isoformat() }}'
            and date '{{ last_day_previous_month.isoformat() }}'
    {% endif %}

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
