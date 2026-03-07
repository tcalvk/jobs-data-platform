select 
    date,
    balance,
    balance_available,
    balance_limit,
    usage_pct,
    cast(account_id as string) as account_id,
    account_name
from {{ ref('stg_personal_finance__bsa_balances') }}