with join_budgets as (
    select 
        date_trunc(t.date, month) as transaction_month,
        t.category_id,
        t.category,
        t.transaction_type,
        t.amount as amount,
        b.amount as budget_amount,
    from {{ ref('fact_pf_transactions') }} t 
    left join {{ ref('dim_pf_budgets') }} b 
        on t.category_id = b.category_id
        and t.date >= b.start_date
        and t.date <= b.end_date
    where 1=1 
    and t.transaction_type = 'Annual Expense' 
),

agg as (
    select 
        transaction_month,
        date_trunc(transaction_month, year) as year,
        category_id,
        category,
        transaction_type,
        sum(amount) as total_amount,
        max(budget_amount) as budget_amount
    from join_budgets
    group by 1,2,3,4,5
)

select * from agg
