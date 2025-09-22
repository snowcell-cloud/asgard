#!/usr/bin/env python3
"""
Generic SQL transformation script that reads SQL from environment.
Minimal, non-invasive Iceberg support appended (enabled by default).
Only the Iceberg feature is added — transformation logic is unchanged.
"""

import os
import sys
import json
import re
import traceback
from pyspark.sql import SparkSession

# -----------------------------
# ICEBERG FEATURE CONFIG (hardcoded here)
# Edit these values if you need different behaviour.
# -----------------------------
ICEBERG_ENABLED = True
ICEBERG_CATALOG_NAME = "iceberg"                      # Spark catalog name to register for Iceberg
ICEBERG_WAREHOUSE = "s3://airbytedestination1/iceberg/"         # Iceberg warehouse path (where metadata + table data live)
# If you want a specific target table, set in format: catalog.namespace.table
# If None, the script will derive catalog.namespace.table from the DESTINATION_PATH (last two path components)
ICEBERG_TARGET_TABLE_OVERRIDE = None
# Options: "create_or_replace" (default), "append", "overwrite"
ICEBERG_WRITE_MODE = "append"
# -----------------------------

def getenv_conf_or_env(spark, conf_key, env_key, default=None):
    """Try Spark conf first, then environment variable, then default (kept from earlier variant)."""
    try:
        v = spark.conf.get(conf_key, None)
    except Exception:
        v = None
    if v is None or v == "null":
        v = os.getenv(env_key, None)
    return v if v is not None else default

def sanitize_identifier(name: str) -> str:
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r'[^a-z0-9_]', '_', n)
    n = re.sub(r'_+', '_', n)
    n = n.strip('_')
    if not n:
        n = "x"
    if re.match(r'^\d', n):
        n = "t" + n
    return n

def derive_table_from_s3_path(path: str, catalog_name: str = "iceberg_catalog", default_namespace: str = "raw", default_table: str = "table"):
    """
    Derive catalog.namespace.table from S3 path.
    Example:
      s3://bucket/bronze/orders/ -> iceberg_catalog.bronze.orders
    """
    if not path:
        return f"{catalog_name}.{default_namespace}.{default_table}"
    p = re.sub(r'^s3://', '', path)
    p = p.rstrip('/')
    parts = p.split('/')
    # ignore bucket name
    if len(parts) >= 3:
        namespace = parts[-2]
        table = parts[-1]
    elif len(parts) == 2:
        namespace = parts[0]
        table = parts[1]
    else:
        namespace = default_namespace
        table = default_table
    namespace = sanitize_identifier(namespace)
    table = sanitize_identifier(table)
    return f"{catalog_name}.{namespace}.{table}"

def ensure_namespace(spark, catalog: str, namespace: str):
    """
    Try to create namespace if it doesn't exist. Ignore failures gracefully.
    """
    try:
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {catalog}.{namespace}")
    except Exception as e:
        print(f"Warning: could not CREATE NAMESPACE {catalog}.{namespace}: {e}")

