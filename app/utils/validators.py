"""
SQL validation utilities
"""

import re
from typing import Dict, List, Any
import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML

from app.utils.logging import get_logger

logger = get_logger(__name__)


class SQLValidator:
    """SQL query validator for transformation queries"""

    def __init__(self):
        self.dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "ALTER",
            "CREATE DATABASE",
            "DROP DATABASE",
            "GRANT",
            "REVOKE",
            "SHUTDOWN",
            "KILL",
            "LOAD_FILE",
            "INTO OUTFILE",
            "INTO DUMPFILE",
            "EXEC",
            "EXECUTE",
            "xp_",
            "sp_",
        ]

        self.dml_keywords = ["INSERT", "UPDATE", "DELETE"]

        self.required_table_reference = "bronze_data"

    async def validate_query(self, sql_query: str) -> Dict[str, Any]:
        """Validate SQL query and return validation results"""

        if not sql_query or not sql_query.strip():
            return {
                "is_valid": False,
                "errors": ["SQL query cannot be empty"],
                "warnings": [],
            }

        errors = []
        warnings = []

        try:
            # Basic length check
            if len(sql_query) > 10000:
                errors.append("SQL query is too long (maximum 10,000 characters)")

            # Parse SQL
            parsed = sqlparse.parse(sql_query)

            if not parsed:
                errors.append("Unable to parse SQL query")
                return {"is_valid": False, "errors": errors, "warnings": warnings}

            # Validate each statement
            for statement in parsed:
                if isinstance(statement, Statement):
                    stmt_errors, stmt_warnings = await self._validate_statement(
                        statement
                    )
                    errors.extend(stmt_errors)
                    warnings.extend(stmt_warnings)

            # Check for required table reference
            if not self._contains_table_reference(sql_query):
                warnings.append(
                    f"Query should reference '{self.required_table_reference}' table"
                )

            # Check for potentially expensive operations
            expensive_ops = self._check_expensive_operations(sql_query)
            if expensive_ops:
                warnings.extend(
                    [f"Potentially expensive operation: {op}" for op in expensive_ops]
                )

            return {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
            }

        except Exception as e:
            logger.error(f"SQL validation error: {str(e)}")
            return {
                "is_valid": False,
                "errors": [f"SQL validation failed: {str(e)}"],
                "warnings": [],
            }

    async def _validate_statement(
        self, statement: Statement
    ) -> tuple[List[str], List[str]]:
        """Validate individual SQL statement"""

        errors = []
        warnings = []

        # Check for dangerous keywords
        for token in statement.flatten():
            if token.ttype is Keyword:
                token_upper = token.value.upper()

                # Check for dangerous operations
                for dangerous in self.dangerous_keywords:
                    if dangerous in token_upper:
                        errors.append(f"Forbidden SQL operation: {dangerous}")

                # Check for DML operations (should be read-only)
                if token.ttype is DML and token_upper in self.dml_keywords:
                    errors.append(f"DML operations not allowed: {token_upper}")

        # Check statement type
        statement_type = self._get_statement_type(statement)

        if statement_type not in ["SELECT", "WITH"]:
            errors.append(
                f"Only SELECT and WITH statements are allowed, found: {statement_type}"
            )

        return errors, warnings

    def _get_statement_type(self, statement: Statement) -> str:
        """Get the type of SQL statement"""

        first_token = statement.token_first(skip_whitespace=True, skip_comments=True)
        if first_token:
            return first_token.value.upper()
        return "UNKNOWN"

    def _contains_table_reference(self, sql_query: str) -> bool:
        """Check if query contains reference to the required table"""

        query_upper = sql_query.upper()
        return self.required_table_reference.upper() in query_upper

    def _check_expensive_operations(self, sql_query: str) -> List[str]:
        """Check for potentially expensive SQL operations"""

        expensive_ops = []
        query_upper = sql_query.upper()

        # Check for operations that might be expensive
        if "ORDER BY" in query_upper and "LIMIT" not in query_upper:
            expensive_ops.append("ORDER BY without LIMIT")

        if "DISTINCT" in query_upper:
            expensive_ops.append("DISTINCT operation")

        if "GROUP BY" in query_upper:
            expensive_ops.append("GROUP BY operation")

        # Count number of JOINs
        join_count = len(re.findall(r"\bJOIN\b", query_upper))
        if join_count > 3:
            expensive_ops.append(f"Multiple JOINs ({join_count})")

        # Check for nested subqueries
        subquery_count = query_upper.count("(SELECT")
        if subquery_count > 2:
            expensive_ops.append(f"Multiple nested subqueries ({subquery_count})")

        # Check for window functions
        if "OVER(" in query_upper or "OVER (" in query_upper:
            expensive_ops.append("Window functions")

        return expensive_ops

    def suggest_optimizations(self, sql_query: str) -> List[str]:
        """Suggest query optimizations"""

        suggestions = []
        query_upper = sql_query.upper()

        # Suggest LIMIT for potentially large results
        if "ORDER BY" in query_upper and "LIMIT" not in query_upper:
            suggestions.append("Consider adding LIMIT clause to ORDER BY queries")

        # Suggest WHERE clause optimization
        if "WHERE" not in query_upper:
            suggestions.append("Consider adding WHERE clause to filter data")

        # Suggest column selection optimization
        if re.search(r"SELECT\s+\*", query_upper):
            suggestions.append(
                "Consider selecting specific columns instead of SELECT *"
            )

        # Suggest partitioning
        if "GROUP BY" in query_upper:
            suggestions.append(
                "Consider partitioning output data for better performance"
            )

        return suggestions


