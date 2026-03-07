select 
    cast(account_id as string) as account_id,
    name as account_name,
    account_type,
    update_method
from {{ ref('stg_personal_finance__accounts') }}