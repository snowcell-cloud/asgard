"""
AWS S3 client for data lake operations
"""

import json
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class S3Client:
    """S3 client for data lake operations"""

    def __init__(self):
        self.settings = get_settings()
        self.s3_client = boto3.client("s3", region_name=self.settings.aws_region)
        self.s3_resource = boto3.resource("s3", region_name=self.settings.aws_region)

    async def path_exists(self, path: str) -> bool:
        """Check if S3 path exists"""

        try:
            # Remove leading slash and construct full path
            clean_path = path.lstrip("/")
            full_path = f"{clean_path}/" if not clean_path.endswith("/") else clean_path

            response = self.s3_client.list_objects_v2(
                Bucket=self.settings.s3_bucket, Prefix=full_path, MaxKeys=1
            )

            return response.get("KeyCount", 0) > 0

        except ClientError as e:
            logger.error(f"Error checking path existence {path}: {str(e)}")
            return False

    async def get_path_size(self, path: str) -> float:
        """Get total size of data at S3 path in GB"""

        try:
            clean_path = path.lstrip("/")
            total_size = 0

            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.settings.s3_bucket, Prefix=clean_path
            )

            for page in pages:
                for obj in page.get("Contents", []):
                    total_size += obj["Size"]

            # Convert bytes to GB
            size_gb = total_size / (1024**3)
            return round(size_gb, 2)

        except ClientError as e:
            logger.error(f"Error getting path size {path}: {str(e)}")
            return 0.0

    async def list_objects(
        self, path: str, max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """List objects at S3 path"""

        try:
            clean_path = path.lstrip("/")

            response = self.s3_client.list_objects_v2(
                Bucket=self.settings.s3_bucket, Prefix=clean_path, MaxKeys=max_keys
            )

            objects = []
            for obj in response.get("Contents", []):
                objects.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                        "etag": obj["ETag"].strip('"'),
                    }
                )

            return objects

        except ClientError as e:
            logger.error(f"Error listing objects at {path}: {str(e)}")
            return []

    async def read_json_object(self, key: str) -> Dict[str, Any]:
        """Read JSON object from S3"""

        try:
            response = self.s3_client.get_object(
                Bucket=self.settings.s3_bucket, Key=key
            )

            content = response["Body"].read().decode("utf-8")
            return json.loads(content)

        except ClientError as e:
            logger.error(f"Error reading JSON object {key}: {str(e)}")
            raise Exception(f"Failed to read object: {str(e)}")

    async def write_json_object(self, key: str, data: Dict[str, Any]) -> bool:
        """Write JSON object to S3"""

        try:
            self.s3_client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=json.dumps(data, default=str, indent=2),
                ContentType="application/json",
            )

            logger.info(f"Successfully wrote JSON object to {key}")
            return True

        except ClientError as e:
            logger.error(f"Error writing JSON object {key}: {str(e)}")
            return False

    async def delete_object(self, key: str) -> bool:
        """Delete object from S3"""

        try:
            self.s3_client.delete_object(Bucket=self.settings.s3_bucket, Key=key)

            logger.info(f"Successfully deleted object {key}")
            return True

        except ClientError as e:
            logger.error(f"Error deleting object {key}: {str(e)}")
            return False

    async def copy_object(self, source_key: str, dest_key: str) -> bool:
        """Copy object within S3"""

        try:
            copy_source = {"Bucket": self.settings.s3_bucket, "Key": source_key}

            self.s3_client.copy_object(
                CopySource=copy_source, Bucket=self.settings.s3_bucket, Key=dest_key
            )

            logger.info(f"Successfully copied {source_key} to {dest_key}")
            return True

        except ClientError as e:
            logger.error(f"Error copying object {source_key} to {dest_key}: {str(e)}")
            return False

    async def create_presigned_url(
        self, key: str, expiration: int = 3600
    ) -> Optional[str]:
        """Create presigned URL for S3 object"""

        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.settings.s3_bucket, "Key": key},
                ExpiresIn=expiration,
            )

            return url

        except ClientError as e:
            logger.error(f"Error creating presigned URL for {key}: {str(e)}")
            return None

    async def get_object_metadata(self, key: str) -> Dict[str, Any]:
        """Get object metadata"""

        try:
            response = self.s3_client.head_object(
                Bucket=self.settings.s3_bucket, Key=key
            )

            return {
                "size": response.get("ContentLength", 0),
                "last_modified": response.get("LastModified"),
                "content_type": response.get("ContentType"),
                "etag": response.get("ETag", "").strip('"'),
                "metadata": response.get("Metadata", {}),
            }

        except ClientError as e:
            logger.error(f"Error getting metadata for {key}: {str(e)}")
            return {}

    async def sync_to_glue_catalog(
        self,
        database_name: str,
        table_name: str,
        s3_path: str,
        data_format: str = "parquet",
    ) -> bool:
        """Sync S3 data to Glue Data Catalog"""

        try:
            glue_client = boto3.client("glue", region_name=self.settings.aws_region)

            # Check if database exists
            try:
                glue_client.get_database(Name=database_name)
            except ClientError as e:
                if e.response["Error"]["Code"] == "EntityNotFoundException":
                    # Create database
                    glue_client.create_database(
                        DatabaseInput={
                            "Name": database_name,
                            "Description": f"Data lake database for {database_name} tables",
                        }
                    )
                    logger.info(f"Created Glue database: {database_name}")

            # Detect schema by reading sample data
            schema = await self._detect_schema(s3_path, data_format)

            # Create or update table
            table_input = {
                "Name": table_name,
                "StorageDescriptor": {
                    "Columns": schema,
                    "Location": f"s3://{self.settings.s3_bucket}/{s3_path.lstrip('/')}",
                    "InputFormat": self._get_input_format(data_format),
                    "OutputFormat": self._get_output_format(data_format),
                    "SerdeInfo": {
                        "SerializationLibrary": self._get_serde_library(data_format)
                    },
                    "Compressed": True if data_format == "parquet" else False,
                    "StoredAsSubDirectories": False,
                },
                "PartitionKeys": [],  # Can be enhanced to detect partitions
                "TableType": "EXTERNAL_TABLE",
                "Parameters": {
                    "classification": data_format,
                    "compressionType": "snappy" if data_format == "parquet" else "none",
                    "typeOfData": "file",
                },
            }

            try:
                # Try to update existing table
                glue_client.update_table(
                    DatabaseName=database_name, TableInput=table_input
                )
                logger.info(f"Updated Glue table: {database_name}.{table_name}")
            except ClientError as e:
                if e.response["Error"]["Code"] == "EntityNotFoundException":
                    # Create new table
                    glue_client.create_table(
                        DatabaseName=database_name, TableInput=table_input
                    )
                    logger.info(f"Created Glue table: {database_name}.{table_name}")
                else:
                    raise e

            return True

        except Exception as e:
            logger.error(f"Error syncing to Glue catalog: {str(e)}")
            return False

    async def _detect_schema(
        self, s3_path: str, data_format: str
    ) -> List[Dict[str, str]]:
        """Detect schema from S3 data"""

        try:
            if data_format.lower() == "parquet":
                return await self._detect_parquet_schema(s3_path)
            elif data_format.lower() == "json":
                return await self._detect_json_schema(s3_path)
            elif data_format.lower() == "csv":
                return await self._detect_csv_schema(s3_path)
            else:
                logger.warning(
                    f"Schema detection not implemented for format: {data_format}"
                )
                return []

        except Exception as e:
            logger.error(f"Error detecting schema: {str(e)}")
            return []

    async def _detect_parquet_schema(self, s3_path: str) -> List[Dict[str, str]]:
        """Detect schema from Parquet files"""

        try:
            import pandas as pd

            # List parquet files in the path
            objects = await self.list_objects(s3_path)
            parquet_files = [
                obj["key"] for obj in objects if obj["key"].endswith(".parquet")
            ]

            if not parquet_files:
                return []

            # Read first parquet file to get schema
            first_file = f"s3://{self.settings.s3_bucket}/{parquet_files[0]}"
            df = pd.read_parquet(first_file, nrows=1)

            schema = []
            for column, dtype in df.dtypes.items():
                glue_type = self._pandas_to_glue_type(str(dtype))
                schema.append({"Name": column, "Type": glue_type})

            return schema

        except Exception as e:
            logger.error(f"Error detecting Parquet schema: {str(e)}")
            # Return default schema
            return [
                {"Name": "id", "Type": "bigint"},
                {"Name": "data", "Type": "string"},
                {"Name": "timestamp", "Type": "timestamp"},
            ]

    async def _detect_json_schema(self, s3_path: str) -> List[Dict[str, str]]:
        """Detect schema from JSON files"""

        try:
            # List JSON files
            objects = await self.list_objects(s3_path)
            json_files = [obj["key"] for obj in objects if obj["key"].endswith(".json")]

            if not json_files:
                return []

            # Read first JSON file to infer schema
            sample_data = await self.read_json_object(json_files[0])

            schema = []
            for key, value in sample_data.items():
                glue_type = self._python_to_glue_type(type(value))
                schema.append({"Name": key, "Type": glue_type})

            return schema

        except Exception as e:
            logger.error(f"Error detecting JSON schema: {str(e)}")
            return []

    async def _detect_csv_schema(self, s3_path: str) -> List[Dict[str, str]]:
        """Detect schema from CSV files"""

        try:
            import pandas as pd

            # List CSV files
            objects = await self.list_objects(s3_path)
            csv_files = [obj["key"] for obj in objects if obj["key"].endswith(".csv")]

            if not csv_files:
                return []

            # Read first CSV file to get schema
            first_file = f"s3://{self.settings.s3_bucket}/{csv_files[0]}"
            df = pd.read_csv(first_file, nrows=1)

            schema = []
            for column, dtype in df.dtypes.items():
                glue_type = self._pandas_to_glue_type(str(dtype))
                schema.append({"Name": column, "Type": glue_type})

            return schema

        except Exception as e:
            logger.error(f"Error detecting CSV schema: {str(e)}")
            return []

    def _pandas_to_glue_type(self, pandas_type: str) -> str:
        """Convert pandas dtype to Glue data type"""

        type_mapping = {
            "int64": "bigint",
            "int32": "int",
            "float64": "double",
            "float32": "float",
            "object": "string",
            "bool": "boolean",
            "datetime64[ns]": "timestamp",
            "category": "string",
        }

        return type_mapping.get(pandas_type, "string")

    def _python_to_glue_type(self, python_type) -> str:
        """Convert Python type to Glue data type"""

        type_mapping = {
            int: "bigint",
            float: "double",
            str: "string",
            bool: "boolean",
            list: "array<string>",
            dict: "struct<>",
        }

        return type_mapping.get(python_type, "string")

    def _get_input_format(self, data_format: str) -> str:
        """Get Glue input format for data format"""

        format_mapping = {
            "parquet": "org.apache.hadoop.mapred.TextInputFormat",
            "json": "org.apache.hadoop.mapred.TextInputFormat",
            "csv": "org.apache.hadoop.mapred.TextInputFormat",
        }

        return format_mapping.get(
            data_format.lower(), "org.apache.hadoop.mapred.TextInputFormat"
        )

    def _get_output_format(self, data_format: str) -> str:
        """Get Glue output format for data format"""

        format_mapping = {
            "parquet": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "json": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "csv": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
        }

        return format_mapping.get(
            data_format.lower(),
            "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
        )

    def _get_serde_library(self, data_format: str) -> str:
        """Get SerDe library for data format"""

        serde_mapping = {
            "parquet": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
            "json": "org.openx.data.jsonserde.JsonSerDe",
            "csv": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
        }

        return serde_mapping.get(
            data_format.lower(), "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
        )


# Global instance
_s3_client: Optional[S3Client] = None


async def init_s3_client():
    """Initialize the global S3 client"""
    global _s3_client
    _s3_client = S3Client()
    logger.info("S3 client initialized")


def get_s3_client() -> S3Client:
    """Get the global S3 client instance"""
    if _s3_client is None:
        raise Exception("S3 client not initialized. Call init_s3_client() first.")
    return _s3_client
