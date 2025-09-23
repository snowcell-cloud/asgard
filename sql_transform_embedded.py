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
from pyspark.sql.utils import AnalysisException

# -----------------------------
# ICEBERG FEATURE CONFIG (hardcoded here)
# -----------------------------
ICEBERG_ENABLED = True  # Enabled — assumes Iceberg + Nessie jars are present in the Spark image
ICEBERG_CATALOG_NAME = "iceberg"  # Spark catalog name to register for Iceberg
ICEBERG_WAREHOUSE = "s3://airbytedestination1/iceberg/"  # Iceberg warehouse path
# If you want a specific target table, set in format: catalog.namespace.table
ICEBERG_TARGET_TABLE_OVERRIDE = None
# Options: "create_or_replace" (default), "append", "overwrite"
ICEBERG_WRITE_MODE = "append"
# Hardcode Nessie URI (since provided)
NESSIE_URI = "http://nessie.data-platform.svc.cluster.local:19120/api/v1"
NESSIE_REF = "main"
# -----------------------------


def getenv_conf_or_env(spark, conf_key, env_key, default=None):
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
    n = re.sub(r"[^a-z0-9_]", "_", n)
    n = re.sub(r"_+", "_", n)
    n = n.strip("_")
    if not n:
        n = "x"
    if re.match(r"^\d", n):
        n = "t" + n
    return n


def derive_table_from_s3_path(
    path: str,
    catalog_name: str = "iceberg",
    default_namespace: str = "raw",
    default_table: str = "table",
):
    if not path:
        return f"{catalog_name}.{default_namespace}.{default_table}"
    p = re.sub(r"^s3://", "", path)
    p = p.rstrip("/")
    parts = p.split("/")
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
    try:
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {catalog}.{namespace}")
    except Exception as e:
        print(f"Warning: could not CREATE NAMESPACE {catalog}.{namespace}: {e}")


def _is_table_not_found_exc(e: Exception) -> bool:
    """
    Detect AnalysisException messages that indicate the Iceberg table is missing.
    We look for common markers seen in Spark/AnalysisException messages.
    """
    msg = str(e) if e is not None else ""
    markers = ["TABLE_OR_VIEW_NOT_FOUND", "UnresolvedRelation", "Table or view not found"]
    return any(m in msg for m in markers)


