{{
  config(
    materialized='table',
    description='Monthly revenue data product with trends and forecasting support'
  )
}}

WITH monthly_revenue AS (
    SELECT 
        transaction_month,
        transaction_year,
        COUNT(transaction_id) as total_transactions,
        SUM(amount) as total_revenue,
        AVG(amount) as avg_transaction_value,
        COUNT(DISTINCT customer_id) as unique_customers,
        MAX(transaction_date) as last_transaction_in_month,
        MIN(transaction_date) as first_transaction_in_month
    FROM {{ ref('stg_transactions') }}
    GROUP BY transaction_month, transaction_year
),

revenue_trends AS (
    SELECT 
        *,
        LAG(total_revenue) OVER (ORDER BY transaction_year, transaction_month) as prev_month_revenue,
        total_revenue - LAG(total_revenue) OVER (ORDER BY transaction_year, transaction_month) as revenue_change,
        (total_revenue - LAG(total_revenue) OVER (ORDER BY transaction_year, transaction_month)) / 
            NULLIF(LAG(total_revenue) OVER (ORDER BY transaction_year, transaction_month), 0) * 100 as revenue_growth_pct
    FROM monthly_revenue
)

SELECT 
    transaction_month,
    transaction_year,
    total_transactions,
    total_revenue,
    avg_transaction_value,
    unique_customers,
    last_transaction_in_month,
    first_transaction_in_month,
    prev_month_revenue,
    revenue_change,
    revenue_growth_pct,
    CASE 
        WHEN revenue_growth_pct > 10 THEN 'HIGH_GROWTH'
        WHEN revenue_growth_pct > 0 THEN 'GROWTH'
        WHEN revenue_growth_pct > -10 THEN 'STABLE'
        ELSE 'DECLINING'
    END as growth_trend,
    CURRENT_TIMESTAMP as data_product_updated_at,
    '{{ var("data_product_owner") }}' as data_product_owner,
    'REVENUE_ANALYTICS' as data_product_type
FROM revenue_trends
ORDER BY transaction_year DESC, transaction_month DESC