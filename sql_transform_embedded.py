#!/usr/bin/env python3
"""
Generic SQL transformation script that reads SQL from environment.
"""

import os
import sys
import json
from pyspark.sql import SparkSession

def main():
    print("🚀 Starting SQL transformation...")
    
    # Get configuration from environment variables
    sql_query = os.getenv("SQL_QUERY")
    source_paths_json = os.getenv("SOURCE_PATHS")
    destination_path = os.getenv("DESTINATION_PATH")
    write_mode = os.getenv("WRITE_MODE", "overwrite")
    
    # Validate required environment variables
    if not sql_query:
        print("❌ ERROR: SQL_QUERY environment variable is required")
        sys.exit(1)
    
    if not source_paths_json:
        print("❌ ERROR: SOURCE_PATHS environment variable is required")
        print("    This should be set by the transformation API")
        sys.exit(1)
    
    if not destination_path:
        print("❌ ERROR: DESTINATION_PATH environment variable is required") 
        print("    This should be set by the transformation API")
        sys.exit(1)
    
    print(f"SQL Query: {sql_query}")
    print(f"Source paths: {source_paths_json}")
    print(f"Destination: {destination_path}")
    print(f"Write mode: {write_mode}")
    
    # Parse source paths
    try:
        source_paths = json.loads(source_paths_json)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing source paths: {e}")
        sys.exit(1)
    
    # Initialize Spark session with S3 configuration
    print("🔧 Initializing Spark session...")
    spark = SparkSession.builder \
        .appName("SQL Data Transformation") \
        .getOrCreate()
    
    print("✅ Spark session created")
    
    try:
        # Read data from S3 sources
        print("📂 Reading source data...")
        
        # Create a unified DataFrame from all sources
        combined_df = None
        for i, source_path in enumerate(source_paths):
            print(f"   Reading from: {source_path}")
            try:
                df = spark.read.parquet(source_path)
                if combined_df is None:
                    combined_df = df
                else:
                    combined_df = combined_df.union(df)
                print(f"   ✅ Successfully read source {i+1}")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not read from {source_path}: {e}")
                continue
        
        if combined_df is None:
            print("❌ No data could be read from any source")
            sys.exit(1)
        
        # Register as temporary view
        combined_df.createOrReplaceTempView("source_data")
        print(f"✅ Created temporary view 'source_data' with {combined_df.count()} rows")
        
        # Execute SQL transformation
        print("🔄 Executing SQL transformation...")
        result_df = spark.sql(sql_query)
        
        print(f"✅ SQL executed successfully, result has {result_df.count()} rows")
        
        # Write results to destination
        print(f"💾 Writing results to: {destination_path}")
        result_df.write \
            .mode(write_mode) \
            .parquet(destination_path)
        
        print("✅ Data transformation completed successfully!")
        
        # Show sample of results
        print("📊 Sample of transformed data:")
        result_df.show(10, truncate=False)
        
    except Exception as e:
        print(f"❌ Error during transformation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
