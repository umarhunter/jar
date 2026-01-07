"""
LlamaIndex Agent for Natural Language Observability Queries.
Uses FunctionAgent with workflow-based approach to orchestrate queries across multiple data sources.
"""
import os
import asyncio
from typing import Any, Optional, Callable
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI
from prometheus_engine import PrometheusQueryEngine
from elasticsearch_engine import ElasticsearchQueryEngine
from oracle_db import get_database_engine


class ObservabilityAgent:
    """
    Main agent for natural language observability queries.
    Orchestrates queries across Oracle, Prometheus, and Elasticsearch data sources.
    """
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 progress_callback: Optional[Callable] = None,
                 verbose: bool = True):
        """
        Initialize the observability agent.
        
        Args:
            openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            progress_callback: Function to call with progress updates
            verbose: Enable verbose logging
        """
        self.progress_callback = progress_callback
        self.verbose = verbose
        
        # Set up OpenAI
        if openai_api_key:
            os.environ['OPENAI_API_KEY'] = openai_api_key
        
        self.llm = OpenAI(model="gpt-4", temperature=0)
        
        # Initialize data sources
        self._setup_oracle_engine()
        self._setup_prometheus_engine()
        self._setup_elasticsearch_engine()

        # Create agent with tools
        self._setup_agent()
    
    def _emit_progress(self, step: str, message: str, source: Optional[str] = None, reasoning: str = ""):
        """Emit progress update if callback is provided."""
        if self.progress_callback:
            self.progress_callback({
                'step': step,
                'message': message,
                'source': source,
                'reasoning': reasoning
            })
    
    def _setup_oracle_engine(self):
        """Set up Oracle (SQLite) query engine using NLSQLTableQueryEngine."""
        self._emit_progress('setup', 'Initializing Oracle database connection...', 'oracle',
                           'Setting up connection to configuration database')
        
        # Get database engine
        engine = get_database_engine()
        sql_database = SQLDatabase(engine)
        
        # Create NL to SQL query engine
        self.oracle_query_engine = NLSQLTableQueryEngine(
            sql_database=sql_database,
            tables=['applications', 'performance_thresholds', 'incidents'],
            llm=self.llm,
            verbose=self.verbose
        )
        
        self._emit_progress('setup_complete', 'Oracle database connection established', 'oracle',
                           'Ready to query application configurations and thresholds')
    
    def _setup_prometheus_engine(self):
        """Set up custom Prometheus query engine."""
        self._emit_progress('setup', 'Initializing Prometheus query engine...', 'prometheus',
                           'Setting up connection to metrics database')

        self.prometheus_query_engine = PrometheusQueryEngine(
            llm=self.llm,
            mock_mode=False  # Use real Prometheus (falls back to mock if unavailable)
        )

        self._emit_progress('setup_complete', 'Prometheus query engine initialized', 'prometheus',
                           'Ready to query real-time metrics')

    def _setup_elasticsearch_engine(self):
        """Set up custom Elasticsearch query engine."""
        self._emit_progress('setup', 'Initializing Elasticsearch query engine...', 'elasticsearch',
                           'Setting up connection to logs database')

        self.elasticsearch_query_engine = ElasticsearchQueryEngine(
            llm=self.llm,
            mock_mode=False  # Use real Elasticsearch (falls back to mock if unavailable)
        )

        self._emit_progress('setup_complete', 'Elasticsearch query engine initialized', 'elasticsearch',
                           'Ready to query application logs and traces')
    
    def _setup_agent(self):
        """Set up the FunctionAgent with query engine tools."""
        self._emit_progress('setup', 'Creating agent with multi-tool orchestration...', None,
                           'Setting up FunctionAgent to coordinate queries across data sources')
        
        # Wrap engines as tools using from_defaults
        oracle_tool = QueryEngineTool.from_defaults(
            query_engine=self.oracle_query_engine,
            name="oracle_config",
            description=(
                "Query application configuration, performance thresholds, and historical incidents. "
                "Use this to find:\n"
                "- What applications are being monitored\n"
                "- Performance thresholds (CPU, memory, response time, error rate limits)\n"
                "- Historical incidents and their resolution\n"
                "- Application metadata (owner, environment, description)\n"
                "Examples: 'What applications are monitored?', 'What is the CPU threshold for user-service?', "
                "'Show me recent incidents'"
            )
        )
        
        prometheus_tool = QueryEngineTool.from_defaults(
            query_engine=self.prometheus_query_engine,
            name="prometheus_metrics",
            description=(
                "Query real-time performance metrics from Prometheus. "
                "Use this to get current:\n"
                "- CPU usage (percentage)\n"
                "- Memory usage (percentage)\n"
                "- Request rates (requests per second)\n"
                "- Error counts and rates\n"
                "- Response times and latency\n"
                "Supports time windows like 'right now', 'last 30 minutes', 'past hour'.\n"
                "Examples: 'What is the CPU usage?', 'How many errors in the last 30 minutes?', "
                "'What is the current memory usage?'"
            )
        )

        elasticsearch_tool = QueryEngineTool.from_defaults(
            query_engine=self.elasticsearch_query_engine,
            name="elasticsearch_logs",
            description=(
                "Query application logs and error traces from Elasticsearch. "
                "Use this to find:\n"
                "- Error logs and stack traces\n"
                "- Application log messages (INFO, WARN, ERROR, FATAL)\n"
                "- Recent errors and their details\n"
                "- Log patterns and trends\n"
                "- Error types and frequencies\n"
                "Supports time windows like 'last 30 minutes', 'past hour', 'today'.\n"
                "Examples: 'Show me recent errors', 'What errors occurred in the last hour?', "
                "'Are there any authentication failures?', 'Show logs for user-service'"
            )
        )

        # Create FunctionAgent with workflow approach
        self.agent = FunctionAgent(
            tools=[oracle_tool, prometheus_tool, elasticsearch_tool],
            llm=self.llm,
            system_prompt=(
                "You are an observability assistant that helps users understand application health and performance.\n"
                "You have access to three data sources:\n"
                "1. Oracle database - contains application configurations, thresholds, and historical incidents\n"
                "2. Prometheus - contains real-time performance metrics (CPU, memory, requests, errors, latency)\n"
                "3. Elasticsearch - contains application logs, error traces, and log-level messages\n\n"
                "When answering questions about application performance:\n"
                "- Check Oracle for thresholds and configuration\n"
                "- Check Prometheus for current metrics\n"
                "- Check Elasticsearch for detailed error logs and traces\n"
                "- Compare metrics against thresholds\n"
                "- Correlate metrics with log data to provide deeper insights\n"
                "- Provide clear, actionable insights\n\n"
                "Always synthesize information from multiple sources to give complete answers.\n"
                "Use natural language and be helpful and concise."
            )
        )
        
        # Create workflow context
        self.ctx = Context(self.agent)
        
        self._emit_progress('setup_complete', 'Agent ready to process queries', None,
                           'All data sources connected and agent is operational')
    
    def query(self, user_query: str) -> str:
        """
        Process a natural language query.
        
        Args:
            user_query: Natural language question about application health
            
        Returns:
            Natural language response synthesized from data sources
        """
        self._emit_progress('started', f'Processing query: "{user_query}"', None,
                           'Analyzing query and determining which data sources to consult')
        
        try:
            # Execute query through agent using workflow API
            handler = self.agent.run(user_query, ctx=self.ctx)
            response = asyncio.run(handler)
            
            self._emit_progress('complete', 'Query processing complete', None,
                               'Successfully synthesized response from all relevant data sources')
            
            return str(response)
            
        except Exception as e:
            self._emit_progress('error', f'Error processing query: {str(e)}', None,
                               'An unexpected error occurred during query processing')
            raise
    
    def reset(self):
        """Reset agent conversation history."""
        # Recreate context for fresh conversation
        self.ctx = Context(self.agent)
        self._emit_progress('reset', 'Agent conversation reset', None,
                           'Cleared conversation history for new query session')
