#!/usr/bin/env python3
"""
Example usage of the new Airbyte ingestion API with schedule and status parameters.

This example demonstrates how to use the enhanced /ingestion endpoint with optional
schedule and status parameters, and how to check the status using the new status endpoint.
"""

import requests
import json
from datetime import datetime

# Base URL for the API (adjust as needed)
BASE_URL = "http://localhost:8000"

def create_ingestion_with_schedule():
    """Example: Create an ingestion connection with a cron schedule."""
    
    payload = {
        "name": "postgres-to-s3-daily",
        "sourceId": "12345678-1234-1234-1234-123456789012",
        "destinationId": "87654321-4321-4321-4321-210987654321",
        "schedule": {
            "scheduleType": "cron",
            "cronExpression": "0 2 * * *"  # Daily at 2 AM
        },
        "status": "active"
    }
    
    print("📤 Creating ingestion with schedule:")
    print(json.dumps(payload, indent=2))
    
    # In a real scenario, you would make this request:
    # response = requests.post(f"{BASE_URL}/ingestion", json=payload)
    # return response.json()
    
    # For this example, we'll simulate the expected response
    mock_response = {
        "connectionId": "conn-12345678-1234-1234-1234-123456789012",
        "sourceId": payload["sourceId"],
        "destinationId": payload["destinationId"],
        "name": payload["name"],
        "status": payload["status"],
        "schedule": payload["schedule"],
        "created": datetime.utcnow().isoformat()
    }
    
    print("\n📥 Expected response:")
    print(json.dumps(mock_response, indent=2, default=str))
    return mock_response

def create_simple_ingestion():
    """Example: Create a simple ingestion connection with minimal parameters."""
    
    payload = {
        "name": "mysql-to-s3-manual",
        "sourceId": "source-98765432-1234-1234-1234-123456789012",
        "destinationId": "dest-11111111-2222-3333-4444-555555555555"
        # No schedule or status - will use defaults
    }
    
    print("📤 Creating simple ingestion (minimal parameters):")
    print(json.dumps(payload, indent=2))
    
    # Simulate response with defaults
    mock_response = {
        "connectionId": "conn-simple-1234-1234-1234-123456789012",
        "sourceId": payload["sourceId"],
        "destinationId": payload["destinationId"],
        "name": payload["name"],
        "status": "active",  # Default status
        "schedule": None,    # No schedule provided
        "created": datetime.utcnow().isoformat()
    }
    
    print("\n📥 Expected response (with defaults):")
    print(json.dumps(mock_response, indent=2, default=str))
    return mock_response

def check_ingestion_status(connection_id):
    """Example: Check the status of an ingestion connection."""
    
    print(f"🔍 Checking status for connection: {connection_id}")
    
    # In a real scenario:
    # response = requests.get(f"{BASE_URL}/ingestion/{connection_id}/status")
    # return response.json()
    
    # Simulate status response
    mock_status_response = {
        "connectionId": connection_id,
        "status": "active",
        "lastSync": "2024-01-15T10:30:00Z",
        "nextSync": "2024-01-16T02:00:00Z",
        "schedule": {
            "scheduleType": "cron",
            "cronExpression": "0 2 * * *"
        }
    }
    
    print("📊 Status response:")
    print(json.dumps(mock_status_response, indent=2))
    return mock_status_response

def main():
    """Demonstrate the new ingestion API features."""
    
    print("🚀 Airbyte Ingestion API Examples")
    print("=" * 50)
    
    print("\n1️⃣ Creating ingestion with schedule and status:")
    print("-" * 45)
    scheduled_connection = create_ingestion_with_schedule()
    
    print("\n2️⃣ Creating simple ingestion (minimal parameters):")
    print("-" * 50)
    simple_connection = create_simple_ingestion()
    
    print("\n3️⃣ Checking connection status:")
    print("-" * 35)
    check_ingestion_status(scheduled_connection["connectionId"])
    
    print("\n✨ Summary of New Features:")
    print("-" * 30)
    print("• Optional 'schedule' parameter with 'scheduleType' and 'cronExpression'")
    print("• Optional 'status' parameter (defaults to 'active')")
    print("• New GET /ingestion/{connectionId}/status endpoint")
    print("• Backward compatible - existing code will continue to work")
    
    print("\n🔧 Available Schedule Types:")
    print("• 'cron' - Use cronExpression for custom scheduling")
    print("• 'manual' - Manual trigger only")
    print("• 'basic' - Simple interval-based scheduling")
    
    print("\n📋 Status Values:")
    print("• 'active' - Connection is enabled and will sync")
    print("• 'inactive' - Connection is disabled")

if __name__ == "__main__":
    main()
