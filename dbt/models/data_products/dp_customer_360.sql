{{
  config(
    materialized='table',
    description='Curated customer data product with enriched customer insights'
  )
}}

WITH customer_transactions AS (
    SELECT 
        c.customer_id,
        c.email,
        c.created_at,
        COUNT(t.transaction_id) as total_transactions,
        SUM(t.amount) as total_spent,
        AVG(t.amount) as avg_transaction_value,
        MAX(t.transaction_date) as last_transaction_date,
        MIN(t.transaction_date) as first_transaction_date
    FROM {{ ref('stg_customers') }} c
    LEFT JOIN {{ ref('stg_transactions') }} t 
        ON c.customer_id = t.customer_id
    GROUP BY c.customer_id, c.email, c.created_at
),

customer_segments AS (
    SELECT 
        *,
        CASE 
            WHEN total_spent >= 1000 THEN 'HIGH_VALUE'
            WHEN total_spent >= 500 THEN 'MEDIUM_VALUE' 
            WHEN total_spent > 0 THEN 'LOW_VALUE'
            ELSE 'NO_PURCHASES'
        END as customer_segment,
        
        CASE
            WHEN last_transaction_date >= CURRENT_DATE - INTERVAL '30' DAY THEN 'ACTIVE'
            WHEN last_transaction_date >= CURRENT_DATE - INTERVAL '90' DAY THEN 'AT_RISK'
            WHEN last_transaction_date IS NOT NULL THEN 'CHURNED'
            ELSE 'NEVER_PURCHASED'
        END as customer_status
        
    FROM customer_transactions
)

SELECT 
    customer_id,
    email,
    created_at,
    total_transactions,
    total_spent,
    avg_transaction_value,
    last_transaction_date,
    first_transaction_date,
    customer_segment,
    customer_status,
    CURRENT_TIMESTAMP as data_product_updated_at,
    '{{ var("data_product_owner") }}' as data_product_owner,
    'CUSTOMER_360' as data_product_type
FROM customer_segments