
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class TransformReq(BaseModel):
    sql: str = Field(..., description="Semicolon-separated Spark SQL") 
    # All other parameters are hidden from user with sensible defaults
    write_mode: Literal["append","overwrite"] = Field(default="overwrite", description="Write mode for output data")
    executor_instances: int = Field(default=2, description="Number of Spark executor instances")
    executor_cores: int = Field(default=2, description="Number of cores per executor")
    executor_memory: str = Field(default="4g", description="Memory per executor")
    driver_cores: int = Field(default=1, description="Number of driver cores")
    driver_memory: str = Field(default="2g", description="Driver memory")
    
    model_config = {
        # Example showing only the required field for API docs
        "json_schema_extra": {
            "example": {
                "sql": "SELECT customer_id, SUM(amount) as total FROM source_data GROUP BY customer_id"
            }
        }
    }
