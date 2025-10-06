{{
  config(
    materialized='view',
    description='Standardized customer data from silver layer'
  )
}}

SELECT 
    customer_id,
    TRIM(name) as customer_name,
    TRIM(LOWER(email)) as email,
    registration_date,
    created_at,
    updated_at,
    CURRENT_TIMESTAMP as _loaded_at
FROM {{ source('silver_layer', 'customers') }}
WHERE customer_id IS NOT NULL
  AND email IS NOT NULL
  AND email LIKE '%@%'
  AND name IS NOT NULL