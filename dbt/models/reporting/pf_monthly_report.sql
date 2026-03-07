with join_budgets as (
    select 
        date_trunc(t.date, month) as month,
        t.category_id,
        t.category,
        t.transaction_type,
        t.amount as amount,
        b.amount as budget_amount
    from {{ ref('fact_pf_transactions') }} t 
    left join {{ ref('dim_pf_budgets') }} b 
        on t.category_id = b.category_id
        and t.date >= b.start_date
        and t.date <= b.end_date
    where 1=1 
    and (
        t.transaction_type = 'Monthly Expense' or 
        lower(t.transaction_type) like '%vh%' or 
        t.transaction_type = 'Monthly Income'
    )    
),

agg as (
    select 
        month,
        category_id,
        category,
        transaction_type,
        sum(amount) as total_amount,
        max(budget_amount) as budget_amount
    from join_budgets
    group by 1,2,3,4
)

select * from agg

