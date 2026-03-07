select 
    category_id,
    amount,
    start_date,
    if(end_date is null, cast(current_timestamp() as date), end_date) as end_date
from {{ ref('stg_personal_finance__budgets') }}
qualify row_number() over(
    partition by 
        category_id,
        start_date,
        end_date
    order by amount desc
) = 1 
