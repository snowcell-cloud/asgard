{{
  config(
    materialized='view',
    description='Standardized transaction data from silver layer'
  )
}}

SELECT 
    transaction_id,
    customer_id,
    amount,
    transaction_date,
    DATE_TRUNC('month', CAST(transaction_date AS DATE)) as transaction_month,
    DATE_TRUNC('year', CAST(transaction_date AS DATE)) as transaction_year,
    CURRENT_TIMESTAMP as last_updated
FROM {{ source('silver_layer', 'transaction_data') }}
WHERE transaction_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND amount > 0