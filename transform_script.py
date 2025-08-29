#!/usr/bin/env python3
"""
SQL transformation script for Spark on Kubernetes.
Reads from S3 parquet files and applies SQL transformations.
"""

import os
import sys
import json
from pyspark.sql import SparkSession

def main():
    print("🚀 Starting SQL transformation...")
    
    # Get configuration from environment variables
    sql_query = os.getenv("SQL_QUERY", "SELECT *, CURRENT_TIMESTAMP() as processing_time FROM source_data")
    source_paths_json = os.getenv("SOURCE_PATHS", '["s3a://airbytedestination1/bronze/*"]')
    destination_path = os.getenv("DESTINATION_PATH", "s3a://airbytedestination1/silver/default/")
    write_mode = os.getenv("WRITE_MODE", "overwrite")
    
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
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("AWS_ACCESS_KEY_ID")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("AWS_SECRET_ACCESS_KEY")) \
        .config("spark.hadoop.fs.s3a.endpoint", "s3.amazonaws.com") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.fast.upload", "true") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()
    
    print("✅ Spark session initialized successfully")
    
    try:
        # Read data from all source paths
        print(f"📖 Reading data from {len(source_paths)} source(s)...")
        dfs = []
        
        for source_path in source_paths:
            print(f"Reading from: {source_path}")
            try:
                df = spark.read.parquet(source_path)
                row_count = df.count()
                print(f"✅ Successfully read {row_count} rows from {source_path}")
                if row_count > 0:
                    dfs.append(df)
                else:
                    print(f"⚠️  Warning: No data found in {source_path}")
            except Exception as e:
                print(f"❌ Error reading from {source_path}: {e}")
        
        if not dfs:
            print("❌ No data found in any source paths")
            print("📝 Creating sample test data for demonstration...")
            
            # Create sample test data using Spark
            from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
            from pyspark.sql.functions import current_timestamp
            
            # Define schema for test orders data
            schema = StructType([
                StructField("order_id", StringType(), True),
                StructField("customer_id", StringType(), True),
                StructField("product_name", StringType(), True),
                StructField("quantity", IntegerType(), True),
                StructField("unit_price", DoubleType(), True),
                StructField("total_amount", DoubleType(), True),
                StructField("order_date", StringType(), True),
                StructField("status", StringType(), True),
                StructField("region", StringType(), True)
            ])
            
            # Create test data
            test_data = []
            for i in range(1, 101):  # Create 100 test orders
                test_data.append((
                    f"ORD-{i:06d}",
                    f"CUST-{(i % 20):04d}",
                    f"Product-{(i % 10):02d}",
                    (i % 5) + 1,
                    round(10.0 + (i % 100), 2),
                    ((i % 5) + 1) * round(10.0 + (i % 100), 2),
                    f"2025-08-{(i % 28) + 1:02d}",
                    "completed" if i % 4 != 0 else "pending",
                    "north" if i % 3 == 0 else "south" if i % 3 == 1 else "central"
                ))
            
            combined_df = spark.createDataFrame(test_data, schema)
            print(f"📊 Created test dataset with {combined_df.count()} rows")
        else:
            # Union all dataframes
            print("🔄 Combining data from all sources...")
            if len(dfs) == 1:
                combined_df = dfs[0]
            else:
                combined_df = dfs[0]
                for df in dfs[1:]:
                    combined_df = combined_df.union(df)
        
        total_rows = combined_df.count()
        print(f"📊 Combined dataset has {total_rows} total rows")
        
        # Show schema and sample data
        print("📋 Schema:")
        combined_df.printSchema()
        
        print("📄 Sample data (first 5 rows):")
        combined_df.show(5, truncate=False)
        
        # Create temporary view for SQL
        combined_df.createOrReplaceTempView("source_data")
        print("🔍 Created temporary view 'source_data'")
        
        # Execute SQL transformation
        print(f"⚡ Executing SQL transformation: {sql_query}")
        result_df = spark.sql(sql_query)
        
        result_count = result_df.count()
        print(f"✅ SQL transformation completed. Result has {result_count} rows")
        
        print("📄 Transformation result sample (first 5 rows):")
        result_df.show(5, truncate=False)
        
        # Write results to destination
        print(f"💾 Writing {result_count} rows to: {destination_path}")
        result_df.coalesce(1) \
            .write \
            .mode(write_mode) \
            .parquet(destination_path)
        
        print("🎉 ✅ Transformation completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during transformation: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        print("🛑 Stopping Spark session...")
        spark.stop()

if __name__ == "__main__":
    main()
