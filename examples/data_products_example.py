"""
Example usage script for the Data Products API.
"""

import asyncio
import httpx
from typing import Dict, Any


class DataProductExample:
    """Example usage of the Data Products API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def create_sample_data_products(self):
        """Create sample data products."""

        # Customer 360 Data Product
        customer_360_request = {
            "name": "Customer 360 Analytics",
            "description": "Comprehensive customer view with transaction history and segmentation",
            "data_product_type": "CUSTOMER_360",
            "source_query": """
                SELECT 
                    c.customer_id,
                    c.email,
                    c.created_at,
                    COUNT(t.transaction_id) as total_transactions,
                    SUM(t.amount) as total_spent,
                    AVG(t.amount) as avg_transaction_value
                FROM nessie.silver.customer_data c
                LEFT JOIN nessie.silver.transaction_data t ON c.customer_id = t.customer_id
                GROUP BY c.customer_id, c.email, c.created_at
            """,
            "owner": "data-platform-team",
            "consumers": ["marketing_team", "customer_success", "analytics_team"],
            "update_frequency": "daily",
            "tags": ["customer", "analytics", "pii"],
        }

        # Product Performance Data Product
        product_performance_request = {
            "name": "Product Performance Dashboard",
            "description": "Product sales metrics and performance analytics",
            "data_product_type": "PRODUCT_PERFORMANCE",
            "source_query": """
                SELECT 
                    p.product_id,
                    p.product_name,
                    p.category,
                    p.price,
                    COUNT(DISTINCT t.customer_id) as unique_customers,
                    SUM(t.amount) as total_revenue
                FROM nessie.silver.product_data p
                LEFT JOIN nessie.silver.transaction_data t ON p.product_id = CAST(t.transaction_id AS VARCHAR)
                GROUP BY p.product_id, p.product_name, p.category, p.price
            """,
            "owner": "product-team",
            "consumers": ["sales_team", "product_team", "executive_team"],
            "update_frequency": "daily",
            "tags": ["product", "sales", "analytics"],
        }

        # Create the data products
        async with httpx.AsyncClient() as client:
            # Create Customer 360
            response = await client.post(
                f"{self.base_url}/api/v1/data-products/", json=customer_360_request
            )
            if response.status_code == 200:
                customer_360_dp = response.json()
                print(f"✅ Created Customer 360 Data Product: {customer_360_dp['id']}")
            else:
                print(f"❌ Failed to create Customer 360: {response.text}")

            # Create Product Performance
            response = await client.post(
                f"{self.base_url}/api/v1/data-products/", json=product_performance_request
            )
            if response.status_code == 200:
                product_perf_dp = response.json()
                print(f"✅ Created Product Performance Data Product: {product_perf_dp['id']}")
            else:
                print(f"❌ Failed to create Product Performance: {response.text}")

    async def demonstrate_api_usage(self):
        """Demonstrate various API endpoints."""
        async with httpx.AsyncClient() as client:

            # List all data products
            print("\n📋 Listing all data products...")
            response = await client.get(f"{self.base_url}/api/v1/data-products/")
            if response.status_code == 200:
                data_products = response.json()
                print(f"Found {data_products['total_count']} data products")
                for dp in data_products["data_products"]:
                    print(f"  - {dp['name']} ({dp['data_product_type']}) - Status: {dp['status']}")

            if not data_products["data_products"]:
                print("No data products found. Creating samples first...")
                await self.create_sample_data_products()
                return

            # Get first data product details
            first_dp_id = data_products["data_products"][0]["id"]
            print(f"\n🔍 Getting details for data product: {first_dp_id}")

            response = await client.get(f"{self.base_url}/api/v1/data-products/{first_dp_id}")
            if response.status_code == 200:
                dp_details = response.json()
                print(f"  Name: {dp_details['name']}")
                print(f"  Type: {dp_details['data_product_type']}")
                print(f"  Owner: {dp_details['owner']}")
                print(f"  Consumers: {', '.join(dp_details['consumers'])}")

            # Run the data product
            print(f"\n🔄 Running data product: {first_dp_id}")
            response = await client.post(f"{self.base_url}/api/v1/data-products/{first_dp_id}/run")
            if response.status_code == 200:
                run_result = response.json()
                print(f"  Run Status: {run_result['status']}")
                print(f"  Message: {run_result['message']}")
            else:
                print(f"  Run failed: {response.text}")

            # Query the data product
            print(f"\n📊 Querying data from: {first_dp_id}")
            response = await client.get(
                f"{self.base_url}/api/v1/data-products/{first_dp_id}/query", params={"limit": 5}
            )
            if response.status_code == 200:
                query_result = response.json()
                print(f"  Returned {query_result['returned_rows']} rows")
                print(f"  Columns: {', '.join(query_result['columns'])}")
                if query_result["data"]:
                    print("  Sample data:")
                    for i, row in enumerate(query_result["data"][:2]):
                        print(f"    Row {i+1}: {dict(zip(query_result['columns'], row))}")
            else:
                print(f"  Query failed: {response.text}")

            # Get schema
            print(f"\n📋 Getting schema for: {first_dp_id}")
            response = await client.get(
                f"{self.base_url}/api/v1/data-products/{first_dp_id}/schema"
            )
            if response.status_code == 200:
                schema_result = response.json()
                print(f"  Table: {schema_result['table_name']}")
                if schema_result["schema"]:
                    print("  Columns:")
                    for col in schema_result["schema"][:5]:  # Show first 5 columns
                        print(f"    - {col['column_name']}: {col['data_type']}")
            else:
                print(f"  Schema fetch failed: {response.text}")


async def main():
    """Main example function."""
    example = DataProductExample()

    print("🚀 Asgard Data Products API Examples")
    print("=====================================")

    # Create sample data products
    await example.create_sample_data_products()

    # Demonstrate API usage
    await example.demonstrate_api_usage()

    print("\n✅ Example completed!")


if __name__ == "__main__":
    asyncio.run(main())
