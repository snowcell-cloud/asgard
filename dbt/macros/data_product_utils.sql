{#
  Macro to generate data product metadata for lineage and governance
#}
{% macro generate_data_product_metadata(model_name, data_product_type, owner, update_frequency) %}
  SELECT 
    '{{ model_name }}' as data_product_name,
    '{{ data_product_type }}' as data_product_type,
    '{{ owner }}' as owner,
    '{{ update_frequency }}' as update_frequency,
    CURRENT_TIMESTAMP as metadata_created_at
{% endmacro %}

{#
  Macro to add data quality checks to data products
#}
{% macro add_data_quality_checks(table_name) %}
  WITH quality_checks AS (
    SELECT 
      COUNT(*) as total_rows,
      COUNT(*) - COUNT({{ get_primary_key(table_name) }}) as null_primary_keys,
      CURRENT_TIMESTAMP as quality_check_timestamp
    FROM {{ ref(table_name) }}
  )
  SELECT * FROM quality_checks
  WHERE null_primary_keys = 0  -- Ensure no null primary keys
{% endmacro %}

{#
  Helper macro to get primary key column name (simplified)
#}
{% macro get_primary_key(table_name) %}
  {% if 'customer' in table_name %}
    customer_id
  {% elif 'product' in table_name %}
    product_id
  {% elif 'revenue' in table_name %}
    transaction_month
  {% else %}
    id
  {% endif %}
{% endmacro %}