class DataQualityValidator:
    """Validator for data quality rules"""

    def __init__(self):
        self.supported_rules = [
            "not_null",
            "unique",
            "range",
            "regex",
            "length",
            "custom",
            "customer_pii",
            "data_type",
        ]

    def validate_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data quality rules"""

        errors = []
        warnings = []

        for rule in rules:
            rule_type = rule.get("rule_type")

            if not rule_type:
                errors.append("Data quality rule must have 'rule_type'")
                continue

            if rule_type not in self.supported_rules:
                errors.append(f"Unsupported rule type: {rule_type}")
                continue

            # Validate rule-specific parameters
            if rule_type == "range":
                params = rule.get("parameters", {})
                if "min" not in params and "max" not in params:
                    errors.append("Range rule must specify 'min' or 'max' parameter")

            elif rule_type == "regex":
                params = rule.get("parameters", {})
                if "pattern" not in params:
                    errors.append("Regex rule must specify 'pattern' parameter")
                else:
                    try:
                        re.compile(params["pattern"])
                    except re.error:
                        errors.append(f"Invalid regex pattern: {params['pattern']}")

            elif rule_type == "length":
                params = rule.get("parameters", {})
                if "min_length" not in params and "max_length" not in params:
                    errors.append(
                        "Length rule must specify 'min_length' or 'max_length' parameter"
                    )

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}


class ColumnOperationValidator:
    """Validator for column operations"""

    def __init__(self):
        self.supported_operations = ["add", "remove", "rename", "update", "cast"]

    def validate_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate column operations"""

        errors = []
        warnings = []

        column_names = set()

        for operation in operations:
            op_type = operation.get("operation")
            column_name = operation.get("name")

            if not op_type:
                errors.append("Column operation must have 'operation' field")
                continue

            if op_type not in self.supported_operations:
                errors.append(f"Unsupported operation type: {op_type}")
                continue

            if not column_name:
                errors.append("Column operation must have 'name' field")
                continue

            # Check for duplicate column operations
            if column_name in column_names:
                warnings.append(f"Multiple operations on column: {column_name}")
            column_names.add(column_name)

            # Validate operation-specific requirements
            if op_type == "rename":
                if not operation.get("new_name"):
                    errors.append(
                        f"Rename operation for '{column_name}' must specify 'new_name'"
                    )

            elif op_type == "cast":
                if not operation.get("data_type"):
                    errors.append(
                        f"Cast operation for '{column_name}' must specify 'data_type'"
                    )

            elif op_type == "add":
                if not operation.get("expression") and not operation.get(
                    "default_value"
                ):
                    errors.append(
                        f"Add operation for '{column_name}' must specify 'expression' or 'default_value'"
                    )

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}
