{{
  config(
    materialized='table',
    description='Product performance data product with sales metrics and insights'
  )
}}

WITH product_sales AS (
    SELECT 
        p.product_id,
        p.product_name,
        p.category,
        p.price,
        COUNT(t.transaction_id) as total_sales,
        SUM(t.amount) as total_revenue,
        COUNT(DISTINCT t.customer_id) as unique_customers,
        AVG(t.amount) as avg_sale_amount,
        MAX(t.transaction_date) as last_sale_date,
        MIN(t.transaction_date) as first_sale_date
    FROM {{ ref('stg_products') }} p
    LEFT JOIN {{ ref('stg_transactions') }} t 
        ON p.product_id = CAST(t.transaction_id AS VARCHAR) -- Adjust join logic as needed
    GROUP BY p.product_id, p.product_name, p.category, p.price
),

product_performance AS (
    SELECT 
        *,
        CASE 
            WHEN total_revenue >= 10000 THEN 'TOP_PERFORMER'
            WHEN total_revenue >= 5000 THEN 'GOOD_PERFORMER'
            WHEN total_revenue > 0 THEN 'LOW_PERFORMER'
            ELSE 'NO_SALES'
        END as performance_tier,
        
        total_revenue / NULLIF(total_sales, 0) as revenue_per_sale,
        unique_customers / NULLIF(total_sales, 0) as customer_diversity_ratio
        
    FROM product_sales
)

SELECT 
    product_id,
    product_name,
    category,
    price,
    total_sales,
    total_revenue,
    unique_customers,
    avg_sale_amount,
    last_sale_date,
    first_sale_date,
    performance_tier,
    revenue_per_sale,
    customer_diversity_ratio,
    CURRENT_TIMESTAMP as data_product_updated_at,
    '{{ var("data_product_owner") }}' as data_product_owner,
    'PRODUCT_PERFORMANCE' as data_product_type
FROM product_performance