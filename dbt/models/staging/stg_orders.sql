{{
  config(
    materialized='view',
    description='Standardized order data from silver layer'
  )
}}

SELECT 
    order_id,
    customer_id,
    order_date,
    amount,
    TRIM(UPPER(status)) as order_status,
    created_at,
    updated_at,
    CURRENT_TIMESTAMP as _loaded_at
FROM {{ source('silver_layer', 'orders') }}
WHERE order_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND amount >= 0
  AND order_date IS NOT NULL