WITH source AS (
    SELECT 
        Date AS date,
        CAST(NULLIF(REGEXP_REPLACE(`_Balance_`, r'[^0-9.\-]', ''), '-') AS NUMERIC) AS balance,
        CAST(NULLIF(REGEXP_REPLACE(`_BalanceAvailable_`, r'[^0-9.\-]', ''), '-') AS NUMERIC) AS balance_available,
        CAST(NULLIF(REGEXP_REPLACE(`_BalanceLimit_`, r'[^0-9.\-]', ''), '-') AS NUMERIC) AS balance_limit,
        UsePct AS usage_pct,
        Currency AS currency,
        AccountName AS account_name,
        AccountId AS account_id,
        AccountType AS account_type

    FROM {{ source('personal_finance', 'bsa_balances') }}
)

SELECT * FROM source