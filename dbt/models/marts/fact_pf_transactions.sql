{% set sources = [
  ref('stg_personal_finance__plaid_transactions'),
  ref('stg_personal_finance__manual_transactions')
] %}

{% set columns = [
    'date',
    'transaction_id',
    'account',
    'category_id',
    'category',
    'amount',
    'transaction_type',
    'status',
    'source'
] %}

with unioned as (
  {% for src in sources %}
    
    select
      {% for col in columns %}
        {{ col }}{% if not loop.last %},{% endif %}
      {% endfor %}
    from {{ src }}
    
    {% if not loop.last %}union all{% endif %}
  
  {% endfor %}
),

filtered as (
    select 
        date,
        transaction_id,
        account,
        category_id,
        category,
        amount,
        if(transaction_type = '#N/A', null, transaction_type) as transaction_type,
        source
    from unioned 
    where 1=1
    and (
        status is null or 
        status != 'Pending'
    )
    and category_id != 0
    and category_id is not null 
)

select * 
from filtered 
-- deduplicate in case of duplicate loads
qualify row_number() over(
  partition by transaction_id, source
  order by category_id
) = 1