def main():
    print("🚀 Starting SQL transformation...")

    # Initialize Spark session first to access configuration
    print("🔧 Initializing Spark session...")
    spark = SparkSession.builder \
        .appName("SQL Data Transformation") \
        .getOrCreate()

    print("✅ Spark session created")

    # Get configuration from Spark conf (preferred) or environment variables (fallback)
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
    print(f"ICEBERG_ENABLED (hardcoded): {ICEBERG_ENABLED}")

    # Parse source paths
    try:
        source_paths = json.loads(sources_json)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing source paths: {e}")
        sys.exit(1)

    # Spark session already initialized, any S3/Iceberg configs should be supplied via spark-submit --conf or cluster configuration.
    # However, to ensure Iceberg catalog is available during the write step we will set minimal spark.conf entries here
    # (these are non-invasive and only applied when ICEBERG_ENABLED is True).
    if ICEBERG_ENABLED:
        # configure iceberg catalog (Hadoop catalog) in the running Spark session
        try:
            spark.conf.set(f"spark.sql.catalog.{ICEBERG_CATALOG_NAME}", "org.apache.iceberg.spark.SparkCatalog")
            spark.conf.set(f"spark.sql.catalog.{ICEBERG_CATALOG_NAME}.type", "hadoop")
            spark.conf.set(f"spark.sql.catalog.{ICEBERG_CATALOG_NAME}.warehouse", ICEBERG_WAREHOUSE)
            # note: if your spark cluster already had differing catalog config, this may override it in this session only
            print(f"Configured Iceberg catalog '{ICEBERG_CATALOG_NAME}' with warehouse '{ICEBERG_WAREHOUSE}' in Spark session")
        except Exception as e:
            print(f"Warning: failed to set Iceberg catalog config in Spark session: {e}")

    try:
        # Read data from S3 sources
        print("📂 Reading source data...")

        # Create a unified DataFrame from all sources (keeping original union semantics)
        combined_df = None
        for i, source_path in enumerate(source_paths):
            print(f"   Reading from: {source_path}")
            try:
                df = spark.read.parquet(source_path)
                if combined_df is None:
                    combined_df = df
                else:
                    # original code used union (not unionByName) — keeping same behaviour
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

        # Write results to destination (original behavior preserved)
        print(f"💾 Writing results to: {destination_path}")
        result_df.write \
            .mode(write_mode) \
            .parquet(destination_path)

        print("✅ Data transformation completed successfully!")

        # Show sample of results
        print("📊 Sample of transformed data:")
        result_df.show(10, truncate=False)

        # -------------------------
        # Iceberg step (minimal, non-invasive)
        # -------------------------
        if ICEBERG_ENABLED:
            print("🔁 Starting Iceberg write step (reading back transformed Parquet and writing to Iceberg)")

            # Determine target table: override or derive from destination_path
            target_table = ICEBERG_TARGET_TABLE_OVERRIDE
            if not target_table:
                target_table = derive_table_from_s3_path(destination_path, catalog_name=ICEBERG_CATALOG_NAME)
                print(f"Derived ICEBERG_TARGET_TABLE = {target_table}")

            # Validate target_table format catalog.namespace.table
            m = re.match(r'^([^\.]+)\.([^\.]+)\.([^\.]+)$', target_table)
            if not m:
                print("❌ ERROR: ICEBERG_TARGET_TABLE must be in format catalog.namespace.table")
                # Fail the Iceberg step to avoid silent inconsistencies
                sys.exit(1)
            catalog, namespace, table = m.group(1), m.group(2), m.group(3)

            # Ensure namespace exists (best-effort)
            try:
                ensure_namespace(spark, catalog, namespace)
            except Exception as e:
                print(f"Warning: could not ensure namespace {catalog}.{namespace}: {e}")

            # Read back the parquet that was just written (so Iceberg writes exactly what was persisted)
            print(f"📥 Reading back Parquet from {destination_path} for Iceberg write")
            try:
                iceberg_df = spark.read.parquet(destination_path)
                print("Schema of data to write to Iceberg:")
                iceberg_df.printSchema()
                print("Sample rows:")
                iceberg_df.show(5, truncate=False)
            except Exception as e:
                print(f"❌ ERROR: failed to read back Parquet from {destination_path}: {e}")
                traceback.print_exc()
                sys.exit(1)

            # Write to Iceberg using DataFrameWriterV2 (writeTo); use fallbacks for varying Iceberg versions
            print(f"💾 Writing to Iceberg target table {target_table} with mode {ICEBERG_WRITE_MODE}")
            try:
                if ICEBERG_WRITE_MODE == "append":
                    iceberg_df.writeTo(target_table).append()
                elif ICEBERG_WRITE_MODE == "overwrite":
                    try:
                        iceberg_df.writeTo(target_table).overwritePartitions()
                    except Exception:
                        iceberg_df.writeTo(target_table).createOrReplace()
                else:
                    # default create_or_replace with fallbacks
                    try:
                        iceberg_df.writeTo(target_table).createOrReplace()
                    except AttributeError:
                        try:
                            iceberg_df.writeTo(target_table).create()
                        except Exception:
                            iceberg_df.writeTo(target_table).append()
                print("🎉 Iceberg write completed successfully")
            except Exception as e:
                print(f"❌ ERROR writing to Iceberg table {target_table}: {e}")
                traceback.print_exc()
                sys.exit(1)
        else:
            print("ℹ️ Iceberg step is disabled (ICEBERG_ENABLED=False)")

    except Exception as e:
        print(f"❌ Error during transformation: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
