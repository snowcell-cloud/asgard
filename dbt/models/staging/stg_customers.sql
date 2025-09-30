{{
  config(
    materialized='view',
    description='Standardized customer data from silver layer'
  )
}}

SELECT 
    customer_id,
    TRIM(LOWER(email)) as email,
    created_at,
    CURRENT_TIMESTAMP as last_updated
FROM {{ source('silver_layer', 'customer_data') }}
WHERE customer_id IS NOT NULL
  AND email IS NOT NULL
  AND email LIKE '%@%'