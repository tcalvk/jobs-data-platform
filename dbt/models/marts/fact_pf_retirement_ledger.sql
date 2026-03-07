select 
    period,
    year,
    age,
    household_income,
    expenses,
    contributions,
    withdrawals,
    returns, 
    beginning_bal,
    ending_bal
from {{ ref('stg_personal_finance__retirement_ledger') }}