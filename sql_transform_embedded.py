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
    
    # Initialize Spark session first to access configuration
    print("🔧 Initializing Spark session...")
    spark = SparkSession.builder \
        .appName("SQL Data Transformation") \
        .getOrCreate()
    
    print("✅ Spark session created")
    
    # Get configuration from Spark conf (new method) or environment variables (fallback)
    sql_query = spark.conf.get("spark.sql.transform.query", None) or os.getenv("SQL_QUERY")
    sources_json = spark.conf.get("spark.sql.transform.sources", None) or os.getenv("SOURCE_PATHS")
    destination_path = spark.conf.get("spark.sql.transform.destination", None) or os.getenv("DESTINATION_PATH")
    write_mode = spark.conf.get("spark.sql.transform.writeMode", None) or os.getenv("WRITE_MODE", "overwrite")
    
    # Validate required parameters
    if not sql_query:
        print("❌ ERROR: SQL query is required")
        print("    Set via spark.sql.transform.query or SQL_QUERY environment variable")
        sys.exit(1)
    
    if not sources_json:
        print("❌ ERROR: Source paths are required")
        print("    Set via spark.sql.transform.sources or SOURCE_PATHS environment variable")
        sys.exit(1)
    
    if not destination_path:
        print("❌ ERROR: Destination path is required") 
        print("    Set via spark.sql.transform.destination or DESTINATION_PATH environment variable")
        sys.exit(1)
    
    print(f"SQL Query: {sql_query}")
    print(f"Source paths: {sources_json}")
    print(f"Destination: {destination_path}")
    print(f"Write mode: {write_mode}")
    
    # Parse source paths
    try:
        source_paths = json.loads(sources_json)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing source paths: {e}")
        sys.exit(1)
    
    # Initialize Spark session with S3 configuration
    print("🔧 Spark session already initialized")
    
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