def main():
    print("🚀 Starting SQL transformation...")

    spark = SparkSession.builder.appName("SQL Data Transformation").getOrCreate()
    print("✅ Spark session created")

    sql_query = spark.conf.get("spark.sql.transform.query", None) or os.getenv("SQL_QUERY")
    sources_json = spark.conf.get("spark.sql.transform.sources", None) or os.getenv("SOURCE_PATHS")
    destination_path = spark.conf.get("spark.sql.transform.destination", None) or os.getenv(
        "DESTINATION_PATH"
    )
    write_mode = spark.conf.get("spark.sql.transform.writeMode", None) or os.getenv(
        "WRITE_MODE", "overwrite"
    )

    if not sql_query:
        print("❌ ERROR: SQL query is required")
        sys.exit(1)
    if not sources_json:
        print("❌ ERROR: Source paths are required")
        sys.exit(1)
    if not destination_path:
        print("❌ ERROR: Destination path is required")
        sys.exit(1)

    print(f"SQL Query: {sql_query}")
    print(f"Source paths: {sources_json}")
    print(f"Destination: {destination_path}")
    print(f"Write mode: {write_mode}")
    print(f"ICEBERG_ENABLED: {ICEBERG_ENABLED}")

    try:
        source_paths = json.loads(sources_json)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing source paths: {e}")
        sys.exit(1)

    if ICEBERG_ENABLED:
        try:
            spark.conf.set(
                f"spark.sql.catalog.{ICEBERG_CATALOG_NAME}", "org.apache.iceberg.spark.SparkCatalog"
            )
            spark.conf.set(
                f"spark.sql.catalog.{ICEBERG_CATALOG_NAME}.catalog-impl",
                "org.apache.iceberg.nessie.NessieCatalog",
            )
            spark.conf.set(f"spark.sql.catalog.{ICEBERG_CATALOG_NAME}.uri", NESSIE_URI)
            spark.conf.set(f"spark.sql.catalog.{ICEBERG_CATALOG_NAME}.ref", NESSIE_REF)
            spark.conf.set(f"spark.sql.catalog.{ICEBERG_CATALOG_NAME}.warehouse", ICEBERG_WAREHOUSE)
            print(
                f"Configured Iceberg Nessie catalog '{ICEBERG_CATALOG_NAME}' -> uri={NESSIE_URI} ref={NESSIE_REF} warehouse={ICEBERG_WAREHOUSE}"
            )
        except Exception as e:
            print(f"Warning: failed to set Iceberg catalog config in Spark session: {e}")

    try:
        print("📂 Reading source data...")
        combined_df = None
        for i, source_path in enumerate(source_paths):
            print(f"   Reading from: {source_path}")
            try:
                df = spark.read.parquet(source_path)
                combined_df = df if combined_df is None else combined_df.union(df)
                print(f"   ✅ Successfully read source {i+1}")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not read from {source_path}: {e}")
                continue

        if combined_df is None:
            print("❌ No data could be read from any source")
            sys.exit(1)

        combined_df.createOrReplaceTempView("source_data")
        print(f"✅ Created temporary view 'source_data' with {combined_df.count()} rows")

        print("🔄 Executing SQL transformation...")
        result_df = spark.sql(sql_query)
        print(f"✅ SQL executed successfully, result has {result_df.count()} rows")

        print(f"💾 Writing results to: {destination_path}")
        result_df.write.mode(write_mode).parquet(destination_path)
        print("✅ Data transformation completed successfully!")

        print("📊 Sample of transformed data:")
        result_df.show(10, truncate=False)

        if ICEBERG_ENABLED:
            print("🔁 Starting Iceberg write step")
            target_table = ICEBERG_TARGET_TABLE_OVERRIDE or derive_table_from_s3_path(
                destination_path, catalog_name=ICEBERG_CATALOG_NAME
            )
            print(f"Derived ICEBERG_TARGET_TABLE = {target_table}")

            m = re.match(r"^([^\.]+)\.([^\.]+)\.([^\.]+)$", target_table)
            if not m:
                print("❌ ERROR: ICEBERG_TARGET_TABLE must be in format catalog.namespace.table")
                sys.exit(1)
            catalog, namespace, table = m.group(1), m.group(2), m.group(3)

            try:
                ensure_namespace(spark, catalog, namespace)
            except Exception as e:
                print(f"Warning: could not ensure namespace {catalog}.{namespace}: {e}")

            print(f"📥 Reading back Parquet from {destination_path} for Iceberg write")
            iceberg_df = spark.read.parquet(destination_path)
            iceberg_df.persist()  # keep in memory during potential retries

            try:
                # Attempt to append normally (preserves default behavior)
                if ICEBERG_WRITE_MODE == "append":
                    try:
                        print(f"Attempting to append to {target_table} ...")
                        iceberg_df.writeTo(target_table).append()
                        print("Append succeeded.")
                    except AnalysisException as e:
                        # Table might not exist — try to create then write
                        if _is_table_not_found_exc(e):
                            print(
                                f"Table {target_table} not found in catalog; creating table and writing data..."
                            )
                            # createOrReplace will create the table when missing.
                            # It's used here only in the missing-table scenario so we don't
                            # accidentally replace existing tables.
                            iceberg_df.writeTo(target_table).createOrReplace()
                            print("Table created and data written with createOrReplace().")
                        else:
                            # Re-raise unexpected AnalysisExceptions
                            raise
                elif ICEBERG_WRITE_MODE == "overwrite":
                    try:
                        iceberg_df.writeTo(target_table).overwritePartitions()
                        print("overwritePartitions() succeeded.")
                    except Exception:
                        print("overwritePartitions() failed; falling back to createOrReplace()")
                        iceberg_df.writeTo(target_table).createOrReplace()
                        print("createOrReplace() completed.")
                else:
                    # create_or_replace or any other mode--create or replace
                    try:
                        iceberg_df.writeTo(target_table).createOrReplace()
                        print("createOrReplace() completed.")
                    except AttributeError:
                        try:
                            iceberg_df.writeTo(target_table).create()
                            print("create() completed.")
                        except Exception:
                            iceberg_df.writeTo(target_table).append()
                            print("append() completed (fallback).")

                print("🎉 Iceberg write completed successfully")
            except Exception as e:
                print(f"❌ ERROR writing to Iceberg table {target_table}: {e}")
                traceback.print_exc()
                sys.exit(1)
            finally:
                try:
                    iceberg_df.unpersist()
                except Exception:
                    pass
        else:
            print("ℹ️ Iceberg step is disabled")

    except Exception as e:
        print(f"❌ Error during transformation: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
