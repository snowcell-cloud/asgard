{{
  config(
    materialized='view',
    description='Standardized product data from silver layer'
  )
}}

SELECT 
    product_id,
    TRIM(product_name) as product_name,
    TRIM(UPPER(category)) as category,
    price,
    CURRENT_TIMESTAMP as last_updated
FROM {{ source('silver_layer', 'product_data') }}
WHERE product_id IS NOT NULL
  AND product_name IS NOT NULL
  AND price >= 0