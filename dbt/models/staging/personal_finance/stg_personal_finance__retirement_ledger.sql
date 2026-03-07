with source as (
    
    select 
        Period as period,
        Year as year,
        Age as age,
        Household_Income as household_income,
        Expenses as expenses,
        Contributions as contributions,
        Withdrawals as withdrawals,
        Returns as returns, 
        Beginning_Bal as beginning_bal,
        Ending_Bal as ending_bal
    from {{ source('personal_finance', 'retirement_ledger') }}

)

select * from source