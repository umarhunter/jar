"""
Custom Oracle Query Engine wrapper for LlamaIndex.
Wraps NLSQLTableQueryEngine with progress callback support.
"""
from typing import Any, Optional
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.llms.llm import BaseLLM


class OracleQueryEngine(CustomQueryEngine):
    """Custom query engine wrapper for Oracle (SQLite) with progress callbacks."""

    llm: BaseLLM
    sql_database: SQLDatabase
    tables: list
    nl_sql_engine: Any = None
    progress_callback: Any = None

    def __init__(self, llm: BaseLLM, sql_database: SQLDatabase, tables: list,
                 progress_callback: Any = None, verbose: bool = True, **kwargs):
        """
        Initialize Oracle query engine wrapper.

        Args:
            llm: LLM instance
            sql_database: SQLDatabase instance
            tables: List of table names to query
            progress_callback: Optional callback for progress updates
            verbose: Enable verbose logging
        """
        super().__init__(
            llm=llm,
            sql_database=sql_database,
            tables=tables,
            progress_callback=progress_callback,
            **kwargs
        )

        # Create the underlying NLSQLTableQueryEngine
        self.nl_sql_engine = NLSQLTableQueryEngine(
            sql_database=sql_database,
            tables=tables,
            llm=llm,
            verbose=verbose
        )

        print(f"Oracle query engine initialized with tables: {', '.join(tables)}")

    def _emit_progress(self, step: str, message: str, reasoning: str = ""):
        """Emit progress update if callback is provided."""
        if self.progress_callback:
            self.progress_callback({
                'step': step,
                'message': message,
                'source': 'oracle',
                'reasoning': reasoning
            })

    def custom_query(self, query_str: str) -> Any:
        """Execute a query against Oracle database with progress tracking."""

        self._emit_progress('query_start', 'Querying Oracle configuration database...',
                           'Translating natural language to SQL')

        try:
            # Execute query using the underlying NLSQLTableQueryEngine
            result = self.nl_sql_engine.query(query_str)

            self._emit_progress('query_complete', 'Oracle query complete',
                               'Successfully retrieved configuration data')

            return result

        except Exception as e:
            self._emit_progress('query_error', f'Oracle query failed: {str(e)}',
                               'Error executing SQL query')
            raise
