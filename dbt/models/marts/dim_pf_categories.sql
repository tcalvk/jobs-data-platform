select 
    category_id,
    name as category_name,
    description,
    active,
    category_type,
    vh_balance
from {{ ref('stg_personal_finance__categories') }}