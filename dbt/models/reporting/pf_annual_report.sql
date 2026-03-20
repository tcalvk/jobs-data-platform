with budgets as (
    select
        b.category_id,
        b.amount as budget_amount,
        b.start_date,
        b.end_date,
        c.category_name,
        c.category_type,
    from {{ ref('dim_pf_budgets') }} b
    left join {{ ref('dim_pf_categories') }} c
        on b.category_id = c.category_id
    where c.category_type = 'Annual Expense'
),

join_transactions as (
    select
        b.category_id,
        b.category_name,
        b.budget_amount,
        b.end_date,
        t.transaction_type,
        t.amount
    from budgets b
    left join {{ ref('fact_pf_transactions') }} t
        on t.category_id = b.category_id
        and t.date >= b.start_date
        and t.date <= b.end_date
        -- only include transactions up to the end of the previous month (closed months)
        and t.date <= date_sub(date_trunc(cast(current_timestamp() as date), month), interval 1 day)
),

agg as (
    select
        left(cast(end_date as string), 4) as year,
        category_id,
        category_name,
        budget_amount,
        transaction_type,
        ifnull(sum(amount), 0) as total_amount,
        round(budget_amount - ifnull(sum(amount), 0),2) as budget_remaining
    from join_transactions
    group by 1, 2, 3, 4, 5
)

select * from agg
