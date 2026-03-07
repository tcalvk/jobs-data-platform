with retirement_ledger as (
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
    from {{ ref('fact_pf_retirement_ledger') }}
),

budgets as (
    select 
        category_id,
        amount,
        start_date,
        end_date
    from {{ ref('dim_pf_budgets') }}
),

categories as (
    select 
        category_id,
        category_name,
        description,
        active,
        category_type,
        vh_balance
    from {{ ref('dim_pf_categories') }}
),

account_balances as (
    select 
        date,
        date_trunc(date, month) as month,
        balance,
        balance_available,
        balance_limit,
        usage_pct,
        account_id,
        account_name
    from {{ ref('fact_pf_account_balances') }}
),

accounts as (
    select 
        account_id,
        account_name,
        account_type,
        update_method
    from {{ ref('dim_pf_accounts') }}
),

eomonth_bal as (
    select 
        ab.month,
        ab.balance,
        ab.account_id 
    from account_balances ab 
    left join accounts a 
        using (account_name) 
    where a.account_type = 'Retirement' -- only grab retirement accounts for the join
    and ab.month <= date_trunc(date_add(cast(current_timestamp() as date), interval -1 month), month)
    qualify row_number() over(partition by ab.month, ab.account_name order by ab.date desc) = 1 -- sometimes account_id is null in this table, so use name instead
),

joined_bal as (
    select 
        l.*,
        sum(bal.balance) as ending_bal_actual -- sum the bal of all retirement accounts 
    from retirement_ledger l 
    left join eomonth_bal bal 
        on l.period = bal.month 
    group by all 
),

joined_budgets as (
    select 
        j.*,
        nullif(sum(case when c.category_type = 'Monthly Expense' and j.period <= date_trunc(date_add(cast(current_timestamp() as date), interval -1 month), month) then b.amount else 0 end),0) as actual_monthly_expense,
        nullif(sum(case when c.category_type = 'Annual Expense' and j.period <= date_trunc(date_add(cast(current_timestamp() as date), interval -1 month), month) then b.amount else 0 end) / 12, 0) as actual_annual_expense,
        nullif(sum(case when c.category_type = 'Monthly Income' and j.period <= date_trunc(date_add(cast(current_timestamp() as date), interval -1 month), month) then b.amount else 0 end), 0) as actual_household_income, 
    from joined_bal j 
    left join budgets b 
        on j.period between b.start_date and b.end_date
    left join categories c 
        using (category_id) 
    group by all 
)

select * except(actual_monthly_expense, actual_annual_expense),
    actual_monthly_expense + actual_annual_expense + (actual_household_income * 0.10) as actual_expense -- this includes adding tithing and annual expense (made monthly) into actual planned expense 
from joined_budgets
where period is not null 
