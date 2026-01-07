"""
LlamaIndex Agent for Natural Language Observability Queries.
Uses ReActAgent to orchestrate queries across multiple data sources.
"""
import os
from typing import Any, Optional, Callable
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.agent.openai import OpenAIAgent
from llama_index.llms.openai import OpenAI
from prometheus_engine import PrometheusQueryEngine
from oracle_db import get_database_engine


class ObservabilityAgent:
    """
    Main agent for natural language observability queries.
    Orchestrates queries across Oracle and Prometheus data sources.
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
            mock_mode=True  # Using mock data for pilot
        )
        
        self._emit_progress('setup_complete', 'Prometheus query engine initialized', 'prometheus',
                           'Ready to query real-time metrics')
    
    def _setup_agent(self):
        """Set up the ReActAgent with query engine tools."""
        self._emit_progress('setup', 'Creating agent with multi-tool orchestration...', None,
                           'Setting up ReActAgent to coordinate queries across data sources')
        
        # Wrap engines as tools
        oracle_tool = QueryEngineTool(
            query_engine=self.oracle_query_engine,
            metadata=ToolMetadata(
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
        )
        
        prometheus_tool = QueryEngineTool(
            query_engine=self.prometheus_query_engine,
            metadata=ToolMetadata(
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
        )
        
        # Create ReActAgent
        self.agent = OpenAIAgent.from_tools(
            tools=[oracle_tool, prometheus_tool],
            llm=self.llm,
            verbose=self.verbose,
            system_prompt=(
                "You are an observability assistant that helps users understand application health and performance.\n"
                "You have access to two data sources:\n"
                "1. Oracle database - contains application configurations, thresholds, and historical incidents\n"
                "2. Prometheus - contains real-time performance metrics\n\n"
                "When answering questions about application performance:\n"
                "- First check Oracle for thresholds and configuration\n"
                "- Then check Prometheus for current metrics\n"
                "- Compare metrics against thresholds\n"
                "- Provide clear, actionable insights\n\n"
                "Always synthesize information from multiple sources to give complete answers.\n"
                "Use natural language and be helpful and concise."
            )
        )
        
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
            # Execute query through agent
            response = self.agent.chat(user_query)
            
            self._emit_progress('complete', 'Query processing complete', None,
                               'Successfully synthesized response from all relevant data sources')
            
            return str(response)
            
        except Exception as e:
            self._emit_progress('error', f'Error processing query: {str(e)}', None,
                               'An unexpected error occurred during query processing')
            raise
    
    def reset(self):
        """Reset agent conversation history."""
        self.agent.reset()
        self._emit_progress('reset', 'Agent conversation reset', None,
                           'Cleared conversation history for new query session')
