with source as (
    
    select 
        Id as category_id,
        Name as name,
        Description as description,
        Active as active,
        Category_Type as category_type,
        VH_Bal as vh_balance,
        VH_Spent as vh_spent,
        VH_Goal_Bal as vh_goal_bal
    from {{ source('personal_finance', 'categories') }}

)

select * from source 